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
│   ├── contentin.py  # Rückkanal: ContentIn-MCP (JSON-RPC), Zuordnung, Kennzahlen, nächtlicher Abgleich
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
`parse_dimensionen()` liest sie aus dem Fließtext, ohne ihn zu verändern. **Seit
2026-10-11 werden sie gespeichert:** `drafts.scores[].dimensionen` trägt je Persona Name
und Note der Kriterien (die Begründung bleibt im Feedback), aus der Oberfläche wie aus dem
Rückfluss; der Score-Chip im Entwürfe-Tab zeigt sie als Tooltip. Damit lässt sich erstmals
auswerten, welches Kriterium einen Beitrag trägt oder reißt.

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
  **Seit 2026-10-11 geeicht** (Kanon `personas/claudia.md`, Abschnitt Eichung): Sie
  vergab 25 von 28 mal die 8 und trennte nichts. Jetzt drei Maßstäbe aus echten
  LinkedIn-Reaktionen auf eigene Beiträge (Entwürfe 6, 16, 25 als 8, 6, 4), Grundrate
  höchstens eine 8 je zehn Beiträge, SCORE nie über dem Durchschnitt ihrer vier Kriterien.

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

## Der Rückkanal von ContentIn

Seit 2026-10-11 weiß das Cockpit, was draußen passiert. Anlass: Seit dem 20.08.
war kein Entwurf mehr als „gepostet" markiert, obwohl 13 nachweislich live
gingen. Der Auto-Archiv-Automatismus griff nicht, der Posteingang wuchs auf
244 Funde, und eine Kalibrierung der Prüfer an echten Reaktionen war unmöglich.

ContentIn hat keine REST-API; der MCP-Server ist die Schnittstelle
(`app/contentin.py`, Streamable HTTP = JSON-RPC über HTTPS, Header `X-MCP-Key`,
`Mcp-Session-Id` wird mitgeführt, JSON- und SSE-Antworten werden gelesen).
Gerufen werden nur `list_posts` und `get_post_analytics`, nie etwas, das
veröffentlicht. Der Abgleich ordnet Beiträge über den normierten Textanfang
(60 Zeichen, ohne HTML/Entities/Typografie) den Entwürfen zu, setzt „gepostet",
speichert `contentin_post_id`, `veroeffentlicht_am` und `kennzahlen` (JSON) am
Entwurf und nimmt den Quell-Fund aus dem Posteingang (`db.archiviere_fund`,
dieselbe Funktion wie beim Markieren von Hand). Kennzahlen der letzten 30 Tage
werden bei jedem Lauf erneuert, ältere nur einmal.

Läuft täglich 01:10 UTC im eigenen Thread, kein n8n nötig, und beim
Containerstart, falls heute noch nicht (Stand in `sync_log`). Von Hand:
`POST /api/sync/contentin` (Sitzung oder Ingest-Token) oder der Knopf neben
dem Export. Ohne `CONTENTIN_MCP_KEY` bleibt alles aus. Ein fehlgeschlagener
Lauf wird geloggt, nicht gemerkt, damit der nächste es erneut versucht.

**Bewusst nicht:** Veröffentlichen oder Planen über ContentIn, und
ContentIn-Themen setzen: `schedule_post` kennt kein Thema-Feld. ContentIns
Säulen-Berichte bleiben deshalb ein Artefakt, solange Beiträge dort nicht von
Hand getaggt werden.

## Änderungsprotokoll

