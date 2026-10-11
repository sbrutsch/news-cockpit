"""Rückkanal von ContentIn: Zuordnung, Markieren, Kennzahlen, Idempotenz, Zugang.

Kein Netz: `FakeClient` spielt den MCP-Server auf Werkzeug-Ebene; für den
Protokoll-Test wird `_transport` durch eine Attrappe ersetzt.
"""

import json
import os

import pytest

from app import contentin, db, main

AUSZUG = ("<p>Zweites Quartal in Folge wird das Budget f&uuml;r Ihr Projekt gek&uuml;rzt. "
          "Vor sechs Monaten war der Vorstand noch begeistert.<br><br>Zwei K&uuml;rzungsrunden…")
ENTWURF = ("Zweites Quartal in Folge wird das Budget für Ihr Projekt gekürzt. Vor sechs Monaten "
           "war der Vorstand noch begeistert, jetzt schießt der CFO quer.")
VARIANTE = ("Zweites Quartal in Folge kürzt die Geschäftsführung Ihr Projektbudget. "
            "Im letzten Jahr war das anders.")
KENNZAHLEN = {"impressions": 137, "members_reached": 95, "likes": 4, "comments": 0,
              "shares": 0, "engagement": 2.92}


@pytest.fixture(autouse=True)
def pausen(monkeypatch):
    """Kein echtes Schlafen in Tests — nur mitschreiben, wie lange gewartet würde."""
    protokoll = []
    monkeypatch.setattr(contentin, "_warten", protokoll.append)
    return protokoll


class FakeClient:
    def __init__(self, posts, metrics=None):
        self.posts, self.metrics = posts, metrics or {}
        self.aufrufe = []

    def werkzeug(self, name, argumente):
        self.aufrufe.append((name, argumente))
        if name == "list_posts":
            return {"posts": self.posts}
        if name == "get_post_analytics":
            pid = argumente["post_id"]
            if pid in self.metrics:
                return {"measured": True, "metrics": self.metrics[pid]}
            return {"measured": False}
        raise AssertionError("unerwartetes Werkzeug " + name)


def _fund_und_entwurf(text=ENTWURF):
    db.insert_item("Fund", "https://example.org/fund", kind="idee")
    item = db.list_items(tab="new")[0]
    entwurf = db.insert_draft(text, item_id=item["id"], item_title=item["title"])
    return item, entwurf


def test_zuordnung_ueber_textanfang():
    """HTML, Entities und Typografie stören nicht; eine Textvariante passt nicht."""
    assert contentin.passt(AUSZUG, ENTWURF)
    assert not contentin.passt(AUSZUG, VARIANTE)
    assert not contentin.passt("<p>Kurz</p>", "Kurz"), "zu wenig Text für ein Urteil"


def test_abgleich_markiert_speichert_und_archiviert():
    item, entwurf = _fund_und_entwurf()
    client = FakeClient(
        posts=[{"post_id": 42, "excerpt": AUSZUG, "posted_at": "2026-10-07T05:45:16"}],
        metrics={42: KENNZAHLEN})

    ergebnis = contentin.abgleich(client)

    assert (ergebnis["zugeordnet"], ergebnis["neu_gepostet"], ergebnis["archiviert"]) == (1, 1, 1)
    neu = db.get_draft(entwurf["id"])
    assert neu["status"] == "gepostet"
    assert neu["contentin_post_id"] == 42
    assert neu["veroeffentlicht_am"] == "2026-10-07T05:45:16"
    assert json.loads(neu["kennzahlen"])["impressions"] == 137
    assert db.get_item(item["id"])["status"] == "archived"
    assert db.draft_flags([item["id"]]) == {item["id"]: "gepostet"}


def test_abgleich_ist_idempotent_und_holt_alte_kennzahlen_nur_einmal():
    _, entwurf = _fund_und_entwurf()
    alt = {"post_id": 7, "excerpt": AUSZUG, "posted_at": "2026-01-05T06:00:00"}
    client = FakeClient([alt], {7: KENNZAHLEN})

    erster = contentin.abgleich(client)
    zweiter = contentin.abgleich(client)

    assert erster["neu_gepostet"] == 1
    assert (zweiter["neu_gepostet"], zweiter["archiviert"]) == (0, 0)
    analytics = [a for a in client.aufrufe if a[0] == "get_post_analytics"]
    assert len(analytics) == 1, "Kennzahlen eines alten Beitrags werden nur einmal geholt"
    assert db.get_draft(entwurf["id"])["status"] == "gepostet"


