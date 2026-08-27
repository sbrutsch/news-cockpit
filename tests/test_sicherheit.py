"""Regressionstest zum Sicherheits-Check vom 2026-08-22.

Jeder Test hier bewacht einen Befund, der einmal offen war. Wird einer rot,
ist eine Lücke zurückgekehrt — nicht nur ein Test kaputt.

Ursprünglich ein eigenständiges Skript mit Rückgabewert 0/1, „bewusst ohne
pytest, passend zum Rest des Projekts". Seit dem 2026-08-26 hat das Projekt
`pytest` und eine CI; damit die Prüfungen bei jedem Push mitlaufen statt nur
auf Zuruf, sind sie hier umgestellt. Umgebung und Aufräumen kommen aus
`tests/conftest.py`.
"""

import pytest

from app import auth, main

PASSWORT = "test-passwort"  # wie in conftest.py gesetzt


def xff(erfunden, echt="203.0.113.50"):
    """Der Header, wie ihn Traefik weiterreicht.

    Links steht, was der Aufrufer selbst geschrieben hat (frei erfunden),
    rechts hängt der Proxy die Adresse an, die er tatsächlich gesehen hat.
    Genau diese rechte Seite muss die Drossel zählen.
    """
    return f"{erfunden}, {echt}" if erfunden else echt


# --- Befund 1: Login-Drossel war über X-Forwarded-For umgehbar ---------------

def test_login_drossel_greift_trotz_gefaelschtem_header(client):
    """`client_ip()` nahm den ERSTEN Eintrag — den schreibt der Aufrufer selbst."""
    codes = [client.post("/api/login", json={"password": "falsch"},
                         headers={"X-Forwarded-For": xff(f"10.0.0.{i}")}).status_code
             for i in range(auth.MAX_ATTEMPTS + 4)]

    assert codes[:auth.MAX_ATTEMPTS] == [401] * auth.MAX_ATTEMPTS, codes
    assert all(c == 429 for c in codes[auth.MAX_ATTEMPTS:]), codes


def test_anderer_echter_absender_wird_nicht_mitgesperrt(client):
    """Die Sperre darf nur den treffen, der sie ausgelöst hat."""
    for i in range(auth.MAX_ATTEMPTS + 2):
        client.post("/api/login", json={"password": "falsch"},
                    headers={"X-Forwarded-For": xff(f"10.0.0.{i}")})

    antwort = client.post("/api/login", json={"password": "falsch"},
                          headers={"X-Forwarded-For": xff("10.0.0.99",
                                                          echt="198.51.100.7")})
    assert antwort.status_code == 401


# --- Befund 2: signierter Klartext war vorhersagbar --------------------------

def test_cookie_inhalt_ist_nicht_vorhersagbar():
    """Vorher stand dort nur ein Unix-Zeitstempel — offline durchprobierbar."""
    assert auth.create_session_token(now=1000) != auth.create_session_token(now=1000)


def test_cookie_pruefung_haelt_bei_manipulation_und_ablauf():
    """Der Zufallsanteil hat das Payload-Format geändert — hier die Gegenprobe."""
    assert auth.verify_session_token(auth.create_session_token()) is True
    verfaelscht = auth.create_session_token()[:-3] + "AAA"
    assert auth.verify_session_token(verfaelscht) is False
    assert auth.verify_session_token(auth.create_session_token(now=1)) is False
    assert auth.verify_session_token("kein.gueltiges.token") is False


# --- Befund 3: Sitzungen hingen nicht am Passwort ----------------------------

def test_passwortwechsel_beendet_offene_sitzungen(monkeypatch):
    """Ein gestohlenes Cookie galt 30 Tage weiter, auch nach neuem Passwort."""
    cookie = auth.create_session_token()
    assert auth.verify_session_token(cookie) is True

    monkeypatch.setenv("APP_PASSWORD", "ein-anderes-passwort")
    auth._session_key_cache = auth._pw_hash_cache = None
    assert auth.verify_session_token(cookie) is False

    # Zurück auf das alte Passwort: dasselbe Cookie gilt wieder.
    monkeypatch.setenv("APP_PASSWORD", PASSWORT)
    auth._session_key_cache = auth._pw_hash_cache = None
    assert auth.verify_session_token(cookie) is True


# --- Befund 4: Ingest hatte keine Mengengrenze -------------------------------

def test_ingest_drossel(client):
    """500 Einträge je Aufruf, beliebig oft — jetzt INGEST_LIMIT_PRO_STUNDE."""
    limit = main.INGEST_LIMIT_PRO_STUNDE
    kopf = {"Authorization": "Bearer test-ingest-token"}
    codes = [client.post("/api/ingest", headers=kopf,
                         json={"title": f"Titel {i}",
                               "url": f"https://example.invalid/{i}"}).status_code
             for i in range(limit + 2)]

    assert all(c in (200, 201) for c in codes[:limit]), codes
    assert all(c == 429 for c in codes[limit:]), codes


def test_falscher_ingest_token_bleibt_401(client):
    assert client.post("/api/ingest", headers={"Authorization": "Bearer falsch"},
                       json={"title": "x", "url": "https://example.invalid/x"}
                       ).status_code == 401


# --- Befund 5: Schutz-Header -------------------------------------------------

def test_schutz_header(client):
    kopf = client.get("/healthz").headers
    csp = kopf.get("content-security-policy", "")

    assert csp, "CSP fehlt"
    assert "connect-src 'self'" in csp, csp
    assert "frame-ancestors 'none'" in csp, csp
    assert kopf.get("x-content-type-options") == "nosniff"
    assert kopf.get("x-frame-options") == "DENY"
    assert kopf.get("referrer-policy") == "no-referrer"


def test_hsts_nur_ueber_https(client):
    """Über http gesetzt, würde der Browser den lokalen Port dauerhaft umbiegen."""
    assert "strict-transport-security" not in client.get("/healthz").headers

    ueber_https = client.get("/healthz", headers={"X-Forwarded-Proto": "https"})
    assert "max-age=" in ueber_https.headers.get("strict-transport-security", "")


# --- Grundregel: ohne Anmeldung gibt keine Route Daten heraus ----------------

@pytest.mark.parametrize("pfad", ["/api/items", "/api/drafts", "/api/export?days=7",
                                  "/api/me", "/api/pruefer"])
def test_ohne_anmeldung_keine_daten(client, pfad):
    assert client.get(pfad).status_code == 401


@pytest.mark.parametrize("pfad", ["/healthz", "/api/version"])
def test_bewusst_offene_routen(client, pfad):
    assert client.get(pfad).status_code == 200


# --- Die Anmeldung selbst funktioniert unverändert ---------------------------

def test_anmeldung_und_cookie_flags(client):
    antwort = client.post("/api/login", json={"password": PASSWORT},
                          headers={"X-Forwarded-For": xff(None, echt="198.51.100.200")})
    assert antwort.status_code == 200, antwort.text[:120]

    cookie = antwort.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie, cookie
    assert "SameSite=lax" in cookie, cookie
    assert "Secure" not in cookie, "über http kein Secure — sonst geht lokal nichts"

    for pfad in ("/api/items", "/api/drafts", "/api/export?days=7"):
        assert client.get(pfad).status_code == 200, pfad
    assert client.get("/").status_code == 200


def test_cookie_ueber_https_mit_secure_flag(client):
    antwort = client.post("/api/login", json={"password": PASSWORT},
                          headers={"X-Forwarded-For": xff(None, echt="198.51.100.201"),
                                   "X-Forwarded-Proto": "https"})
    assert "Secure" in antwort.headers.get("set-cookie", "")
