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
│   ├── main.py       # FastAPI: Routen, Auth-Dependencies, Dienst-Drossel, Security-Header, .env-Loader
│   ├── db.py         # Speicherschicht: Postgres (psycopg) ODER SQLite über DATABASE_URL
│   ├── auth.py       # PBKDF2-Hash, signierte Session-Cookies, Login-Drossel (stdlib)
│   ├── pruefer.py    # Die drei Ziel-Personas, Score- und Dimensionen-Parser
│   └── transform.py  # Claude-Aufrufe: Entwurf, Überarbeiten, Einordnen (`_claude_text`)
├── public/
│   ├── index.html    # Komplette UI: Vanilla HTML/CSS/JS, kein Build-Step, keine CDN-Abhängigkeit
│   ├── sw.js         # PWA: netz-zuerst, kein API-Caching
│   └── manifest.webmanifest + icons/
├── tests/            # pytest, kein Netz, keine Claude-Aufrufe (Kopf von conftest.py lesen)
├── docs/             # Notizen, die nicht ins Projekt gehören (globale Claude-Regeln)
├── scripts/make_password_hash.py
├── .github/workflows/tests.yml  # py_compile + pytest bei PR und Push nach main
├── Dockerfile        # python:3.12-slim, non-root, CMD python -m app.main; kopiert nur app/ und public/
├── requirements.txt      # fastapi, uvicorn, psycopg[binary], anthropic — landet im Image
└── requirements-dev.txt  # pytest, httpx — bewusst getrennt, NICHT im Image
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

Secrets **ausschließlich** als Umgebungsvariablen — lokal `.env` (ist in
`.gitignore`), Produktion: Coolify-UI. Nie in Code, Doku oder Chat-Ausgaben.
Ein Token, das je in OneDrive/Git lag, gilt als kompromittiert und wird rotiert.

**Welche Variablen es gibt, steht in genau einer Datei: der Env-Tabelle in
`README.md`.** Hier stand bis 2026-08-26 eine zweite, kürzere Liste — und die
war zurückgeblieben (`ANTHROPIC_API_KEY` und `DIENST_TOKEN` fehlten, obwohl
beides Secrets sind). Zwei Listen für dieselbe Sache driften; deshalb steht
hier nur noch das Prinzip.

## Lokale Entwicklung

- venv liegt AUSSERHALB von OneDrive: `%LOCALAPPDATA%\venvs\news-cockpit`
  (windows-safe-editing Regel 7)
- Start: `& "$env:LOCALAPPDATA\venvs\news-cockpit\Scripts\python" -m app.main`
  aus dem Projektordner (liest `.env`, SQLite unter `data/`)
- Nach jeder Python-Änderung:
  `python -m py_compile app/main.py app/db.py app/auth.py app/pruefer.py app/transform.py`
  (alle fünf Module — `pruefer.py` und `transform.py` fehlten hier lange)
- Nach jeder Änderung an `app/`: `pytest -q` (einmalig
  `pip install -r requirements-dev.txt`). Kein Netz, keine Claude-Aufrufe.
  Was bewusst ungetestet bleibt, steht im Kopf von `tests/conftest.py`.
  Dieselben Prüfungen laufen bei jedem Push in GitHub Actions.

## Deployment-Weg

GitHub-Repo (privat) → Coolify (Dockerfile-Build) → `news.itcoach.cloud`.
Healthcheck: `GET /healthz`. Env-Vars in Coolify pflegen. Auto-Deploy bei Push.

## Die drei Prüfer .. Herkunft und Belegwert

Am 2026-08-15 nachgeprüft, weil die Pfade in diesem Dokument ins Leere zeigten.

| Persona | Woraus entstanden | Quelle liegt |
|---|---|---|
| **Ronny Berger** | Originalinterview | `Claude-Code/skills-bibliothek/claude-ai/marktfilter-ronny/references/ronny-marktfilter.md`, dazu `Dokumente/KI/KI-Agenten/Ronny-IT-Leiter.docx` |
| **Markus Leitner** | Originalinterview vom 2026-07-17 | `Claude-Code/Marketing-Cockpit/material/Client - … - 2026-07-17.txt` |
| **Claudia Brenner** | **konstruiert** aus Kundendaten, kein einzelnes Interview | `Dokumente/KI/KI-Agenten/Tagesworkshop/Agent-Material/simulator-claudia-prompt.md` |

