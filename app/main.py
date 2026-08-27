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

import json  # noqa: E402
import logging  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from collections import deque  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi import Depends, FastAPI, HTTPException, Request, Response  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app import auth, db, pruefer, transform  # noqa: E402

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


# Inhaltsregel für den Browser. Die Oberfläche lädt nichts von fremden
# Servern, deshalb reicht überall 'self'. 'unsafe-inline' bleibt nötig, weil
# CSS und JS direkt in index.html stehen (bewusste Entscheidung: kein
# Build-Schritt). Der eigentliche Gewinn ist connect-src: Selbst wenn doch
# einmal Fremdcode liefe, könnte er nichts nach draußen schicken.
CSP = ("default-src 'self'; "
       "script-src 'self' 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; "
       "connect-src 'self'; "
       "form-action 'self'; "
       "base-uri 'none'; "
       "object-src 'none'; "
       "frame-ancestors 'none'")


def _ist_https(request: Request) -> bool:
    return (request.headers.get("x-forwarded-proto") or request.url.scheme) == "https"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", CSP)
    # Verschlüsselungszwang nur über HTTPS setzen: Lokal (http://127.0.0.1)
    # würde der Browser den Entwicklungs-Port sonst dauerhaft auf HTTPS
    # umbiegen und die lokale Entwicklung lahmlegen.
    if _ist_https(request):
        response.headers.setdefault("Strict-Transport-Security",
                                    "max-age=31536000; includeSubDomains")
    return response


# Wie viele Einträge in X-Forwarded-For stammen von EIGENEN Proxys? In
# Produktion hängt Coolifys Traefik genau einen an; ohne Proxy davor: 0.
TRUSTED_PROXY_HOPS = max(0, int(os.environ.get("TRUSTED_PROXY_HOPS", "1")))


def client_ip(request: Request) -> str:
    """Absender-Adresse für die Login-Drossel.

    Von RECHTS zählen. Nur die Einträge, die unsere eigenen Proxys angehängt
    haben, sind vertrauenswürdig; alles links davon hat der Aufrufer selbst
    in den Header geschrieben. Wer den ERSTEN Eintrag nimmt, lässt sich die
    Drossel mit einem frei erfundenen Wert pro Versuch aushebeln — dann
    zählt jeder Fehlversuch auf ein anderes Konto und die Sperre greift nie.
    """
    if TRUSTED_PROXY_HOPS:
        kette = [t.strip() for t in request.headers.get("x-forwarded-for", "").split(",")
                 if t.strip()]
        if len(kette) >= TRUSTED_PROXY_HOPS:
            return kette[-TRUSTED_PROXY_HOPS]
    return request.client.host if request.client else "?"


def require_session(request: Request):
    token = request.cookies.get(auth.SESSION_COOKIE, "")
    if not auth.verify_session_token(token):
        raise HTTPException(status_code=401, detail="Nicht angemeldet")


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    return header[7:].strip() if header.lower().startswith("bearer ") else ""


class _Stundenfenster:
    """Gleitendes Stundenfenster im Arbeitsspeicher.

    Zweite Schicht hinter einem Maschinen-Token: Wird einer bekannt, erzeugt
    er begrenzten Schaden statt unbegrenztem. Bewusst pro Prozess und ohne
    Persistenz — die App läuft als einzelner uvicorn-Worker.
    """

    def __init__(self, limit):
        self.limit = limit
        self._lock = threading.Lock()
        self._treffer = deque()

    def frei(self) -> bool:
        """True und zählt den Aufruf mit, solange noch Platz im Fenster ist."""
        jetzt = time.monotonic()
        with self._lock:
            while self._treffer and jetzt - self._treffer[0] > 3600:
                self._treffer.popleft()
            if len(self._treffer) >= self.limit:
                return False
            self._treffer.append(jetzt)
            return True

    def clear(self):
        """Fenster leeren. Fuer Tests, damit sie sich nicht gegenseitig zaehlen."""
        with self._lock:
            self._treffer.clear()


# Drossel für Dienst-Token-Aufrufe: nur die kostenpflichtigen POST-Routen.
DIENST_LIMIT_PRO_STUNDE = int(os.environ.get("DIENST_LIMIT_PRO_STUNDE", "100"))
_dienst_fenster = _Stundenfenster(DIENST_LIMIT_PRO_STUNDE)

# Ingest hatte bislang gar keine Grenze: 500 Einträge je Aufruf, beliebig oft.
# Ein bekannt gewordener INGEST_TOKEN konnte damit die Datenbank volllaufen
# lassen oder gefälschte Meldungen einschleusen. n8n liefert wenige Male am
# Tag — 60 Aufrufe pro Stunde sind reichlich Luft, auch für Wiederholungen.
INGEST_LIMIT_PRO_STUNDE = int(os.environ.get("INGEST_LIMIT_PRO_STUNDE", "60"))
_ingest_fenster = _Stundenfenster(INGEST_LIMIT_PRO_STUNDE)


