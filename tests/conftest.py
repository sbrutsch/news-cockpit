"""Gemeinsame Einrichtung für die Tests.

WICHTIG — Reihenfolge: `db`, `auth` und `main` lesen ihre Umgebung beim
IMPORT (`db.py` DATABASE_URL, `auth.py` SECRET_KEY, `main.py`
DIENST_LIMIT_PRO_STUNDE). Ein `monkeypatch.setenv` in einer Fixture käme zu
spät — deshalb steht der Umgebungsblock hier ganz oben, vor jedem
`app.*`-Import.

Bewusst NICHT getestet:
  * Alles, was die Claude-API ruft (`transform.py`, `pruefer.pruefen` selbst).
    Tests sollen ohne Netz und ohne Kosten laufen; ANTHROPIC_API_KEY wird
    unten aus der Umgebung entfernt, damit ein versehentlicher echter Aufruf
    auffällt statt Geld zu kosten.
  * Die Postgres-Variante — dafür wäre ein Container nötig. Geprüft wird das
    Schema über `db.init()` in SQLite.
"""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="news-cockpit-tests-")

# ENV_FILE zeigt bewusst ins Leere: main._load_env_file() darf die echte .env
# des Entwicklungsrechners nicht anfassen.
os.environ["ENV_FILE"] = os.path.join(_TMP, "keine.env")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP, "test.db")
os.environ["SECRET_KEY"] = "test-schluessel-ohne-bedeutung"
os.environ["INGEST_TOKEN"] = "test-ingest-token"
os.environ["DIENST_TOKEN"] = "test-dienst-token"
os.environ["APP_PASSWORD"] = "test-passwort"
# Klein genug, dass der Drossel-Test drei Aufrufe braucht statt 101.
os.environ["DIENST_LIMIT_PRO_STUNDE"] = "2"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth, db, main  # noqa: E402

db.init()


@pytest.fixture(autouse=True)
def sauberer_zustand():
    """Jeder Test startet mit leeren Tabellen und leerem Drossel-Fenster.

    `_dienst_fenster` ist modulglobal und überlebt sonst von Test zu Test.
    """
    with db.cursor() as cur:
        for tabelle in ("items", "drafts", "dienst_log"):
            cur.execute("DELETE FROM " + tabelle)
    main._dienst_fenster.clear()
    yield
    main._dienst_fenster.clear()


@pytest.fixture
def client():
    """Nicht angemeldet."""
    return TestClient(main.app)


@pytest.fixture
def sitzung():
    """Angemeldet — eigener Client, damit `client` unangemeldet bleibt."""
    c = TestClient(main.app)
    c.cookies.set(auth.SESSION_COOKIE, auth.create_session_token())
    return c


@pytest.fixture
def dienst():
    """Authorization-Header für Maschinen-Aufrufe."""
    return {"Authorization": "Bearer " + os.environ["DIENST_TOKEN"]}


@pytest.fixture
def pruefer_stub(monkeypatch):
    """Ersetzt den Claude-Aufruf und protokolliert, wie oft er wirklich lief."""
    aufrufe = []

    def fake(entwurf, key, art="beitrag"):
        aufrufe.append((entwurf, key, art))
        return {"pruefer": key, "name": key.capitalize(), "rolle": "Test",
                "score": 7, "feedback": "Teststimme", "dimensionen": []}

    monkeypatch.setattr(main.pruefer, "pruefen", fake)
    return aufrufe
