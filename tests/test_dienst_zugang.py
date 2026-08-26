"""Der Prüfstand als Maschinen-Schnittstelle: Zugang, Drossel, Rückfluss.

Jeder Test hier sichert eine Zeile ab, die im Änderungsprotokoll der CLAUDE.md
unter 2026-08-20 (2) als „getestet" steht — bisher aber nur von Hand geprüft
war und danach verfallen ist.
"""

import json

from app import db, main

BEITRAG = {"entwurf": "Ein Entwurf, der geprüft werden will.", "pruefer": "ronny"}


def test_drossel_ab_limit_plus_eins(client, dienst, pruefer_stub):
    """POSTs mit Dienst-Token laufen bis zum Limit, der nächste bekommt 429."""
    limit = main.DIENST_LIMIT_PRO_STUNDE
    for _ in range(limit):
        assert client.post("/api/pruefen", json=BEITRAG, headers=dienst).status_code == 200

    antwort = client.post("/api/pruefen", json=BEITRAG, headers=dienst)
    assert antwort.status_code == 429
    assert "Limit" in antwort.json()["detail"]
    # Der abgewiesene Aufruf darf Claude gar nicht erst erreicht haben —
    # genau dafür sitzt die Drossel vor dem teuren Teil.
    assert len(pruefer_stub) == limit


def test_get_zaehlt_ohne_drossel(client, dienst):
    """Gedrosselt wird nur POST; GET bleibt offen, wird aber mitgezählt."""
    aufrufe = main.DIENST_LIMIT_PRO_STUNDE + 3
    for _ in range(aufrufe):
        assert client.get("/api/pruefer", headers=dienst).status_code == 200

    assert db.counts()["dienst_heute"] == aufrufe


def test_sitzung_wird_nicht_gedrosselt(sitzung, pruefer_stub):
    """Stefans eigene UI läuft an Drossel und Tageszähler vorbei."""
    for _ in range(main.DIENST_LIMIT_PRO_STUNDE + 2):
        assert sitzung.post("/api/pruefen", json=BEITRAG).status_code == 200

    assert db.counts()["dienst_heute"] == 0


def test_art_wird_validiert(client, sitzung):
    """`art` kennt genau zwei Werte — und ohne Auth kommt niemand überhaupt hin."""
    falsch = dict(BEITRAG, art="unsinn")
    assert sitzung.post("/api/pruefen", json=falsch).status_code == 400

    assert client.post("/api/pruefen", json=BEITRAG).status_code == 401


def test_landingpage_bleibt_aus_der_bibliothek(client, dienst, pruefer_stub):
    """`art=seite` wird geprüft, landet aber bewusst nicht in der Bibliothek.

    Die Entwurfs-Bibliothek ist eine LinkedIn-Bibliothek; die beiden Skalen
    (Leseverhalten vs. Kaufnähe) sind ohnehin nicht vergleichbar.
    """
    seite = dict(BEITRAG, entwurf="Eine Landingpage.", art="seite")
    assert client.post("/api/pruefen", json=seite, headers=dienst).status_code == 200
    assert db.list_drafts() == []

    beitrag = dict(BEITRAG, entwurf="Ein echter Beitrag.", art="beitrag")
    assert client.post("/api/pruefen", json=beitrag, headers=dienst).status_code == 200
    entwuerfe = db.list_drafts()
    assert len(entwuerfe) == 1
    assert entwuerfe[0]["item_title"] == "Prüfdienst (extern)"


def test_rueckfluss_dedupliziert_und_ersetzt_je_persona():
    """Dieselbe Persona ersetzt ihren Score, eine zweite kommt daneben."""
    text = "Derselbe Beitrag, mehrfach geprüft."
    main._rueckfluss_beitrag(text, {"pruefer": "ronny", "name": "Ronny Berger", "score": 6})
    main._rueckfluss_beitrag(text, {"pruefer": "ronny", "name": "Ronny Berger", "score": 9})

    entwuerfe = db.list_drafts()
    assert len(entwuerfe) == 1, "gleicher Text darf keinen zweiten Entwurf anlegen"
    scores = json.loads(entwuerfe[0]["scores"])
    assert [(s["pruefer"], s["score"]) for s in scores] == [("ronny", 9)]

    main._rueckfluss_beitrag(text, {"pruefer": "markus", "name": "Markus Leitner", "score": 5})

    entwuerfe = db.list_drafts()
    assert len(entwuerfe) == 1
    scores = json.loads(entwuerfe[0]["scores"])
    assert {s["pruefer"]: s["score"] for s in scores} == {"ronny": 9, "markus": 5}
