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
│   ├── pruefer.py    # Prüfstand: lädt app/personas/*.md (generiert aus wissensbasis), Score- und Dimensionen-Parser
│   ├── personas/     # GENERIERT aus dem Kanon (wissensbasis/personas), nie hier editieren
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
- **`tests/test_sicherheit.py` ist kein gewöhnlicher Test.** Er bewacht die
  Befunde des Sicherheits-Checks vom 2026-08-22 (Login-Drossel, Sitzungen am
  Passwort, Ingest-Grenze, Schutz-Header). Wird er rot, ist eine Lücke
  zurückgekehrt — nicht nur ein Test kaputt.

## Deployment-Weg

GitHub-Repo (privat) → Coolify (Dockerfile-Build) → `news.itcoach.cloud`.
Healthcheck: `GET /healthz`. Env-Vars in Coolify pflegen. Auto-Deploy bei Push.

## Die Prüfer .. Herkunft, Belegwert, Quelle

**Seit 2026-09-12 liegen die Personas nicht mehr im Code.** Quelle ist das Repo
`wissensbasis` (Kanon), Ordner `personas/`. Der Generator dort schreibt sie nach
`app/personas/<schluessel>.md`, je mit Kopfzeile „Generiert aus wissensbasis@…".
`pruefer.py` liest beim Start Frontmatter, `## System-Prompt`, `## Rahmen: Seite` und
`## Rahmen: Audit`. **Diese Dateien hier nie editieren**: Der Drift-Check im Kanon meldet
es täglich, der nächste Generator-Lauf überschreibt es. Eine neue Persona ist eine neue
Datei im Kanon, keine Codeänderung. Herkunft und Belegwert stehen in jeder Datei.

| Persona | Woraus entstanden | Zählt bei Beiträgen | Zählt bei Audits |
|---|---|---|---|
| **Ronny Berger** | Originalinterview | wird gefragt, entscheidet nicht | ja |
| **Markus Leitner** | Originalinterview vom 2026-07-17, anonymisiert | ja | ja |
| **Claudia Brenner** | **konstruiert** aus Kundendaten | ja | ja |
| **CFO** (konstruiert, 2026-09-12) | gesetzt für die Gremium-Simulation | nein | ja |
| **Vorstand** (konstruiert, 2026-09-12) | gesetzt für die Gremium-Simulation | nein | ja |

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

- **2026-09-12 (2):** **Workflow-Actions auf Node 24, per Commit-SHA angepinnt.**
  `tests.yml` nutzte `actions/checkout@v4` und `actions/setup-python@v5`; beide laufen auf
  Node 20, das GitHub abkündigt (Warnung in jedem Lauf seit September). Jetzt checkout
  v7.0.1 und setup-python v7.0.0 (Node 24), nicht mehr über den beweglichen Tag, sondern
  über den Commit-SHA der Version mit Versionskommentar: ein verschobener Tag kann so
  keinen fremden Code in den Workflow bringen. Neu `.github/dependabot.yml`, nur für
  Actions, monatlich; die Python-Pakete bleiben bewusst draußen (Regel in
  `requirements.txt`). Geprüft: YAML lädt, Testlauf in der CI auf dem PR grün, Warnung
  weg. Gleiches Muster wie in `wissensbasis` am selben Tag.
- **2026-09-12:** **Personas aus dem Kanon, dritte Lesesituation `audit`.** Die drei
  System-Prompts standen als Konstanten in `pruefer.py` und als Kopien in drei Skills der
  Skills-Bibliothek; Änderungen mussten an vier Orten nachgezogen werden. Jetzt liest
  `pruefer.py` beim Start `app/personas/*.md` (Frontmatter, `## System-Prompt`,
  `## Rahmen: Seite`, `## Rahmen: Audit`); die Dateien erzeugt der Generator des Repos
  `wissensbasis`, je mit Kopfzeile. Neu: CFO und Vorstand als konstruierte Personas für
  die Gremium-Simulation des Audit-Skeletts; `art=audit` liefert Einwände im O-Ton statt
  Content-Noten, wird nie in die Entwurfs-Bibliothek zurückgeführt und nie im Wortlaut
  geloggt; `GET /api/pruefer` nennt je Persona `arten`. Getestet
  (`tests/test_personas.py`): fünf Personas geladen, Kopfzeile vorhanden, Wortlaut kommt
  aus der Datei, Rahmen je Lesesituation, nicht vorgesehene Lesesituation bricht vor dem
  Modellaufruf ab, `art=audit` hinterlässt keinen Entwurf, `art` kennt genau drei Werte.
  Bestehende 29 Tests unverändert grün. Wortlaut der drei alten Prompts ist identisch
  übernommen, der Prüfstand bewertet also weiter wie zuvor.
- **2026-08-26 (3):** **Sicherheits-Check vom 22.08. nachgezogen und gemergt**
  ([PR #1](https://github.com/sbrutsch/news-cockpit/pull/1), vier Tage offen
  liegengeblieben; die ausführliche Fassung steht im
  [`CHANGELOG.md`](CHANGELOG.md) unter 2026-08-22). Vier Lücken repariert:
  umgehbare Login-Drossel, Sitzungen ohne Bindung ans Passwort, vorhersagbarer
  Cookie-Klartext, Ingest ohne Mengengrenze; dazu CSP/HSTS und feste
  Bibliotheks-Versionen. Beim Nachziehen auf den heutigen Stand:
  `tests/test_sicherheit.py` von einem eigenständigen Skript auf `pytest`
  umgestellt, damit die Prüfungen in der CI mitlaufen statt nur auf Zuruf — die
  ursprüngliche Begründung („bewusst ohne pytest, passend zum Rest des
  Projekts") war durch das Testgerüst von heute früh überholt.
  `requirements-dev.txt` zusammengeführt, `httpx2` statt `httpx`, damit
  `starlette.testclient` nicht mehr warnt. Gegenprobe: alle fünf Reparaturen
  einzeln wieder ausgebaut, jede wurde vom richtigen Test gefangen.
  **Bestandscookies werden ungültig — nach dem Deploy einmal neu anmelden.**
**Ältere Einträge stehen in [`CHANGELOG.md`](CHANGELOG.md)** (20 weitere,
zurück bis zum Projektstart am 2026-07-15). Neue Einträge kommen hier oben dazu
und wandern weiter, sobald mehr als drei zusammenkommen.