def require_ingest_token(request: Request):
    if not auth.verify_ingest_token(_bearer(request)):
        raise HTTPException(status_code=401, detail="Ungültiger oder fehlender Ingest-Token")
    if not _ingest_fenster.frei():
        raise HTTPException(
            status_code=429,
            detail=f"Ingest-Limit erreicht ({INGEST_LIMIT_PRO_STUNDE} Aufrufe/Stunde) — bitte später erneut versuchen")


def require_session_oder_dienst(request: Request):
    """Sitzung ODER Dienst-Token.

    Nur für den Prüfstand. Er bewertet einen übergebenen Text und hängt an
    nichts aus dieser Datenbank — deshalb darf ihn auch das Marketing-Cockpit
    rufen, das seine Launch-Beiträge sonst ungeprüft verschickt.

    Ausdrücklich NICHT auf den übrigen Routen: die geben Stefans Fundstücke,
    Notizen und Entwürfe heraus. Ein Token, der versehentlich bekannt wird,
    soll Beiträge benoten können und sonst nichts.
    """
    if auth.verify_session_token(request.cookies.get(auth.SESSION_COOKIE, "")):
        request.state.dienst = False
        return
    if auth.verify_dienst_token(_bearer(request)):
        request.state.dienst = True
        if request.method == "POST" and not _dienst_fenster.frei():
            # nur die kostenpflichtigen Routen drosseln
            raise HTTPException(
                status_code=429,
                detail=f"Prüfdienst-Limit erreicht ({DIENST_LIMIT_PRO_STUNDE} Aufrufe/Stunde) — bitte später erneut versuchen")
        try:
            db.dienst_zaehlen(request.url.path.rsplit("/", 1)[-1])
        except Exception:
            log.exception("Dienst-Tageszähler fehlgeschlagen (Aufruf läuft trotzdem weiter)")
        return
    raise HTTPException(status_code=401, detail="Nicht angemeldet und kein gültiger Dienst-Token")


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
    response.set_cookie(auth.SESSION_COOKIE, auth.create_session_token(),
                        max_age=auth.SESSION_TTL, httponly=True,
                        samesite="lax", secure=_ist_https(request), path="/")
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
    # Verwertungs-Kennzeichnung: hat ein Fund gespeicherte/gepostete Entwürfe?
    flags = db.draft_flags([it["id"] for it in items])
    for it in items:
        it["verwertet"] = flags.get(it["id"], "")
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


class PruefBody(BaseModel):
    entwurf: str
    pruefer: str  # 'ronny', 'claudia' oder 'markus'
    art: str = "beitrag"  # 'beitrag' oder 'seite' — die Lesesituation der Persona


class UeberarbeitenBody(BaseModel):
    entwurf: str
    feedback: list[dict]  # [{name, rolle, score, feedback}, ...]
    anweisung: str = ""   # Stefans Regie-Anweisung, hat Vorrang vor dem Feedback


@app.get("/api/pruefer", dependencies=[Depends(require_session_oder_dienst)])
def pruefer_liste():
    """Wer steht im Prüfstand. Damit ein anderer Dienst die Personas nicht fest
    verdrahten muss und eine vierte hier automatisch dort ankommt."""
    return {"pruefer": [{"schluessel": k, "name": v["name"], "rolle": v["rolle"]}
                        for k, v in pruefer.PRUEFER.items()]}


# Rückfluss: extern geprüfte LinkedIn-Beiträge landen (dedupliziert über den
# Text) in der Entwurfs-Bibliothek — abschaltbar mit DIENST_RUECKFLUSS=0.
# Landingpages (art=seite) bleiben bewusst draußen: das ist keine LinkedIn-Bibliothek.
DIENST_RUECKFLUSS = os.environ.get("DIENST_RUECKFLUSS", "1") != "0"


def _rueckfluss_beitrag(entwurf, ergebnis):
    """Legt den Beitrag als Bibliotheks-Entwurf an bzw. ergänzt den Score der Persona."""
    try:
        eintrag = {"pruefer": ergebnis["pruefer"], "name": ergebnis["name"], "score": ergebnis["score"]}
        vorhanden = db.find_draft_by_text(entwurf)
        if vorhanden:
            try:
                scores = json.loads(vorhanden["scores"] or "[]")
            except ValueError:
                scores = []
            scores = [s for s in scores if s.get("pruefer") != eintrag["pruefer"]] + [eintrag]
            db.update_draft(vorhanden["id"], scores=json.dumps(scores[:8]))
        else:
            db.insert_draft(entwurf, item_title="Prüfdienst (extern)",
                            scores=json.dumps([eintrag]))
    except Exception:
        log.exception("Rückfluss in die Entwurfs-Bibliothek fehlgeschlagen (Prüfung selbst war erfolgreich)")


