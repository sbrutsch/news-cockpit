# News-Cockpit

## Projektbeschreibung

Pilot-App der Web-App-Plattform: IT-Nachrichten werden per token-gesicherter
Ingest-API angeliefert (n8n-Workflow, optional claude.ai-Routine) und in einer
Pressespiegel-UI gesichtet: wichtig markieren, archivieren, löschen, suchen.

**Eigentümer:** Stefan Brutscher
**Produktion:** Coolify auf Hostinger-VPS `srv1143188.hstgr.cloud` (Frankfurt),
Domain `news.itcoach.cloud` (Domain liegt ebenfalls bei Hostinger)

## Architektur

```
├── app/
│   ├── main.py     # FastAPI: Routen, Auth-Dependencies, Security-Header, .env-Loader
│   ├── db.py       # Speicherschicht: Postgres (psycopg) ODER SQLite über DATABASE_URL
│   └── auth.py     # PBKDF2-Hash, signierte Session-Cookies, Login-Drossel (stdlib)
├── public/
│   └── index.html  # Komplette UI: Vanilla HTML/CSS/JS, kein Build-Step, keine CDN-Abhängigkeit
├── scripts/make_password_hash.py
├── Dockerfile      # python:3.12-slim, non-root, CMD python -m app.main
└── requirements.txt  # fastapi, uvicorn, psycopg[binary]
```

### Bewusste Entscheidungen
- **Zeitstempel als UTC-ISO-Strings** in beiden DB-Backends — identische Sortierung,
  keine Datums-Dialekte in der SQL-Schicht (`db.normalize_ts`).
- **Dedupe über `UNIQUE(url)`** + `ON CONFLICT DO NOTHING` — der Sammler darf
  beliebig oft dasselbe liefern.
- **Soft-Delete** (`status='deleted'`), kein hartes Löschen im MVP.
- **Frontend rendert ausschließlich über `textContent`/DOM-APIs** — kein
  `innerHTML` mit Fremddaten (XSS-Schutz gegen bösartige Feed-Titel).
  `innerHTML` nur für die statischen SVG-Icon-Strings.
- **CI:** Farben `#1F2A37`/`#6B7280`/`#C53030` (Rot NUR für Wichtig-Markierung),
  Source Sans 3 mit Arial-Fallback, kein ALL-CAPS, Hierarchie über Größe/Gewicht.

## Secrets (Governance-Regel 3)

`APP_PASSWORD_HASH`, `INGEST_TOKEN`, `SECRET_KEY`, `DATABASE_URL` **nur** als
Umgebungsvariablen (lokal `.env` — ist in `.gitignore`; Produktion: Coolify-UI).
Nie in Code, Doku oder Chat-Ausgaben. Ein Token, das je in OneDrive/Git lag,
gilt als kompromittiert und wird rotiert.

## Lokale Entwicklung

- venv liegt AUSSERHALB von OneDrive: `%LOCALAPPDATA%\venvs\news-cockpit`
  (windows-safe-editing Regel 7)
- Start: `& "$env:LOCALAPPDATA\venvs\news-cockpit\Scripts\python" -m app.main`
  aus dem Projektordner (liest `.env`, SQLite unter `data/`)
- Nach jeder Python-Änderung: `python -m py_compile app/main.py app/db.py app/auth.py`

## Deployment-Weg

GitHub-Repo (privat) → Coolify (Dockerfile-Build) → `news.sternenozean.de`.
Healthcheck: `GET /healthz`. Env-Vars in Coolify pflegen. Auto-Deploy bei Push.

## Änderungsprotokoll

- **2026-07-15:** Projekt angelegt (MVP: Ingest-API, Items-API, Login,
  Pressespiegel-UI, Dockerfile). Plattform-Entscheidung: Coolify auf
  Hostinger-VPS, Beschluss siehe Plan `zippy-snacking-jellyfish`.
- **2026-07-15 (2):** Themenscout-Felder `kind` (news|idee|zitat) und `pillar`
  ergänzt (Schema + Nachrüst-Migration in `db.init`, Ingest-API, UI-Chips).
  Domain-Entscheidung: `news.itcoach.cloud` statt sternenozean.de (Domain und
  VPS im selben Hostinger-Konto, all-inkl/WordPress bleibt unberührt).
- **2026-07-15 (3):** Dunkles UI-Redesign; Titel-Links nur noch bei externen
  Quellen. **Verwerten-Knopf**: `POST /api/items/{id}/verwerten` erzeugt via
  `app/transform.py` (Anthropic-SDK, `TRANSFORM_MODEL`, Standard
  claude-sonnet-5 — Stefans Content-Standardmodell) einen LinkedIn-Entwurf aus
  Positionierungs-Prompt + Eintrag; Modal-UI mit Kopieren/Neu generieren.
  Neuer Secret-Bedarf: `ANTHROPIC_API_KEY` als Coolify-Env (serverseitig,
  nie im Browser).
- **2026-07-15 (4):** Tagesbriefing-Karte (Neu-Tab: heutige Funde nach Art und
  Säulen zusammengefasst) + Datums-Trenner in der Liste (Heute/Gestern/Datum).
  Notizfeld pro Eintrag (`note`-Spalte + Migration, PATCH-API, Amber-Block in
  der UI); Notiz wird beim Verwerten als verbindlicher Winkel in den Prompt
  eingebaut.
- **2026-07-15 (5):** Wochen-Export (`GET /api/export?days=7`, Markdown-Download
  nach Säulen gruppiert inkl. Notizen; Download-Knopf in der Toolbar) und PWA
  (manifest.webmanifest, sw.js netz-zuerst ohne API-Caching, Icons via Pillow
  generiert). Auto-Deploy per GitHub-Webhook aktiv seit d48cfac.
