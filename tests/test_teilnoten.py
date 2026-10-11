"""Teilnoten je Persona werden mit dem Entwurf gespeichert, nicht nur die Gesamtnote.

Bis 2026-10-11 stand in `drafts.scores` je Persona nur `score`. Die vier Kriterien
wurden geparst, angezeigt und weggeworfen; eine Auswertung, welches Kriterium einen
Beitrag trägt oder reißt, war damit unmöglich.
"""

import json

from app import db, main

DIM = [{"name": "Positionierung im ersten Absatz", "score": 4},
       {"name": "Thesenschärfe", "score": 7}]


def test_speichern_aus_der_oberflaeche_behaelt_teilnoten(sitzung):
    antwort = sitzung.post("/api/drafts", json={"text": "Ein Entwurf.", "scores": [
        {"pruefer": "claudia", "name": "Claudia Brenner", "score": 6, "dimensionen": DIM}]})
    assert antwort.status_code == 201

    gespeichert = sitzung.get("/api/drafts").json()["items"][0]
    assert gespeichert["scores"][0]["dimensionen"] == DIM


def test_rueckfluss_behaelt_teilnoten_ohne_begruendung():
    ergebnis = {"pruefer": "claudia", "name": "Claudia Brenner", "score": 6,
                "dimensionen": [dict(d, begruendung="eine lange Begründung") for d in DIM]}
    main._rueckfluss_beitrag("Extern geprüfter Beitrag.", ergebnis)

    scores = json.loads(db.list_drafts()[0]["scores"])
    assert scores[0]["dimensionen"] == DIM, "Name und Note bleiben; die Begründung steht im Feedback"