@app.post("/api/pruefen", dependencies=[Depends(require_session_oder_dienst)])
def pruefen(body: PruefBody, request: Request):
    if not body.entwurf.strip():
        raise HTTPException(status_code=400, detail="Kein Entwurf übergeben")
    if body.art not in ("beitrag", "seite"):
        raise HTTPException(status_code=400, detail="art muss 'beitrag' oder 'seite' sein")
    try:
        ergebnis = pruefer.pruefen(body.entwurf, body.pruefer, body.art)
    except pruefer.TransformError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    if (DIENST_RUECKFLUSS and body.art == "beitrag"
            and getattr(request.state, "dienst", False)):
        _rueckfluss_beitrag(body.entwurf.strip(), ergebnis)
    return ergebnis


@app.post("/api/ueberarbeiten", dependencies=[Depends(require_session_oder_dienst)])
def ueberarbeiten(body: UeberarbeitenBody):
    if not body.entwurf.strip():
        raise HTTPException(status_code=400, detail="Kein Entwurf übergeben")
    if not body.feedback:
        raise HTTPException(status_code=400, detail="Kein Feedback übergeben")
    try:
        return {"draft": transform.ueberarbeiten(body.entwurf, body.feedback, body.anweisung)}
    except transform.TransformError as e:
        raise HTTPException(status_code=e.status, detail=str(e))


class DraftBody(BaseModel):
    text: str
    item_id: int | None = None
    item_title: str = ""
    scores: list[dict] = []  # [{pruefer, name, score}, ...] — Schnappschuss


class DraftPatchBody(BaseModel):
    text: str | None = None
    scores: list[dict] | None = None
    status: str | None = None  # 'entwurf' oder 'gepostet'


def _draft_out(d):
    try:
        d["scores"] = json.loads(d["scores"] or "[]")
    except ValueError:
        d["scores"] = []
    return d


@app.get("/api/drafts", dependencies=[Depends(require_session)])
def get_drafts():
    return {"items": [_draft_out(d) for d in db.list_drafts()], "counts": db.counts()}


@app.post("/api/drafts", dependencies=[Depends(require_session)])
def create_draft(body: DraftBody):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Leerer Entwurf")
    d = db.insert_draft(body.text, item_id=body.item_id,
                        item_title=body.item_title.strip()[:300],
                        scores=json.dumps(body.scores[:8]))
    return JSONResponse(status_code=201, content=_draft_out(d))


@app.patch("/api/drafts/{draft_id}", dependencies=[Depends(require_session)])
def patch_draft(draft_id: int, body: DraftPatchBody):
    if body.status is not None and body.status not in db.DRAFT_STATUS:
        raise HTTPException(status_code=400, detail="status muss 'entwurf' oder 'gepostet' sein")
    if body.text is not None and not body.text.strip():
        raise HTTPException(status_code=400, detail="Leerer Entwurf")
    if not db.get_draft(draft_id):
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    d = db.update_draft(draft_id, text=body.text,
                        scores=json.dumps(body.scores[:8]) if body.scores is not None else None,
                        status=body.status)
    # Automatismus: "gepostet" heißt verarbeitet — der Quell-Fund wandert
    # aus dem Posteingang ins Archiv (Rücknahme bewusst manuell).
    item_archiviert = False
    if body.status == "gepostet" and d.get("item_id"):
        item = db.get_item(d["item_id"])
        if item and item["status"] == "new":
            db.update_item(d["item_id"], status="archived")
            item_archiviert = True
    return {**_draft_out(d), "item_archiviert": item_archiviert}


@app.delete("/api/drafts/{draft_id}", dependencies=[Depends(require_session)])
def delete_draft(draft_id: int):
    if not db.delete_draft(draft_id):
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return {"ok": True}


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


# Versionskennung: Coolify setzt SOURCE_COMMIT beim Build; Fallback ist die
# Container-Startzeit (jedes Deployment startet den Container neu). Das
# Frontend vergleicht dagegen und bietet bei Abweichung "Neu laden" an —
# ein offenes PWA-Fenster bekäme neue Deployments sonst nie mit.
APP_BUILD = (os.environ.get("SOURCE_COMMIT") or "").strip()[:12] or f"start-{db.utcnow_iso()}"


@app.get("/api/version")
def version():
    return {"build": APP_BUILD}


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
