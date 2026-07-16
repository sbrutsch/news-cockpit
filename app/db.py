"""Speicherschicht des News-Cockpits.

Zwei Backends, gesteuert über DATABASE_URL:
  - postgresql://...  -> psycopg (Produktion, Coolify-Postgres)
  - sqlite:///pfad    -> sqlite3 (lokale Entwicklung; Standard: data/news.db)

Alle Zeitstempel werden als UTC-ISO-Strings gespeichert ("2026-07-15T08:30:00Z"),
damit beide Backends identisch sortieren und die SQL-Schicht frei von
Datums-Dialekten bleibt.
"""

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/news.db")
IS_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

_lock = threading.Lock()
_conn = None

COLS = ("id", "title", "url", "source", "summary",
        "published_at", "ingested_at", "status", "important", "kind", "pillar", "note",
        "assessment", "relevance")
SELECT_COLS = ", ".join(COLS)

# Art des Eintrags: klassische Meldung, Content-Idee oder Zitat/Pain-Point
KINDS = ("news", "idee", "zitat")

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS items (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  title        TEXT NOT NULL,
  url          TEXT NOT NULL UNIQUE,
  source       TEXT NOT NULL DEFAULT '',
  summary      TEXT NOT NULL DEFAULT '',
  published_at TEXT,
  ingested_at  TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'new',
  important    INTEGER NOT NULL DEFAULT 0,
  kind         TEXT NOT NULL DEFAULT 'news',
  pillar       TEXT NOT NULL DEFAULT '',
  note         TEXT NOT NULL DEFAULT '',
  assessment   TEXT NOT NULL DEFAULT '',
  relevance    TEXT NOT NULL DEFAULT ''
)"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS items (
  id           BIGSERIAL PRIMARY KEY,
  title        TEXT NOT NULL,
  url          TEXT NOT NULL UNIQUE,
  source       TEXT NOT NULL DEFAULT '',
  summary      TEXT NOT NULL DEFAULT '',
  published_at TEXT,
  ingested_at  TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'new',
  important    BOOLEAN NOT NULL DEFAULT FALSE,
  kind         TEXT NOT NULL DEFAULT 'news',
  pillar       TEXT NOT NULL DEFAULT '',
  note         TEXT NOT NULL DEFAULT '',
  assessment   TEXT NOT NULL DEFAULT '',
  relevance    TEXT NOT NULL DEFAULT ''
)"""

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)",
    "CREATE INDEX IF NOT EXISTS idx_items_ingested ON items(ingested_at)",
)

# Gespeicherte LinkedIn-Entwürfe (aus dem Verwerten-Dialog).
# scores = JSON-Schnappschuss der Prüfer-Urteile zum Speicherzeitpunkt.
DRAFT_COLS = ("id", "item_id", "item_title", "text", "scores", "status",
              "created_at", "updated_at")
DRAFT_SELECT = ", ".join(DRAFT_COLS)
DRAFT_STATUS = ("entwurf", "gepostet")

_SCHEMA_DRAFTS_SQLITE = """
CREATE TABLE IF NOT EXISTS drafts (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id     INTEGER,
  item_title  TEXT NOT NULL DEFAULT '',
  text        TEXT NOT NULL,
  scores      TEXT NOT NULL DEFAULT '[]',
  status      TEXT NOT NULL DEFAULT 'entwurf',
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)"""

_SCHEMA_DRAFTS_PG = """
CREATE TABLE IF NOT EXISTS drafts (
  id          BIGSERIAL PRIMARY KEY,
  item_id     BIGINT,
  item_title  TEXT NOT NULL DEFAULT '',
  text        TEXT NOT NULL,
  scores      TEXT NOT NULL DEFAULT '[]',
  status      TEXT NOT NULL DEFAULT 'entwurf',
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)"""


def utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_ts(value):
    """Beliebige ISO-8601-Eingabe (oder Unix-Sekunden) -> UTC-ISO-String, sonst None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(value).strip()
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect():
    if IS_POSTGRES:
        import psycopg
        return psycopg.connect(DATABASE_URL, autocommit=True)
    path = DATABASE_URL.removeprefix("sqlite:///")
    if path != ":memory:":
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _drop_conn():
    global _conn
    try:
        if _conn is not None:
            _conn.close()
    except Exception:
        pass
    _conn = None


