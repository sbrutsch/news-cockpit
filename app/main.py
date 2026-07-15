"""News-Cockpit — FastAPI-App: Ingest-API, Items-API, Login, statisches Frontend."""

import os


def _load_env_file():
    """Minimaler .env-Loader (nur lokale Entwicklung, keine Abhängigkeit).

    Muss VOR den app-Imports laufen, weil db/auth ihre Umgebung beim Import lesen.
    Bereits gesetzte Variablen werden nie überschrieben.
    """
    path = os.environ.get("ENV_FILE", ".env")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_env_file()

import logging  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi import Depends, FastAPI, HTTPException, Request, Response  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app import auth, db, transform  # noqa: E402

log = logging.getLogger("news-cockpit")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
MAX_BATCH = 500


@asynccontextmanager
async def lifespan(_app):
    db.init()
    backend = "PostgreSQL" if db.IS_POSTGRES else "SQLite (lokale Entwicklung)"
    log.info("Datenbank bereit: %s", backend)
    if auth.SECRET_KEY_IS_EPHEMERAL:
        log.warning("SECRET_KEY nicht gesetzt — Sessions überleben keinen Neustart.")
    if not os.environ.get("INGEST_TOKEN"):
        log.warning("INGEST_TOKEN nicht gesetzt — Ingest-API antwortet mit 401.")
    if not auth.get_password_hash():
        log.warning("APP_PASSWORD_HASH/APP_PASSWORD nicht gesetzt — Login ist deaktiviert.")
    yield