**Der Unterschied zählt.** Bei Ronny und Markus ist jede Eigenschaft belegt. Was dort
ergänzt wird, ohne im Interview zu stehen, ist erfunden und senkt den Belegwert genau um
dieses Maß. Claudia darf freier gestaltet werden, weil sie ohnehin eine Zusammensetzung ist.

Die Transkripte nennen Firmen, Kunden und Personen im Klartext. **Nichts davon gehört in
einen Prompt** — Firma, Branche, Namen und Unternehmenshistorie sind bei Markus bewusst
entfernt, ebenso Kennzahlen wie Fluktuation oder Preissteigerung. Sie würden ihn
identifizierbar machen, ohne die Bewertung zu verbessern.

## Alle drei Prüfer geben Teilnoten

Seit 2026-08-15 bewertet jede Persona vier Kriterien mit 1 bis 10 und Begründung.
`parse_dimensionen()` liest sie aus dem Fließtext, ohne ihn zu verändern.

| Ronny | Claudia | Markus |
|---|---|---|
| Umsetzbarkeit | Positionierung im ersten Absatz | Hebel bei den Head-ofs |
| Problemlösung | Thesenschärfe | Worte für stillen Widerstand |
| Substanz statt Coaching-Gelaber | Verwertbar Richtung Vorstand | Ohne Anweisung von oben |
| Budget-Entscheidung | Begründung statt Behauptung | Belegbarkeit |

**Die Herkunft der Kriterien ist je Persona verschieden — und das ist Absicht:**

- **Markus:** aus seinem Interview vom 2026-07-17, jedes mit Belegstelle. Die Head-of-Ebene
  ist sein einziger echter Blocker; der Widerstand kam nie als Argument, nur als Nicht-Tun;
  eine Anweisung von oben erzeugt Gehorsam statt Nutzung; er baut sich selbst eine Metrik.
- **Ronny:** standen von Anfang an in seinem Prompt, wurden nur nie geparst.
- **Claudia:** **gesetzt, nicht interview-belegt** — aber jede Zeile aus ihrem
  dokumentierten Prompt abgeleitet: „ohne erkennbare Positionierung nach dem ersten Absatz
  bist du weg" · „eine neue These oder eine vertraute, ungewohnt scharf" · der jährliche
  Budgetkampf Richtung CFO · „Ratschläge ohne Begründung, Beraterperspektive ohne
  Unternehmensrealität". Da sie aus Kundendaten konstruiert ist, beschädigt das keinen
  Beleg. Wer ihre Kriterien ändert, ändert eine Setzung, kein Interview.

## Der Prüfstand dient jetzt auch anderen Apps

Seit 2026-08-15 nehmen **drei** Routen wahlweise einen Maschinen-Token statt eines
Anmeldecookies an:

| Route | Zweck |
|---|---|
| `GET /api/pruefer` | Wer im Prüfstand steht (Schlüssel, Name, Rolle) |
| `POST /api/pruefen` | `{entwurf, pruefer, art?}` → Note und Rückmeldung |
| `POST /api/ueberarbeiten` | Entwurf anhand des Feedbacks neu schreiben |

**`art` wechselt die Lesesituation (seit 2026-08-17, 4d8b6cc).** `"beitrag"` (Vorgabe)
heißt: die Persona scrollt durch LinkedIn, der Score misst Leseverhalten. `"seite"` heißt:
sie hat auf einen Verweis geklickt und liest eine Landingpage — `pruefer.pruefen()` hängt
dann `_SEITEN_RAHMEN` an, und **der Score misst Kaufnähe** (1–3 nach dem ersten Abschnitt
geschlossen · 8 Termin-Knopf angesehen · 10 gebucht und weiterempfohlen). Die beiden
Skalen sind nicht vergleichbar. Andere Werte weist `main.py` mit 400 ab; die eigene
Oberfläche des News-Cockpits schickt kein `art` und bleibt unverändert.

**Warum:** Das Marketing-Cockpit erzeugt je Launch drei LinkedIn-Beiträge und schickte sie
bisher **ungeprüft** raus. Der Prüfstand hängt an nichts aus dieser Datenbank — er bewertet
einen übergebenen Text. Ihn dort nachzubauen wäre eine zweite Fassung derselben Personas.

