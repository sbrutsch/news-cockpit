"""Rückkanal von ContentIn: was wurde veröffentlicht, und wie kam es an.

ContentIn hat keine REST-API. Sein MCP-Server (Streamable HTTP) ist die einzige
Maschinenschnittstelle, und JSON-RPC über HTTPS-POST reicht dafür völlig:

    POST https://mcp.contentin.io/mcp-server
    X-MCP-Key: cimcp_…          (Key pro Profil, Settings → „Connect AI clients")
    Accept: application/json, text/event-stream

Ablauf je Verbindung: `initialize` → `notifications/initialized` → `tools/call`.
Antworten kommen als JSON-Body oder als SSE-Strom (`data:`-Zeilen); beides wird
hier gelesen. Eine `Mcp-Session-Id` aus der ersten Antwort wird mitgeführt.

Der Abgleich (`abgleich`) holt die veröffentlichten Beiträge, ordnet sie über
den normierten Textanfang den Entwürfen der Bibliothek zu, setzt „gepostet",
legt die LinkedIn-Kennzahlen am Entwurf ab und nimmt den Quell-Fund aus dem
Posteingang. Gerufen werden nur `list_posts` und `get_post_analytics`, nichts,
was veröffentlicht. Kennzahlen von Beiträgen der letzten 30 Tage werden bei
jedem Lauf erneuert (die Zahlen bewegen sich noch), ältere nur einmal.

Die Tests sprechen kein Netz: `_transport` ist die einzige Stelle, die es tut.
"""

import html
import json
import logging
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from app import db

log = logging.getLogger("news-cockpit.contentin")

MCP_URL = os.environ.get("CONTENTIN_MCP_URL", "https://mcp.contentin.io/mcp-server")
PROTOKOLL = "2025-03-26"
KENNZAHLEN_FRISCH_TAGE = 30
VERGLEICH_ZEICHEN = 60      # so viele normierte Zeichen vom Anfang werden verglichen
VERGLEICH_MINDESTENS = 40   # kürzer ist kein belastbarer Vergleich


class ContentInError(Exception):
    pass


def mcp_key():
    return os.environ.get("CONTENTIN_MCP_KEY", "").strip()


# ---------------------------------------------------------------- Transport

def _transport(url, headers, body, timeout):
    """Ein HTTP-POST; liefert (Antwort-Header, Text). Einzige Stelle mit Netz."""
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return dict(resp.headers.items()), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        hinweis = " — Key abgelehnt oder Plan ohne MCP-Zugang?" if e.code in (401, 403) else ""
        raise ContentInError(f"ContentIn antwortet HTTP {e.code}{hinweis}")
    except urllib.error.URLError as e:
        raise ContentInError(f"ContentIn nicht erreichbar: {e.reason}")
    except TimeoutError:
        raise ContentInError("ContentIn antwortet nicht (Zeitüberschreitung)")


def _nachrichten(content_type, text):
    """JSON-RPC-Nachrichten aus einer Antwort: JSON-Body oder SSE-Strom."""
    if not text.strip():
        return []
    if "text/event-stream" in (content_type or ""):
        nachrichten, daten = [], []
        for zeile in text.splitlines() + [""]:
            if zeile.startswith("data:"):
                daten.append(zeile[5:].strip())
            elif zeile == "" and daten:
                try:
                    nachrichten.append(json.loads("\n".join(daten)))
                except ValueError:
                    pass
                daten = []
        return nachrichten
    try:
        geladen = json.loads(text)
    except ValueError:
        raise ContentInError("ContentIn-Antwort ist weder JSON noch SSE")
    return geladen if isinstance(geladen, list) else [geladen]