def test_beitrag_ohne_entwurf_wird_nur_gezaehlt():
    client = FakeClient([{"post_id": 1, "posted_at": "2026-04-01T06:00:00",
                          "excerpt": "<p>Ein Beitrag, den das Cockpit nie gesehen hat, aus einer anderen Zeit.</p>"}])

    ergebnis = contentin.abgleich(client)

    assert (ergebnis["ohne_entwurf"], ergebnis["zugeordnet"]) == (1, 0)
    assert not any(a[0] == "get_post_analytics" for a in client.aufrufe), "ohne Entwurf keine Kennzahlen-Abfrage"


def test_sync_endpunkt_zugang_und_schalter(client, monkeypatch):
    assert client.post("/api/sync/contentin").status_code == 401

    ingest = {"Authorization": "Bearer " + os.environ["INGEST_TOKEN"]}
    monkeypatch.delenv("CONTENTIN_MCP_KEY", raising=False)
    assert client.post("/api/sync/contentin", headers=ingest).status_code == 503

    monkeypatch.setenv("CONTENTIN_MCP_KEY", "cimcp_test")
    monkeypatch.setattr(main.contentin, "Client", lambda key, **kw: FakeClient([]))
    antwort = client.post("/api/sync/contentin", headers=ingest)
    assert antwort.status_code == 200
    assert antwort.json()["beitraege"] == 0
    assert db.sync_zuletzt("contentin")["zuletzt"]


def test_mcp_client_liest_sse_und_fuehrt_session_mit(monkeypatch):
    gesendet = []

    def fake_transport(url, headers, body, timeout):
        gesendet.append((headers, body))
        methode = body.get("method")
        if methode == "initialize":
            return ({"Mcp-Session-Id": "s-1", "Content-Type": "text/event-stream"},
                    "event: message\ndata: " + json.dumps(
                        {"jsonrpc": "2.0", "id": body["id"], "result": {"protocolVersion": "2025-03-26"}})
                    + "\n\n")
        if methode == "notifications/initialized":
            return ({"Content-Type": "text/plain"}, "")
        if methode == "tools/call":
            inhalt = json.dumps({"posts": [{"post_id": 5}]})
            return ({"Content-Type": "application/json"},
                    json.dumps({"jsonrpc": "2.0", "id": body["id"],
                                "result": {"content": [{"type": "text", "text": inhalt}]}}))
        raise AssertionError(body)

    monkeypatch.setattr(contentin, "_transport", fake_transport)
    c = contentin.Client("cimcp_test")

    assert c.werkzeug("list_posts", {"status": ["posted"]}) == {"posts": [{"post_id": 5}]}
    assert gesendet[-1][0]["Mcp-Session-Id"] == "s-1", "Session-Id aus der Initialisierung wandert mit"
    assert all(h["X-MCP-Key"] == "cimcp_test" for h, _ in gesendet)


def test_drossel_antwort_wird_abgewartet_und_wiederholt(monkeypatch, pausen):
    """Produktionsbefund vom 2026-10-11: ContentIn bremst Bursts. Nach der
    Drossel-Antwort wird gewartet und derselbe Aufruf wiederholt."""
    antworten = iter([
        {"isError": True, "content": [{"type": "text", "text":
            "Too many ContentIn requests in a few seconds. Wait about ten seconds and try again."}]},
        {"content": [{"type": "text", "text": json.dumps({"measured": True, "metrics": {"likes": 3}})}]},
    ])

    def fake_transport(url, headers, body, timeout):
        if body.get("method") == "tools/call":
            ergebnis = next(antworten)
        elif body.get("method") == "initialize":
            ergebnis = {"protocolVersion": "2025-03-26"}
        else:
            return ({"Content-Type": "text/plain"}, "")
        return ({"Content-Type": "application/json"},
                json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": ergebnis}))

    monkeypatch.setattr(contentin, "_transport", fake_transport)
    c = contentin.Client("cimcp_test")

    assert c.werkzeug("get_post_analytics", {"post_id": 1})["metrics"]["likes"] == 3
    assert contentin.DROSSEL_WARTEZEIT in pausen, "nach der Drossel-Antwort muss gewartet werden"


def test_mcp_fehler_wird_zu_contentin_error(monkeypatch):
    def fake_transport(url, headers, body, timeout):
        return ({"Content-Type": "application/json"},
                json.dumps({"jsonrpc": "2.0", "id": body.get("id", 0),
                            "error": {"code": -32001, "message": "invalid key"}}))

    monkeypatch.setattr(contentin, "_transport", fake_transport)
    with pytest.raises(contentin.ContentInError, match="invalid key"):
        contentin.Client("cimcp_falsch").werkzeug("list_posts", {})