**Eigener Token, nicht `INGEST_TOKEN`.** Neu: `DIENST_TOKEN`. Der eine liefert Inhalte ein,
der andere lässt auf Stefans Rechnung generieren. Wird einer bekannt, bleibt der andere
gültig.

**Der Riegel gilt bewusst nur für diese drei.** Alle übrigen Routen geben Fundstücke,
Notizen und Entwürfe heraus und bleiben an die Sitzung gebunden. Ein Token, der
versehentlich bekannt wird, kann **lesend** nichts erreichen.

**Korrektur 2026-08-22 (Sicherheits-Check).** Hier stand bis dahin, ein bekannt
gewordener Token könne „Beiträge benoten und sonst nichts". Das gilt seit dem
Rückfluss vom 20.08. nicht mehr: `art=beitrag` **schreibt** den übergebenen Text
dauerhaft in die Entwurfs-Bibliothek (bis zu `DIENST_LIMIT_PRO_STUNDE` mal pro
Stunde) und erzeugt dabei je Aufruf Anthropic-Kosten. Lesen kann er weiterhin
nichts — der Riegel hält, er ist nur einseitig geworden. Wer den Rückfluss nicht
braucht, setzt `DIENST_RUECKFLUSS=0`.

Ist `DIENST_TOKEN` nicht gesetzt, verhalten sich die Routen wie vorher: nur mit Anmeldung.
Der Wert gehört in die Coolify-Envs beider Apps, **erzeugt und eingetragen von Stefan**
(erledigt am 2026-08-20).