app = FastAPI(title="News-Cockpit", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "?"


def require_session(request: Request):
    token = request.cookies.get(auth.SESSION_COOKIE, "")
    if not auth.verify_session_token(token):
        raise HTTPException(status_code=401, detail="Nicht angemeldet")


def require_ingest_token(request: Request):
    header = request.headers.get("authorization", "")
    candidate = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not auth.verify_ingest_token(candidate):
        raise HTTPException(status_code=401, detail="Ungültiger oder fehlender Ingest-Token")


class LoginBody(BaseModel):
    password: str


class IngestItem(BaseModel):
    title: str
    url: str
    source: str = ""
    summary: str = ""
    published_at: str | int | float | None = None
    kind: str = "news"    # news | idee | zitat
    pillar: str = ""      # z. B. "Decision Breakdown", "Board Dynamics"


class PatchBody(BaseModel):
    important: bool | None = None
    status: str | None = None  # 'new' (wiederherstellen) oder 'archived'
    note: str | None = None    # Stefans eigener Gedanke zum Eintrag; '' löscht


@app.post("/api/login")
def login(body: LoginBody, request: Request, response: Response):
    ip = client_ip(request)
    if not auth.login_allowed(ip):
        raise HTTPException(status_code=429, detail="Zu viele Fehlversuche — bitte 15 Minuten warten")
    stored = auth.get_password_hash()
    if not stored:
        raise HTTPException(status_code=503, detail="Kein Passwort konfiguriert (APP_PASSWORD_HASH)")
    if not auth.verify_password(body.password, stored):
        auth.register_failure(ip)
        log.warning("Fehlgeschlagener Login von %s", ip)
        raise HTTPException(status_code=401, detail="Falsches Passwort")
    auth.clear_failures(ip)
    secure = (request.headers.get("x-forwarded-proto") or request.url.scheme) == "https"
    response.set_cookie(auth.SESSION_COOKIE, auth.create_session_token(),
                        max_age=auth.SESSION_TTL, httponly=True,
                        samesite="lax", secure=secure, path="/")
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me", dependencies=[Depends(require_session)])
def me():
    return {"ok": True}


@app.post("/api/ingest", dependencies=[Depends(require_ingest_token)])
def ingest(payload: IngestItem | list[IngestItem]):
    items = payload if isinstance(payload, list) else [payload]
    if len(items) > MAX_BATCH:
        raise HTTPException(status_code=413, detail=f"Maximal {MAX_BATCH} Items pro Aufruf")
    created = duplicates = rejected = 0
    for it in items:
        title, url = it.title.strip(), it.url.strip()
        if not title or not url.startswith(("http://", "https://")):
            rejected += 1
            continue
        if db.insert_item(title, url, it.source, it.summary, it.published_at,
                          kind=it.kind, pillar=it.pillar):
            created += 1
        else:
            duplicates += 1
    body = {"received": len(items), "created": created,
            "duplicates": duplicates, "rejected": rejected}
    return JSONResponse(body, status_code=201 if created else 200)


@app.get("/api/items", dependencies=[Depends(require_session)])
def get_items(tab: str = "new", q: str = "", limit: int = 50, offset: int = 0, kind: str = ""):
    if tab not in ("new", "important", "archived"):
        raise HTTPException(status_code=400, detail="tab muss new, important oder archived sein")
    if kind and kind not in db.KINDS:
        raise HTTPException(status_code=400, detail="kind muss news, idee oder zitat sein")
    items = db.list_items(tab=tab, q=q.strip(), limit=limit, offset=offset, kind=kind)
    return {"items": items, "counts": db.counts()}


@app.patch("/api/items/{item_id}", dependencies=[Depends(require_session)])
def patch_item(item_id: int, body: PatchBody):
    if body.status is not None and body.status not in ("new", "archived"):
        raise HTTPException(status_code=400, detail="status muss 'new' oder 'archived' sein")
    if body.note is not None and len(body.note) > 5000:
        raise HTTPException(status_code=400, detail="Notiz darf höchstens 5000 Zeichen haben")
    item = db.get_item(item_id)
    if not item or item["status"] == "deleted":
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    note = body.note.strip() if body.note is not None else None
    return db.update_item(item_id, important=body.important, status=body.status, note=note)


@app.post("/api/items/{item_id}/verwerten", dependencies=[Depends(require_session)])
def verwerten(item_id: int):
    item = db.get_item(item_id)
    if not item or item["status"] == "deleted":
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    try:
        draft = transform.linkedin_entwurf(item)
    except transform.TransformError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return {"draft": draft, "model": transform.MODEL}


@app.post("/api/items/{item_id}/einordnen", dependencies=[Depends(require_session)])
def einordnen(item_id: int):
    item = db.get_item(item_id)
    if not item or item["status"] == "deleted":
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    try:
        relevanz, resumee = transform.einordnung(item)
    except transform.TransformError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    return db.update_item(item_id, assessment=resumee, relevance=relevanz)


@app.delete("/api/items/{item_id}", dependencies=[Depends(require_session)])
def delete_item(item_id: int):
    item = db.get_item(item_id)
    if not item or item["status"] == "deleted":
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    db.update_item(item_id, status="deleted")
    return {"ok": True}


_EXPORT_KIND = {"news": "Meldung", "idee": "Content-Idee", "zitat": "Zitat"}


def _export_datum(iso):
    try:
        s = iso[:-1] + "+00:00" if iso.endswith("Z") else iso
        return datetime.fromisoformat(s).strftime("%d.%m.%Y")
    except (ValueError, TypeError, AttributeError):
        return ""


@app.get("/api/export", dependencies=[Depends(require_session)])
def export_markdown(days: int = 7):
    days = max(1, min(days, 90))
    seit = datetime.now(timezone.utc) - timedelta(days=days)
    items = db.export_items(seit.strftime("%Y-%m-%dT%H:%M:%SZ"))
    heute = datetime.now(timezone.utc)

    zeilen = [
        "# Wochen-Export — Wichtiges aus dem News-Cockpit",
        "",
        f"Zeitraum: {seit.strftime('%d.%m.%Y')} bis {heute.strftime('%d.%m.%Y')} · "
        f"{len(items)} {'Eintrag' if len(items) == 1 else 'Einträge'}",
        "",
    ]
    if not items:
        zeilen.append("*Keine als wichtig markierten Einträge in diesem Zeitraum.*")
    else:
        # Nach Content-Säule gruppieren; Einträge ohne Säule ans Ende
        gruppen = {}
        for it in items:
            gruppen.setdefault(it["pillar"] or "zzz_ohne", []).append(it)
        for pillar in sorted(gruppen):
            zeilen.append(f"## {'Ohne Säule' if pillar == 'zzz_ohne' else pillar}")
            zeilen.append("")
            for it in gruppen[pillar]:
                zeilen.append(f"### [{it['title']}]({it['url']})")
                meta = [t for t in (it["source"], _export_datum(it["published_at"] or it["ingested_at"]),
                                    _EXPORT_KIND.get(it["kind"], "Meldung")) if t]
                zeilen.append(f"*{' · '.join(meta)}*")
                zeilen.append("")
                if it["summary"]:
                    zeilen.append(it["summary"])
                    zeilen.append("")
                if it["note"]:
                    zeilen.append(f"> **Mein Winkel:** {it['note']}")
                    zeilen.append("")
                if it["assessment"]:
                    zeilen.append(f"> **Resümee (Relevanz {it['relevance'] or 'unbewertet'}):** {it['assessment']}")
                    zeilen.append("")
            zeilen.append("---")
            zeilen.append("")

    md = "\n".join(zeilen)
    dateiname = f"wochen-export-{heute.strftime('%Y-%m-%d')}.md"
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


@app.get("/healthz")
def healthz():
    try:
        db.ping()
        return {"ok": True}
    except Exception:
        log.exception("Healthcheck: Datenbank nicht erreichbar")
        return JSONResponse({"ok": False}, status_code=503)


app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")


def run():
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