class Client:
    def __init__(self, key, url=None, timeout=30):
        self.key = key
        self.url = url or MCP_URL
        self.timeout = timeout
        self.session_id = None
        self._zaehler = 0
        self._verbunden = False

    def _headers(self):
        h = {"Content-Type": "application/json",
             "Accept": "application/json, text/event-stream",
             "X-MCP-Key": self.key,
             "MCP-Protocol-Version": PROTOKOLL}
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    def _senden(self, body):
        kopf, text = _transport(self.url, self._headers(), body, self.timeout)
        kopf = {k.lower(): v for k, v in kopf.items()}
        if kopf.get("mcp-session-id"):
            self.session_id = kopf["mcp-session-id"]
        return _nachrichten(kopf.get("content-type", ""), text)

    def _rpc(self, methode, params):
        self._zaehler += 1
        rid = self._zaehler
        for msg in self._senden({"jsonrpc": "2.0", "id": rid, "method": methode, "params": params}):
            if isinstance(msg, dict) and msg.get("id") == rid:
                if "error" in msg:
                    fehler = msg.get("error") or {}
                    raise ContentInError(
                        f"{methode}: {fehler.get('message', 'Fehler')} ({fehler.get('code', '?')})")
                return msg.get("result") or {}
        raise ContentInError(f"{methode}: keine Antwort von ContentIn")

    def verbinden(self):
        self._rpc("initialize", {"protocolVersion": PROTOKOLL, "capabilities": {},
                                 "clientInfo": {"name": "news-cockpit", "version": "1"}})
        self._senden({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._verbunden = True

    def werkzeug(self, name, argumente):
        """Ein MCP-Werkzeug rufen; liefert dessen JSON-Ergebnis als dict."""
        if not self._verbunden:
            self.verbinden()
        res = self._rpc("tools/call", {"name": name, "arguments": argumente})
        text = "".join(b.get("text", "") for b in res.get("content", [])
                       if isinstance(b, dict) and b.get("type") == "text")
        if res.get("isError"):
            raise ContentInError(f"{name}: {text[:200] or 'Werkzeug meldet Fehler'}")
        if isinstance(res.get("structuredContent"), dict):
            return res["structuredContent"]
        try:
            return json.loads(text)
        except ValueError:
            raise ContentInError(f"{name}: Antwort ist kein JSON")


# ---------------------------------------------------------------- Zuordnung

_TAGS = re.compile(r"<[^>]+>")
_ZEICHEN = re.compile("[„“”\"»«‚‘’'­]")   # Anführungszeichen, weiche Trennstriche
_STRICHE = re.compile("[–—-]+")
_LEER = re.compile(r"\s+")


def normieren(text):
    """Textanfang vergleichbar machen: ohne HTML, Entities, Typografie, Groß/Klein."""
    t = html.unescape(_TAGS.sub(" ", text or ""))
    t = _ZEICHEN.sub("", t)
    t = _STRICHE.sub("-", t)
    return _LEER.sub(" ", t).strip().casefold()[:VERGLEICH_ZEICHEN]


def passt(auszug, entwurf_text):
    """Beginnt der Entwurf mit demselben Text wie der ContentIn-Auszug?"""
    a, b = normieren(auszug), normieren(entwurf_text)
    n = min(len(a), len(b))
    return n >= VERGLEICH_MINDESTENS and a[:n] == b[:n]


def _finde(entwuerfe, post):
    pid = post.get("post_id")
    for d in entwuerfe:
        if pid is not None and d.get("contentin_post_id") == pid:
            return d
    for d in entwuerfe:
        if passt(post.get("excerpt", ""), d["text"]):
            return d
    return None


def _juenger_als(zeitstempel, tage):
    if not zeitstempel:
        return True
    try:
        t = datetime.fromisoformat(str(zeitstempel).replace("Z", "+00:00"))
    except ValueError:
        return True
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - t < timedelta(days=tage)


def _kennzahlen_holen(client, post_id):
    if post_id is None:
        return None
    res = client.werkzeug("get_post_analytics", {"post_id": int(post_id)})
    if not res.get("measured"):
        return None
    m = res.get("metrics") or {}
    return {"impressions": m.get("impressions"), "members_reached": m.get("members_reached"),
            "likes": m.get("likes"), "comments": m.get("comments"), "shares": m.get("shares"),
            "engagement": m.get("engagement"), "gemessen_am": db.utcnow_iso()}


# ---------------------------------------------------------------- Abgleich

def abgleich(client):
    """Veröffentlichte Beiträge holen, Entwürfen zuordnen, Kennzahlen ablegen.

    Liefert eine Zusammenfassung für Log, Antwort und Oberfläche.
    """
    posts = client.werkzeug("list_posts", {"status": ["posted"], "limit": 50}).get("posts") or []
    entwuerfe = db.list_drafts(limit=500)
    ergebnis = {"beitraege": len(posts), "zugeordnet": 0, "neu_gepostet": 0,
                "kennzahlen_aktualisiert": 0, "archiviert": 0,
                "ohne_entwurf": 0, "ohne_entwurf_beispiele": []}
    for post in posts:
        d = _finde(entwuerfe, post)
        if d is None:
            ergebnis["ohne_entwurf"] += 1
            if len(ergebnis["ohne_entwurf_beispiele"]) < 3:
                ergebnis["ohne_entwurf_beispiele"].append(normieren(post.get("excerpt", "")))
            continue
        ergebnis["zugeordnet"] += 1
        zahlen = None
        if not d.get("kennzahlen") or _juenger_als(post.get("posted_at"), KENNZAHLEN_FRISCH_TAGE):
            zahlen = _kennzahlen_holen(client, post.get("post_id"))
        war_gepostet = d["status"] == "gepostet"
        db.draft_veroeffentlichung(d["id"], post_id=post.get("post_id"),
                                   veroeffentlicht_am=post.get("posted_at"),
                                   kennzahlen=json.dumps(zahlen) if zahlen else None)
        if zahlen:
            ergebnis["kennzahlen_aktualisiert"] += 1
        if not war_gepostet:
            ergebnis["neu_gepostet"] += 1
            if d.get("item_id") and db.archiviere_fund(d["item_id"]):
                ergebnis["archiviert"] += 1
        # Jeder Entwurf gehört zu höchstens einem Beitrag
        entwuerfe = [e for e in entwuerfe if e["id"] != d["id"]]
    return ergebnis