- **2026-10-11 (3):** **Messung der Claudia-Eichung: Kriterium 1 verfehlt, Kriterium 2
  erfüllt.** Sechs Beiträge, die nicht Maßstab sind, im Produktions-Container mit dem
  neuen `scripts/pruefer_messen.py` geprüft (sechs Claude-Aufrufe, Cent-Betrag): Noten
  7, 7, 7, 6, 6, 7, vorher 7, 7, 8, 8, 8, 8. Zwei verschiedene Noten statt drei; stark
  7,0 gegen schwach 6,5, richtige Richtung, kleiner Abstand. Lesart: Der Freifahrtschein
  ist weg, die Prüfschleife bekommt von Claudia keine 8 mehr geschenkt. Trennschärfe im
  engen Band entsteht aber nicht im Prompt: Die sechs Beiträge entstammen demselben
  Generator und Format und sind einander textlich ähnlich, die Unterschiede in den
  Reaktionen kommen eher aus Thema und Zeitpunkt. Deshalb nicht weiter am Prompt gedreht
  (vereinfachen statt nachbessern), sondern als Beleg für das Format-Experiment
  festgehalten, im Kanon wie hier. Teilnoten der Messung: „Verwertbar Richtung Vorstand"
  streut 5 bis 8 und ist das Kriterium mit dem größten Ausschlag.
- **2026-10-11 (2):** **Claudia geeicht, Teilnoten gespeichert.** Befund aus den
  Produktionsdaten: Claudia vergab 25 von 28 mal die 8, Ronny nie, die Prüfschleife
  endete in 29 von 29 Fällen in Runde 1. Claudia ist im Kanon geeicht
  (`wissensbasis@85c4041`, `personas/claudia.md`, neuer Abschnitt Eichung; Vertrag in
  `personas/README.md` um den optionalen Abschnitt ergänzt): drei Maßstäbe aus echten
  LinkedIn-Reaktionen auf eigene Beiträge (Entwürfe 6, 16, 25 als 8, 6, 4), Grundrate
  höchstens eine 8 je zehn Beiträge, SCORE nie über dem Durchschnitt der vier Kriterien.
  Kopie per Generator nach `app/personas/claudia.md`; die Skills-Bibliothek trägt keine
  Claudia-Kopie (Generator-Check: nichts zu schreiben). Teilnoten landen jetzt in
  `drafts.scores[].dimensionen`, aus der Oberfläche wie aus dem Rückfluss, Tooltip am
  Score-Chip; zwei Tests in `tests/test_teilnoten.py`. Prüfkriterium der Eichung: sechs
  Beiträge, die nicht Maßstab sind, ergeben mindestens drei verschiedene Noten, und die
  zwei mit den meisten Reaktionen liegen über den zwei mit den wenigsten. Messung: siehe
  Eintrag (3).
- **2026-10-11:** **Rückkanal von ContentIn** (`app/contentin.py`, Abschnitt
  oben). Anlass war die Auswertung der Generierung gegen 30 Entwürfe und 41
  veröffentlichte Beiträge: Prüfer ohne Trennschärfe (Claudia 25 von 28 mal
  8, Ronny nie 8, Schleife endet in 29 von 29 Fällen in Runde 1), Kommentare
  je Beitrag von 2,0 (Frühjahr) auf 0,2 (Sept/Okt), und das Cockpit wusste
  seit 20.08. nicht mehr, was gepostet wurde. Neu: Spalten `contentin_post_id`,
  `veroeffentlicht_am`, `kennzahlen` an `drafts` (Migration in `db.init`),
  Tabelle `sync_log`, `db.archiviere_fund` statt Inline-Code in `patch_draft`,
  Envs `CONTENTIN_MCP_KEY`/`CONTENTIN_MCP_URL`, Route `POST /api/sync/contentin`,
  Abgleich-Knopf und Kennzahlen-Zeile im Entwürfe-Tab. Getestet ohne Netz:
  Zuordnung über Textanfang inkl. HTML und Entities, Textvariante wird nicht
  zugeordnet, Markieren mit Kennzahlen und Auto-Archiv, Idempotenz und kein
  zweiter Analytics-Abruf für alte Beiträge, 401/503/200 am Endpunkt, SSE-
  und JSON-Antworten, Session-Id-Mitführung, Fehlerpfad.
**Ältere Einträge stehen in [`CHANGELOG.md`](CHANGELOG.md)** (23 weitere,
zurück bis zum Projektstart am 2026-07-15). Neue Einträge kommen hier oben dazu
und wandern weiter, sobald mehr als drei zusammenkommen.
