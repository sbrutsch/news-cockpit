"""Personas kommen aus Dateien (Kanon), nicht aus dem Code.

Sichert den Vertrag aus wissensbasis/personas/README.md ab: Frontmatter, Abschnitt
System-Prompt, Rahmen je Lesesituation, Kopfzeile des Generators. Und die Regel aus dem
Bauplan Schritt 7: art=audit wird geprueft, aber nie gespeichert.
"""

import re

import pytest

from app import db, main, pruefer

KOPFZEILE = re.compile(r"<!-- Generiert aus wissensbasis@\S+ am \S+\. Nicht hier editieren\.")


def test_alle_personas_aus_dateien_geladen():
    """Fuenf Personas, jede mit Name, Rolle und einem System-Prompt, der die SCORE-Zeile verlangt."""
    assert set(pruefer.PRUEFER) == {"ronny", "claudia", "markus", "cfo", "vorstand"}
    for key, p in pruefer.PRUEFER.items():
        assert p["name"] and p["rolle"], key
        assert "SCORE:" in p["system"], key
        assert p["datei"] == f"{key}.md"


def test_dateien_tragen_die_kopfzeile_des_generators():
    """Eine Persona ohne Kopfzeile wurde von Hand angelegt und driftet."""
    for pfad in pruefer.PERSONA_ORDNER.glob("*.md"):
        text = pfad.read_text(encoding="utf-8")
        assert KOPFZEILE.search(text), f"{pfad.name} ohne Generator-Kopfzeile"


def test_system_prompt_kommt_aus_der_datei():
    """Der Wortlaut der Datei ist der Wortlaut des Prompts, nicht eine Konstante im Code."""
    text = (pruefer.PERSONA_ORDNER / "ronny.md").read_text(encoding="utf-8")
    erster_satz = "Du bist Ronny Berger, erfahrener IT-Leiter Anfang 50"
    assert erster_satz in text
    assert pruefer.PRUEFER["ronny"]["system"].startswith(erster_satz)


def test_rahmen_je_lesesituation():
    """Beitrag immer; Seite nur, wo vorgesehen; Audit bei allen fuenf."""
    assert pruefer.arten_fuer("ronny") == ["beitrag", "seite", "audit"]
    assert pruefer.arten_fuer("cfo") == ["beitrag", "audit"]
    assert pruefer.arten_fuer("vorstand") == ["beitrag", "audit"]
    audit = pruefer.system_prompt("cfo", "audit")
    assert audit.startswith(pruefer.PRUEFER["cfo"]["system"])
    assert "EINWAND 1" in audit and "WAS ICH NICHT SAGE" in audit


def test_nicht_vorgesehene_lesesituation_bricht_vor_dem_modellaufruf_ab(monkeypatch):
    """CFO bewertet keine Landingpage: 400, und Claude wird gar nicht erst gerufen."""
    def nie(*args, **kwargs):
        raise AssertionError("Modellaufruf trotz ungueltiger Lesesituation")
    monkeypatch.setattr(pruefer, "_claude_text", nie)
    with pytest.raises(pruefer.TransformError) as e:
        pruefer.pruefen("Eine Seite.", "cfo", "seite")
    assert e.value.status == 400
    with pytest.raises(pruefer.TransformError):
        pruefer.pruefen("x", "ronny", "unsinn")


def test_api_kennt_arten_je_persona(sitzung):
    """GET /api/pruefer nennt je Persona die Lesesituationen, damit Aufrufer nichts raten."""
    daten = sitzung.get("/api/pruefer").json()["pruefer"]
    je_key = {p["schluessel"]: p for p in daten}
    assert je_key["cfo"]["arten"] == ["beitrag", "audit"]
    assert je_key["markus"]["arten"] == ["beitrag", "seite", "audit"]


def test_audit_wird_geprueft_aber_nie_gespeichert(client, dienst, pruefer_stub):
    """Bauplan Schritt 7: Audit-Vorlagen landen in keiner Bibliothek, auch mit Rueckfluss an."""
    assert main.DIENST_RUECKFLUSS is True
    vorlage = {"entwurf": "Anonymisierte Entscheidungsvorlage.", "pruefer": "vorstand", "art": "audit"}
    antwort = client.post("/api/pruefen", json=vorlage, headers=dienst)
    assert antwort.status_code == 200
    assert pruefer_stub[-1][2] == "audit"
    assert db.list_drafts() == []
    assert db.find_draft_by_text("Anonymisierte Entscheidungsvorlage.") is None


def test_art_kennt_genau_drei_werte(sitzung):
    assert sitzung.post("/api/pruefen", json={"entwurf": "x", "pruefer": "ronny", "art": "audit"},
                        headers={}).status_code != 400
    assert sitzung.post("/api/pruefen", json={"entwurf": "x", "pruefer": "ronny", "art": "gremium"}).status_code == 400
