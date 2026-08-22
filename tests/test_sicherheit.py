"""Regressionstest zum Sicherheits-Check vom 2026-08-22.

Jeder Block hier bewacht einen Befund, der einmal offen war. Wenn eine
Prüfung rot wird, ist eine Lücke zurückgekehrt — nicht nur ein Test kaputt.

Bewusst ohne pytest, passend zum Rest des Projekts (kein Build-Schritt, so
wenig Fremdabhängigkeit wie möglich). Der Test startet die echte App gegen
eine Wegwerf-SQLite in einem temporären Ordner; er fasst weder eine
laufende Instanz noch die Produktionsdatenbank an.

    pip install -r requirements.txt -r requirements-dev.txt
    python tests/test_sicherheit.py        # Rückgabewert 0 = alles gut
"""

import os
import pathlib
import shutil
import sys
import tempfile

WURZEL = pathlib.Path(__file__).resolve().parent.parent
TMP = tempfile.mkdtemp(prefix="news-cockpit-test-")

# Muss VOR dem Import von app.* stehen: db und auth lesen ihre Umgebung
# beim Import, und main.py würde sonst eine echte .env einlesen.
os.environ.update({
    "ENV_FILE": os.path.join(TMP, "gibt-es-nicht"),
    "DATABASE_URL": f"sqlite:///{TMP}/test.db",
    "SECRET_KEY": "t" * 64,
    "INGEST_TOKEN": "test-ingest-token",
    "INGEST_LIMIT_PRO_STUNDE": "3",   # klein, damit der Test kurz bleibt
    "TRUSTED_PROXY_HOPS": "1",        # wie in Produktion hinter Coolify/Traefik
})
sys.path.insert(0, str(WURZEL))

from app import auth  # noqa: E402

PASSWORT = "test-passwort-1234"
os.environ["APP_PASSWORD_HASH"] = auth.hash_password(PASSWORT)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

_ok = _fehler = 0


def pruefe(name, bedingung, detail=""):
    global _ok, _fehler
    if bedingung:
        _ok += 1
        print(f"  [ok]   {name}")
    else:
        _fehler += 1
        print(f"  [FEHL] {name}   {detail}")


def xff(erfunden, echt="203.0.113.50"):
    """Der Header, wie ihn Traefik weiterreicht.

    Links steht, was der Aufrufer selbst geschrieben hat (frei erfunden),
    rechts hängt der Proxy die Adresse an, die er tatsächlich gesehen hat.
    Genau diese rechte Seite muss die Drossel zählen.
    """
    return f"{erfunden}, {echt}" if erfunden else echt