@contextmanager
def cursor():
    """Serialisierter Cursor; verbindet bei toter Verbindung einmal neu."""
    global _conn
    with _lock:
        cur = None
        for attempt in (1, 2):
            try:
                if _conn is None:
                    _conn = _connect()
                cur = _conn.cursor()
                break
            except Exception:
                _drop_conn()
                if attempt == 2:
                    raise
        try:
            yield cur
            if not IS_POSTGRES:
                _conn.commit()
        except Exception:
            if IS_POSTGRES:
                broken = getattr(_conn, "closed", False) or getattr(_conn, "broken", False)
                if broken:
                    _drop_conn()
            else:
                try:
                    _conn.rollback()
                except Exception:
                    _drop_conn()
            raise
        finally:
            try:
                cur.close()
            except Exception:
                pass


def _q(sql):
    """Platzhalter-Übersetzung: '?' (sqlite) -> '%s' (psycopg)."""
    return sql.replace("?", "%s") if IS_POSTGRES else sql


def _row(r):
    d = dict(zip(COLS, r))
    d["important"] = bool(d["important"])
    return d


def _column_names(cur):
    if IS_POSTGRES:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'items'")
        return {r[0] for r in cur.fetchall()}
    cur.execute("PRAGMA table_info(items)")
    return {r[1] for r in cur.fetchall()}


def init():
    with cursor() as cur:
        cur.execute(_SCHEMA_PG if IS_POSTGRES else _SCHEMA_SQLITE)
        cur.execute(_SCHEMA_DRAFTS_PG if IS_POSTGRES else _SCHEMA_DRAFTS_SQLITE)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_drafts_updated ON drafts(updated_at)")
        for stmt in _INDEXES:
            cur.execute(stmt)
        # Nachrüst-Migration für Bestände, die vor kind/pillar angelegt wurden
        have = _column_names(cur)
        if "kind" not in have:
            cur.execute("ALTER TABLE items ADD COLUMN kind TEXT NOT NULL DEFAULT 'news'")
        if "pillar" not in have:
            cur.execute("ALTER TABLE items ADD COLUMN pillar TEXT NOT NULL DEFAULT ''")
        if "note" not in have:
            cur.execute("ALTER TABLE items ADD COLUMN note TEXT NOT NULL DEFAULT ''")
        if "assessment" not in have:
            cur.execute("ALTER TABLE items ADD COLUMN assessment TEXT NOT NULL DEFAULT ''")
        if "relevance" not in have:
            cur.execute("ALTER TABLE items ADD COLUMN relevance TEXT NOT NULL DEFAULT ''")


def ping():
    with cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    return True


def insert_item(title, url, source="", summary="", published_at=None, kind="news", pillar=""):
    """Legt ein Item an. True = neu angelegt, False = URL existierte schon."""
    if kind not in KINDS:
        kind = "news"
    with cursor() as cur:
        cur.execute(
            _q("INSERT INTO items (title, url, source, summary, published_at, ingested_at, kind, pillar) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (url) DO NOTHING"),
            (title.strip(), url.strip(), (source or "").strip(),
             (summary or "").strip(), normalize_ts(published_at), utcnow_iso(),
             kind, (pillar or "").strip()[:80]),
        )
        return cur.rowcount == 1


def list_items(tab="new", q="", limit=50, offset=0, kind=""):
    if tab == "important":
        where, params = ["status != ?", "important = ?"], ["deleted", True]
    elif tab == "archived":
        where, params = ["status = ?"], ["archived"]
    else:
        where, params = ["status = ?"], ["new"]
    if kind in KINDS:
        where.append("kind = ?")
        params.append(kind)
    if q:
        like = f"%{q.lower()}%"
        where.append("(lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(source) LIKE ?)")
        params += [like, like, like]
    sql = (f"SELECT {SELECT_COLS} FROM items WHERE {' AND '.join(where)} "
           "ORDER BY COALESCE(published_at, ingested_at) DESC, id DESC "
           "LIMIT ? OFFSET ?")
    params += [max(1, min(int(limit), 200)), max(0, int(offset))]
    with cursor() as cur:
        cur.execute(_q(sql), params)
        return [_row(r) for r in cur.fetchall()]


