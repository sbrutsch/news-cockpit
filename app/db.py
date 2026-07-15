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
        "published_at", "ingested_at", "status", "important")
SELECT_COLS = ", ".join(COLS)

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
  important    INTEGER NOT NULL DEFAULT 0
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
  important    BOOLEAN NOT NULL DEFAULT FALSE
)"""

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)",
    "CREATE INDEX IF NOT EXISTS idx_items_ingested ON items(ingested_at)",
)


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


def init():
    with cursor() as cur:
        cur.execute(_SCHEMA_PG if IS_POSTGRES else _SCHEMA_SQLITE)
        for stmt in _INDEXES:
            cur.execute(stmt)


def ping():
    with cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    return True


def insert_item(title, url, source="", summary="", published_at=None):
    """Legt ein Item an. True = neu angelegt, False = URL existierte schon."""
    with cursor() as cur:
        cur.execute(
            _q("INSERT INTO items (title, url, source, summary, published_at, ingested_at) "
               "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (url) DO NOTHING"),
            (title.strip(), url.strip(), (source or "").strip(),
             (summary or "").strip(), normalize_ts(published_at), utcnow_iso()),
        )
        return cur.rowcount == 1


def list_items(tab="new", q="", limit=50, offset=0):
    if tab == "important":
        where, params = ["status != ?", "important = ?"], ["deleted", True]
    elif tab == "archived":
        where, params = ["status = ?"], ["archived"]
    else:
        where, params = ["status = ?"], ["new"]
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
    return {"new": new_c, "important": imp_c, "archived": arch_c}


def get_item(item_id):
    with cursor() as cur:
        cur.execute(_q(f"SELECT {SELECT_COLS} FROM items WHERE id = ?"), (item_id,))
        r = cur.fetchone()
    return _row(r) if r else None


def update_item(item_id, important=None, status=None):
    sets, params = [], []
    if important is not None:
        sets.append("important = ?")
        params.append(bool(important))
    if status is not None:
        if status not in ("new", "archived", "deleted"):
            raise ValueError("Ungültiger Status")
        sets.append("status = ?")
        params.append(status)
    if sets:
        params.append(item_id)
        with cursor() as cur:
            cur.execute(_q(f"UPDATE items SET {', '.join(sets)} WHERE id = ?"), params)
    return get_item(item_id)
