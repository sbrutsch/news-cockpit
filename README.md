# News-Cockpit

IT-Nachrichten sammeln, sichten, verwerten: Meldungen kommen per API herein
(n8n oder claude.ai-Routine), werden in einer Pressespiegel-Oberfläche gelesen
und lassen sich als wichtig markieren, archivieren, löschen und durchsuchen.

**Eigentümer:** Stefan Brutscher · läuft auf eigenem Server (Coolify, Frankfurt)

## Lokal starten

```powershell
# Einmalig: virtuelles Environment AUSSERHALB von OneDrive anlegen
python -m venv "$env:LOCALAPPDATA\venvs\news-cockpit"
& "$env:LOCALAPPDATA\venvs\news-cockpit\Scripts\pip" install -r requirements.txt

# .env anlegen (Vorlage kopieren, Werte setzen)
Copy-Item .env.example .env

# Starten (nutzt lokal SQLite unter data/news.db)
& "$env:LOCALAPPDATA\venvs\news-cockpit\Scripts\python" -m app.main
# → http://127.0.0.1:8100
```

## Konfiguration (Umgebungsvariablen)

| Variable | Pflicht | Bedeutung |
|---|---|---|
| `DATABASE_URL` | nein | `postgresql://…` (Produktion) oder `sqlite:///data/news.db` (Standard) |
| `APP_PASSWORD_HASH` | ja¹ | Login-Passwort als PBKDF2-Hash — erzeugen mit `python scripts/make_password_hash.py` |
| `APP_PASSWORD` | ja¹ | Alternative: Klartext-Passwort (nur wenn kein Hash gesetzt ist) |
| `INGEST_TOKEN` | ja | Bearer-Token für `POST /api/ingest`; ohne Token ist Ingest deaktiviert |
| `SECRET_KEY` | empfohlen | Signiert Session-Cookies; ohne Angabe enden Sessions beim Neustart |
| `HOST` / `PORT` | nein | Standard `127.0.0.1` / `8080` (Docker setzt `HOST=0.0.0.0`) |

¹ Eines von beiden. Secrets niemals ins Repo — in Produktion in der Coolify-UI pflegen.

## Ingest-API (für n8n und claude.ai-Routine)

```
POST /api/ingest
Authorization: Bearer <INGEST_TOKEN>
Content-Type: application/json
```

Body: ein Objekt **oder** ein Array von Objekten (max. 500):

```json
{
  "title":        "VMware ändert Lizenzmodell erneut",     // Pflicht
  "url":          "https://www.heise.de/...",              // Pflicht, dient der Deduplizierung
  "source":       "heise online",                          // optional
  "summary":      "Kurzfassung in 2–3 Sätzen …",           // optional
  "published_at": "2026-07-15T06:30:00Z"                   // optional, ISO 8601 oder Unix-Sekunden
}
```

Antwort: `{"received": 10, "created": 7, "duplicates": 3, "rejected": 0}` —
Status 201, wenn mindestens ein Item neu angelegt wurde, sonst 200.
Bereits bekannte URLs werden still übersprungen (Dedupe), der Sammler muss
sich also nichts merken.

## Weitere Endpunkte

- `POST /api/login` · `POST /api/logout` · `GET /api/me` — Session (Cookie, HttpOnly)
- `GET /api/items?tab=new|important|archived&q=&limit=&offset=` — Liste + Zähler
- `PATCH /api/items/{id}` — `{"important": true}` und/oder `{"status": "archived"|"new"}`
- `DELETE /api/items/{id}` — Soft-Delete
- `GET /healthz` — für Coolify-Healthcheck

## Deployment

Coolify-App aus diesem Repo (Dockerfile-Build), Domain `news.sternenozean.de`,
Healthcheck-Pfad `/healthz`, Umgebungsvariablen siehe oben. Postgres läuft als
Coolify-Datenbank im internen Docker-Netz (kein öffentlicher Port).
