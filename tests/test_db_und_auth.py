"""Speicherschicht und Anmeldung — die Zusagen, auf denen der Rest aufsetzt."""

import time

from app import auth, db


def test_ingest_dedupe_ueber_url():
    """Der Sammler darf beliebig oft dasselbe liefern (UNIQUE(url))."""
    assert db.insert_item("Erster Titel", "https://example.test/a") is True
    assert db.insert_item("Anderer Titel, gleiche URL", "https://example.test/a") is False

    treffer = db.list_items()
    assert len(treffer) == 1
    assert treffer[0]["title"] == "Erster Titel", "der Erstfund bleibt stehen"


def test_draft_flags_gepostet_gewinnt():
    """Ein Fund mit mehreren Entwürfen gilt als gepostet, sobald einer es ist."""
    db.insert_item("Ein Fund", "https://example.test/fund")
    item = db.list_items()[0]

    db.insert_draft("Entwurf A", item_id=item["id"])
    assert db.draft_flags([item["id"]]) == {item["id"]: "entwurf"}

    zweiter = db.insert_draft("Entwurf B", item_id=item["id"])
    db.update_draft(zweiter["id"], status="gepostet")
    assert db.draft_flags([item["id"]]) == {item["id"]: "gepostet"}

    # Ein Fund ohne Entwurf taucht gar nicht erst auf
    assert db.draft_flags([item["id"] + 999]) == {}


def test_session_cookie_signatur():
    """Nur selbst signierte, unverfallene Token gelten."""
    token = auth.create_session_token()
    assert auth.verify_session_token(token) is True

    kopf, _, sig = token.partition(".")
    assert auth.verify_session_token(f"{kopf}.{sig[:-3]}aaa") is False, "Signatur manipuliert"
    assert auth.verify_session_token(f"{kopf}.") is False
    assert auth.verify_session_token("") is False

    abgelaufen = auth.create_session_token(now=time.time() - auth.SESSION_TTL - 60)
    assert auth.verify_session_token(abgelaufen) is False