def counts():
    sql = ("SELECT "
           "COUNT(*) FILTER (WHERE status = 'new'), "
           "COUNT(*) FILTER (WHERE important AND status != 'deleted'), "
           "COUNT(*) FILTER (WHERE status = 'archived') "
           "FROM items")
    with cursor() as cur:
        cur.execute(sql)
        new_c, imp_c, arch_c = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM drafts")
        drafts_c = cur.fetchone()[0]
    return {"new": new_c, "important": imp_c, "archived": arch_c, "drafts": drafts_c}


def export_items(since_iso):
    """Wichtige, nicht gelöschte Einträge seit since_iso — für den Wochen-Export."""
    sql = (f"SELECT {SELECT_COLS} FROM items "
           "WHERE important = ? AND status != ? AND ingested_at >= ? "
           "ORDER BY pillar, COALESCE(published_at, ingested_at) DESC")
    with cursor() as cur:
        cur.execute(_q(sql), (True, "deleted", since_iso))
        return [_row(r) for r in cur.fetchall()]


def get_item(item_id):
    with cursor() as cur:
        cur.execute(_q(f"SELECT {SELECT_COLS} FROM items WHERE id = ?"), (item_id,))
        r = cur.fetchone()
    return _row(r) if r else None


def update_item(item_id, important=None, status=None, note=None, assessment=None, relevance=None):
    sets, params = [], []
    if important is not None:
        sets.append("important = ?")
        params.append(bool(important))
    if status is not None:
        if status not in ("new", "archived", "deleted"):
            raise ValueError("Ungültiger Status")
        sets.append("status = ?")
        params.append(status)
    if note is not None:
        sets.append("note = ?")
        params.append(note)
    if assessment is not None:
        sets.append("assessment = ?")
        params.append(assessment)
    if relevance is not None:
        if relevance not in ("", "hoch", "mittel", "gering"):
            raise ValueError("Ungültige Relevanz")
        sets.append("relevance = ?")
        params.append(relevance)
    if sets:
        params.append(item_id)
        with cursor() as cur:
            cur.execute(_q(f"UPDATE items SET {', '.join(sets)} WHERE id = ?"), params)
    return get_item(item_id)


# ---------- Entwürfe ----------

def _draft_row(r):
    return dict(zip(DRAFT_COLS, r))


def insert_draft(text, item_id=None, item_title="", scores="[]"):
    now = utcnow_iso()
    params = (item_id, item_title, text, scores, now, now)
    with cursor() as cur:
        if IS_POSTGRES:
            cur.execute(_q("INSERT INTO drafts (item_id, item_title, text, scores, created_at, updated_at) "
                           "VALUES (?, ?, ?, ?, ?, ?) RETURNING id"), params)
            new_id = cur.fetchone()[0]
        else:
            cur.execute("INSERT INTO drafts (item_id, item_title, text, scores, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)", params)
            new_id = cur.lastrowid
    return get_draft(new_id)


def list_drafts(limit=200):
    sql = (f"SELECT {DRAFT_SELECT} FROM drafts "
           "ORDER BY updated_at DESC, id DESC LIMIT ?")
    with cursor() as cur:
        cur.execute(_q(sql), (max(1, min(int(limit), 500)),))
        return [_draft_row(r) for r in cur.fetchall()]


def get_draft(draft_id):
    with cursor() as cur:
        cur.execute(_q(f"SELECT {DRAFT_SELECT} FROM drafts WHERE id = ?"), (draft_id,))
        r = cur.fetchone()
    return _draft_row(r) if r else None


def update_draft(draft_id, text=None, scores=None, status=None):
    sets, params = [], []
    if text is not None:
        sets.append("text = ?")
        params.append(text)
    if scores is not None:
        sets.append("scores = ?")
        params.append(scores)
    if status is not None:
        if status not in DRAFT_STATUS:
            raise ValueError("Ungültiger Status")
        sets.append("status = ?")
        params.append(status)
    # Nur inhaltliche Änderungen heben den Entwurf in der Liste nach oben
    if text is not None or scores is not None:
        sets.append("updated_at = ?")
        params.append(utcnow_iso())
    if sets:
        params.append(draft_id)
        with cursor() as cur:
            cur.execute(_q(f"UPDATE drafts SET {', '.join(sets)} WHERE id = ?"), params)
    return get_draft(draft_id)


def delete_draft(draft_id):
    with cursor() as cur:
        cur.execute(_q("DELETE FROM drafts WHERE id = ?"), (draft_id,))
        return cur.rowcount == 1
