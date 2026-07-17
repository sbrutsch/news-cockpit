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
- **2026-07-17 (3):** **Prüfschleife (Auto-Modus).** Neuer Knopf im
  Verwerten-Dialog automatisiert Stefans manuellen Ablauf: beide Prüfer
  parallel → bestes Urteil < 8 → Überarbeitung mit gesammeltem Feedback →
  erneut prüfen; Stopp bei Urteil ≥ 8 (BESTANDEN_AB) oder nach 2
  Überarbeitungen (MAX_UEBERARBEITUNGEN). Rein clientseitig auf bestehenden
  Endpunkten; Regie-Anweisung bleibt über Runden erhalten (vw.anweisung);
  Knöpfe während des Laufs gesperrt; Abbruch-sicher bei Modal-Schließen.
- **2026-07-17 (2):** **KI-Themen freigeschaltet + Qualitätslatte im Erstentwurf.**
  Stefans Befund 1: Scout mied KI-Themen — Ursache: Scout-Prompt nannte
  „KI-Einführung" als erstes Negativ-Beispiel und hatte kein KI-Suchfeld.
  Fix in n8n-Workflow (1cBLyj7iC9dYW4gT, per API, bleibt aktiv) UND Quelle
  KI/KI-Agenten/news-routine.md: Ausschluss nur noch „Tech als Selbstzweck",
  KI ausdrücklich Kernmaterial bei Führungs-/Entscheidungswinkel; neues
  Suchfeld „KI und Führung". EINORDNUNG_SYSTEM: Technologie-Label entscheidet
  nicht. Befund 2: Erstentwürfe fielen bei den Prüfern mehrfach durch —
  SYSTEM in transform.py um „Qualitätslatte" erweitert (destilliert aus den
  wiederkehrenden Ronny/Claudia-Kritiken): Diagnose nie ohne anwendbares
  Element, Behauptung/Beleg trennen, keine Ferndiagnosen über reale Personen,
  Konzern→Mittelstand übersetzen, beantwortbare Schlussfrage; 120–250 Wörter.
- **2026-07-17:** **Posteingangs-Sortierung.** Stefans Fund: Briefing meldete
  „heute 4 Fundstücke", Liste zeigte sie unter alten Datums-Trennern — Briefing
  zählte nach `ingested_at`, Liste sortierte/gruppierte nach
  `COALESCE(published_at, …)`. Fix: Liste + Tagestrenner + relTime konsequent
  nach Eingang (`ingested_at`); Erscheinungsdatum bleibt als Zusatz sichtbar
  („erschienen 14. Juli", nur bei Abweichung vom Eingangstag). Wochen-Export
  bewusst unverändert (gruppiert nach Säule).
- **2026-07-16 (2):** Prüfstand-Ausbau nach Stefans erstem Praxistest
  (Mercedes-Fall: Ronny 4, Claudia 7 → verschiedene Beiträge je Zielgruppe).
  **Breites Modal:** ab 1000px zweispaltig (Entwurf links, Prüfstand rechts,
  `:has(.two-col)`), mobil unverändert einspaltig. **Entwurf direkt editierbar**
  (Textarea, `field-sizing: content` mit JS-Fallback). **Wählbares Feedback:**
  „einbeziehen"-Checkbox pro Prüfer-Urteil + optionale Regie-Anweisung
  (`anweisung` an /api/ueberarbeiten, hat Vorrang; bewusst statt fragiler
  Einzelvorschlag-Checkboxen). **Entwurfs-Bibliothek:** Tabelle `drafts`
  (Score-Schnappschuss als JSON, Status entwurf/gepostet, hartes Löschen ok),
  CRUD unter /api/drafts, vierter Tab „Entwürfe" (Suche client-seitig,
  Karten mit Score-Badges, Öffnen/Kopieren/Gepostet/Löschen; Öffnen führt
  zurück in den Prüfkreislauf). „Neu generieren" löst die Speicher-Verknüpfung
  (kein Überschreiben gespeicherter Entwürfe); Status-Toggle ändert
  updated_at nicht (Liste bleibt stabil sortiert).
- **2026-07-16:** **IT-Leiter-Prüfstand** im Verwerten-Dialog. `app/pruefer.py`
  mit zwei Ziel-Personas (Ronny Berger aus skills-bibliothek/marktfilter-ronny,
  Claudia Brenner aus KI-Agenten/Tagesworkshop/simulator-claudia-prompt.md);
  einheitliche erste Zeile `SCORE: n` → Ampel in der UI. `POST /api/pruefen`
  (eine Persona bewertet) + `POST /api/ueberarbeiten` (transform.ueberarbeiten
  schreibt Entwurf anhand des Prüfer-Feedbacks neu, ohne Positionslogik zu
  verwässern). Prüfer-Karten mit Score/Feedback im Modal, „Mit Feedback
  überarbeiten"-Knopf. transform.py um `_claude_text`-Helfer zentralisiert.
  Bewusst KEINE eigene App — gehört in die bestehende Verwerten-Kette.
- **2026-07-15 (6):** Layout verbreitert (960px, Summary 80ch). **Resümee**:
  `POST /api/items/{id}/einordnen` bewertet via Claude (strenges JSON:
  relevanz hoch/mittel/gering + resumee) den Nutzen für Stefans Geschäft und
  die IT-Leiter-Zielgruppe; Spalten `assessment`/`relevance` + Migration,
  Ampel-Block in der UI (grün/amber/grau), Zeile im Wochen-Export, Kontext im
  Verwerten-Prompt. Ziel-Icon in den Aktionen (erneuter Klick = neu bewerten).