with TestClient(app) as c:

    print("\nBefund 1 — Login-Drossel trotz gefälschtem X-Forwarded-For")
    codes = [c.post("/api/login", json={"password": "falsch"},
                    headers={"X-Forwarded-For": xff(f"10.0.0.{i}")}).status_code
             for i in range(14)]
    pruefe("die ersten 10 Versuche werden geprüft (401)",
           codes[:auth.MAX_ATTEMPTS] == [401] * auth.MAX_ATTEMPTS, codes[:10])
    pruefe("danach gesperrt (429), obwohl jeder Versuch eine neue Adresse vorgibt",
           all(x == 429 for x in codes[auth.MAX_ATTEMPTS:]), codes[10:])
    pruefe("ein anderer ECHTER Absender wird nicht mitgesperrt",
           c.post("/api/login", json={"password": "falsch"},
                  headers={"X-Forwarded-For": xff("10.0.0.99", echt="198.51.100.7")}
                  ).status_code == 401)

    print("\nBefund 2 — signierter Cookie-Inhalt ist nicht vorhersagbar")
    t1, t2 = auth.create_session_token(now=1000), auth.create_session_token(now=1000)
    pruefe("zwei Cookies zur selben Sekunde sind verschieden", t1 != t2)
    pruefe("frisches Cookie ist gültig",
           auth.verify_session_token(auth.create_session_token()))
    pruefe("verändertes Cookie wird abgewiesen",
           not auth.verify_session_token(t1[:-3] + "AAA"))
    pruefe("abgelaufenes Cookie wird abgewiesen",
           not auth.verify_session_token(auth.create_session_token(now=1)))

    print("\nBefund 3 — Passwortwechsel beendet offene Sitzungen")
    cookie = auth.create_session_token()
    pruefe("Cookie vor dem Wechsel gültig", auth.verify_session_token(cookie))
    auth._session_key_cache = auth._pw_hash_cache = None
    os.environ["APP_PASSWORD_HASH"] = auth.hash_password("ein-anderes-passwort")
    pruefe("Cookie nach dem Wechsel UNGÜLTIG", not auth.verify_session_token(cookie))
    auth._session_key_cache = auth._pw_hash_cache = None
    os.environ["APP_PASSWORD_HASH"] = auth.hash_password(PASSWORT)

    print("\nBefund 4 — Ingest-Drossel (Testlimit 3 pro Stunde)")
    kopf = {"Authorization": "Bearer test-ingest-token"}
    codes = [c.post("/api/ingest", headers=kopf,
                    json={"title": f"Titel {i}", "url": f"https://example.invalid/{i}"}
                    ).status_code for i in range(5)]
    pruefe("die ersten 3 Aufrufe gehen durch", all(x in (200, 201) for x in codes[:3]), codes[:3])
    pruefe("ab dem 4. Aufruf 429", all(x == 429 for x in codes[3:]), codes[3:])
    pruefe("falscher Ingest-Token bleibt 401",
           c.post("/api/ingest", headers={"Authorization": "Bearer falsch"},
                  json={"title": "x", "url": "https://example.invalid/x"}
                  ).status_code == 401)

    print("\nBefund 7 — Schutz-Header")
    r = c.get("/healthz")
    csp = r.headers.get("content-security-policy", "")
    pruefe("CSP wird gesetzt", bool(csp))
    pruefe("CSP verbietet Verbindungen nach draußen", "connect-src 'self'" in csp, csp)
    pruefe("CSP verbietet das Einbetten in fremde Seiten", "frame-ancestors 'none'" in csp, csp)
    pruefe("die drei älteren Header sind unverändert da",
           r.headers.get("x-content-type-options") == "nosniff"
           and r.headers.get("x-frame-options") == "DENY"
           and r.headers.get("referrer-policy") == "no-referrer")
    pruefe("HSTS NICHT über http — sonst wäre die lokale Entwicklung kaputt",
           "strict-transport-security" not in r.headers)
    pruefe("HSTS über https gesetzt",
           "max-age=" in c.get("/healthz", headers={"X-Forwarded-Proto": "https"}
                               ).headers.get("strict-transport-security", ""))

    print("\nGrundregel A — ohne Anmeldung gibt keine Route Daten heraus")
    c.cookies.clear()
    for pfad in ("/api/items", "/api/drafts", "/api/export?days=7", "/api/me",
                 "/api/pruefer"):
        pruefe(f"{pfad} ohne Cookie -> 401", c.get(pfad).status_code == 401)
    pruefe("/healthz bleibt absichtlich offen", c.get("/healthz").status_code == 200)
    pruefe("/api/version bleibt absichtlich offen", c.get("/api/version").status_code == 200)

    print("\nDie Anmeldung selbst funktioniert unverändert")
    r = c.post("/api/login", json={"password": PASSWORT},
               headers={"X-Forwarded-For": xff(None, echt="198.51.100.200")})
    pruefe("Login mit richtigem Passwort", r.status_code == 200, r.text[:120])
    cookie_kopf = r.headers.get("set-cookie", "")
    pruefe("Cookie ist HttpOnly", "HttpOnly" in cookie_kopf, cookie_kopf)
    pruefe("Cookie ist SameSite=lax", "SameSite=lax" in cookie_kopf, cookie_kopf)
    pruefe("Cookie über http OHNE Secure-Flag (sonst ginge lokal keine Anmeldung)",
           "Secure" not in cookie_kopf, cookie_kopf)
    pruefe("/api/items nach dem Login erreichbar", c.get("/api/items").status_code == 200)
    pruefe("/api/drafts nach dem Login erreichbar", c.get("/api/drafts").status_code == 200)
    pruefe("/api/export nach dem Login erreichbar",
           c.get("/api/export?days=7").status_code == 200)
    pruefe("Oberfläche wird ausgeliefert", c.get("/").status_code == 200)

    c.cookies.clear()
    r = c.post("/api/login", json={"password": PASSWORT},
               headers={"X-Forwarded-For": xff(None, echt="198.51.100.201"),
                        "X-Forwarded-Proto": "https"})
    pruefe("Cookie über https MIT Secure-Flag",
           "Secure" in r.headers.get("set-cookie", ""))

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'=' * 60}\n{_ok} bestanden, {_fehler} fehlgeschlagen\n{'=' * 60}")
sys.exit(1 if _fehler else 0)
