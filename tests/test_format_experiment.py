"""Format-Experiment: zwei Erzeugungs-Formate, Etikett am Entwurf, Auswertung je Arm.

Der Testarm "erzaehlung" muss sich vom Lehrstueck unterscheiden, das Etikett muss
den Weg in die Bibliothek finden, und die Auswertung muss die Arme sauber trennen.
Kein Modellaufruf: die Erzeugung wird gestubbt.
"""

import json

import pytest

from app import db, main, transform


def test_formate_haben_eigene_prompts():
    lehr = transform.system_fuer("lehrstueck")
    erz = transform.system_fuer("erzaehlung")
    assert lehr is transform.SYSTEM, "die Kontrolle ist wörtlich das bisherige Format"
    assert "Prüfraster" in lehr and "Erzählung" in erz
    assert "Keine Aufzählungen, kein Prüfraster" in erz
    assert "Alle schauen auf dich." in erz, "Stefans eigene Anfänge sind der Maßstab"
    with pytest.raises(transform.TransformError) as e:
        transform.system_fuer("gedicht")
    assert e.value.status == 400


def test_ueberarbeiten_haelt_das_format(monkeypatch):
    gesehen = {}

    def fake(system, user, max_tokens):
        gesehen["system"] = system
        return "neu"

    monkeypatch.setattr(transform, "_claude_text", fake)
    transform.ueberarbeiten("Ein Entwurf.", [{"name": "Ronny", "score": 5, "feedback": "Raster!"}],
                            format="erzaehlung")
    assert "Das Format bleibt „Erzählung\"" in gesehen["system"]
    assert gesehen["system"].startswith(transform.SYSTEM_ERZAEHLUNG)


def test_verwerten_nimmt_format_entgegen(sitzung, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(main.transform, "linkedin_entwurf",
                        lambda item, format="lehrstueck": aufrufe.append(format) or "Entwurf")
    db.insert_item("Fund", "https://example.org/f", kind="idee")
    item = db.list_items(tab="new")[0]

    assert sitzung.post(f"/api/items/{item['id']}/verwerten").json()["format"] == "lehrstueck"
    assert sitzung.post(f"/api/items/{item['id']}/verwerten", json={"format": "erzaehlung"}).json()["format"] == "erzaehlung"
    assert sitzung.post(f"/api/items/{item['id']}/verwerten", json={"format": "gedicht"}).status_code == 400
    assert aufrufe == ["lehrstueck", "erzaehlung"]


def test_etikett_wird_gespeichert_und_ausgewertet(sitzung):
    assert sitzung.post("/api/drafts", json={"text": "A", "format": "gedicht"}).status_code == 400
    a = sitzung.post("/api/drafts", json={"text": "Erzählung eins", "format": "erzaehlung"}).json()
    b = sitzung.post("/api/drafts", json={"text": "Erzählung zwei", "format": "erzaehlung"}).json()
    sitzung.post("/api/drafts", json={"text": "Lehrstück eins", "format": "lehrstueck"})
    sitzung.post("/api/drafts", json={"text": "Ohne Etikett"})
    assert sitzung.get("/api/drafts").json()["items"][0]["format"] in ("erzaehlung", "lehrstueck", "")

    kennzahlen = lambda imp, likes, komm, eng: json.dumps(  # noqa: E731
        {"impressions": imp, "likes": likes, "comments": komm, "engagement": eng})
    db.draft_veroeffentlichung(a["id"], post_id=1, veroeffentlicht_am="2026-10-12T05:45:00",
                               kennzahlen=kennzahlen(300, 6, 2, 2.7))
    db.draft_veroeffentlichung(b["id"], post_id=2, veroeffentlicht_am="2026-10-14T05:45:00",
                               kennzahlen=kennzahlen(100, 2, 0, 2.0))

    arme = sitzung.get("/api/experiment").json()["arme"]
    erz, lehr = arme["erzaehlung"], arme["lehrstueck"]
    assert (erz["entwuerfe"], erz["gepostet"], erz["gemessen"]) == (2, 2, 2)
    assert (erz["impressionen_median"], erz["likes_median"], erz["kommentare_je_post"], erz["mit_kommentar"]) == (200, 4, 1.0, 1)
    assert (lehr["entwuerfe"], lehr["gemessen"], lehr["impressionen_median"]) == (1, 0, None)
    assert "Ohne Etikett" not in json.dumps(arme), "ohne Etikett zählt kein Entwurf zu einem Arm"