**Drossel, Tageszähler, Rückfluss (seit 2026-08-20).** Token-Aufrufe laufen durch eine
zweite Sicherheitsschicht: POSTs sind auf `DIENST_LIMIT_PRO_STUNDE` (Standard 100,
gleitendes Stundenfenster, In-Memory) gedrosselt — ein geleakter Token erzeugt begrenzt
Kosten, nicht unbegrenzt. Jeder durchgelassene Token-Aufruf wird in `dienst_log`
(tag/route/anzahl) gezählt; das Tagesbriefing zeigt „Prüfdienst: n externe Aufrufe heute".
Sitzungs-Aufrufe (Stefans eigene UI) zählen nicht. **Rückfluss:** Extern geprüfte
Beiträge (`art=beitrag`) landen dedupliziert über den exakten Text in der
Entwurfs-Bibliothek (Quelle „Prüfdienst (extern)"), die Persona-Scores sammeln sich am
selben Eintrag (je Persona ersetzt, nicht dupliziert). Landingpages (`art=seite`) bleiben
bewusst draußen. Abschaltbar mit `DIENST_RUECKFLUSS=0`; Fehler im Rückfluss brechen die
Prüfung nie ab (nur Log).

## Änderungsprotokoll

- **2026-08-26 (2):** **Aufräumen der Reste aus dem Doku-Abgleich.** (a)
  Architektur-Baum zeigte fünf Dateien, die es teils nicht mehr so gab:
  `pruefer.py`, `transform.py`, PWA-Dateien, `tests/`, `docs/`, der Workflow und
  `requirements-dev.txt` fehlten, `anthropic` fehlte bei den Abhängigkeiten.
  (b) Änderungsprotokoll nach `CHANGELOG.md` ausgelagert — es war auf 161 von
  321 Zeilen gewachsen und stand damit den Regeln im Weg, die bei jeder Sitzung
  gelesen werden. In `CLAUDE.md` bleiben die letzten drei Einträge plus Verweis;
  nichts gekürzt, nichts verloren (geprüft: 18 Einträge vorher, 18 nachher).
  (c) `.env.example` kannte `ANTHROPIC_API_KEY`, `TRANSFORM_MODEL` und die drei
  `DIENST_*`-Variablen nicht — ein frisches lokales Setup konnte Verwerten und
  Prüfstand deshalb nicht starten. (d) Die Env-Tabelle in `README.md` nennt jetzt
  auch `SOURCE_COMMIT` und `ENV_FILE`; sie soll die vollständige Liste sein, also
  gehören die beiden hinein. (e) **Neu: `tests/test_env_doku.py`** macht die
  Governance-Regel prüfbar — jede Variable, die `app/` liest, muss in der
  Tabelle stehen, und `.env.example` darf keine toten Variablen nennen. Die
  erste Fassung dieses Tests war wertlos: sie suchte im ganzen README und liess
  sich von einer Erwähnung im Fliesstext täuschen (aufgefallen an der
  Gegenprobe, nicht am grünen Lauf). Sie prüft jetzt die erste Tabellenspalte.
  Gegenprobe: Zeile aus der Tabelle entfernt, tote Variable in `.env.example`,
  neue undokumentierte Env-Lesung im Code, Abschnittsüberschrift umbenannt —
  alle vier wurden gefangen.
- **2026-08-26:** **Testgerüst + Doku-Abgleich.** Anlass: Bewertung eines
  fremden Regelwerks (die „Karpathy"-Prinzipien aus
  `multica-ai/andrej-karpathy-skills`). Übernommen wurde daraus nur, was
  prüfbar ist; die allgemeinen Arbeitsregeln liegen jetzt in
  `docs/claude-globale-regeln.md` (zum Einfügen in `~/.claude/CLAUDE.md`) und
  bewusst NICHT hier — projektweit kopierte Regeln driften. Befunde beim
  Abgleich Doku↔Code: Deployment-Ziel nannte noch `news.sternenozean.de`
  (seit 2026-07-15 (2) überholt); die Secrets-Liste kannte `ANTHROPIC_API_KEY`
  und `DIENST_TOKEN` nicht; `py_compile` deckte 3 von 5 Modulen ab. Alle drei
  behoben, die Secrets-Liste durch einen Verweis auf die vollständige
  Env-Tabelle in `README.md` ersetzt. Neu: `tests/` mit neun Tests auf
  `pytest`, dazu `requirements-dev.txt` — bewusst getrennt von
  `requirements.txt`, das Dockerfile installiert nur letztere und das
  Produktionsimage bleibt unverändert. Getestet: Drossel greift ab Limit+1
  (429) und lässt den teuren Aufruf gar nicht erst zu, GET zählt ohne Drossel,
  Session-Aufrufe zählen nicht, `art=seite` bleibt aus der Bibliothek,
  Rückfluss dedupliziert über den Text und ersetzt je Persona, Ingest-Dedupe
  über `UNIQUE(url)`, `draft_flags` lässt „gepostet" gewinnen, Sitzungstoken
  weist Manipulation und Ablauf ab. Gegenprobe: drei absichtlich eingebaute
  Fehler (Drossel-Off-by-one, Dedupe ausgehebelt, `art`-Filter entfernt) wurden
  je vom richtigen Test gefangen. Damit die Prüfung nicht wieder an der
  Erinnerung hängt, läuft sie seit demselben Tag in GitHub Actions
  (`.github/workflows/tests.yml`, bei Pull Requests und bei Push nach `main`;
  keine Secrets nötig, weil kein Test die Claude-API ruft). Dabei aufgefallen:
  `pytest -q` fand das Paket `app` nicht — das Konsolenskript legt, anders als
  `python -m pytest`, das Arbeitsverzeichnis nicht in den `sys.path`. Behoben
  mit `pytest.ini` (`pythonpath = .`), gilt jetzt für alle Aufrufarten.
- **2026-08-20 (2):** **Dienst-Drossel, Tageszähler, Rückfluss** (Details im
  Prüfstand-Abschnitt oben). Neu: Tabelle `dienst_log`, Envs
  `DIENST_LIMIT_PRO_STUNDE` (100) und `DIENST_RUECKFLUSS` (an),
  `counts.dienst_heute` + Briefing-Zeile. Getestet: Drossel greift ab
  Limit+1 (429), GET zählt ohne Drossel, Session-Aufrufe zählen nicht,
  Rückfluss dedupliziert und ersetzt Scores je Persona.

**Ältere Einträge stehen in [`CHANGELOG.md`](CHANGELOG.md)** (16 weitere,
zurück bis zum Projektstart am 2026-07-15). Ausgelagert am 2026-08-26, weil das
Protokoll auf die Hälfte dieser Datei angewachsen war. Neue Einträge kommen hier
oben dazu und wandern weiter, sobald mehr als drei zusammenkommen.
