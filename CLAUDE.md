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
- Nach Änderungen an Anmeldung, Token, Drosseln oder Headern zusätzlich
  `python tests/test_sicherheit.py` (34 Prüfungen, Rückgabewert 0 = alles gut).
  Der Test bewacht die Befunde des Sicherheits-Checks vom 2026-08-22 — wird er
  rot, ist eine Lücke zurückgekehrt, nicht nur ein Test kaputt. Braucht
  `pip install -r requirements-dev.txt`; läuft gegen eine Wegwerf-SQLite im
  Temp-Ordner, fasst die Produktion nie an.

## Deployment-Weg

GitHub-Repo (privat) → Coolify (Dockerfile-Build) → `news.sternenozean.de`.
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

- **2026-08-22:** **Sicherheits-Check und sechs Reparaturen.** Bestandsaufnahme
  über Code, alle 19 Routen und die gesamte Git-Historie: keine Geheimnisse im
  Repo (`.env` war nie eingecheckt), keine Tabelle ohne Anmeldung lesbar, kein
  SQL-Injection- oder XSS-Weg. Repariert wurden:
  (a) **Login-Drossel war umgehbar** — `client_ip()` nahm den ERSTEN
  `X-Forwarded-For`-Eintrag, den der Aufrufer selbst schreibt; 500 Versuche mit
  wechselndem Wert wurden nachweislich nie gesperrt. Jetzt wird von rechts
  gezählt (`TRUSTED_PROXY_HOPS`, Standard 1).
  (b) **Sitzungen hingen nicht am Passwort** — ein Passwortwechsel warf ein
  gestohlenes Cookie 30 Tage lang nicht raus. Der Signierschlüssel wird jetzt
  aus `SECRET_KEY` + Passwort abgeleitet (`auth._session_key`), damit beendet
  jeder Passwortwechsel alle offenen Sitzungen. **Bestandscookies werden
  ungültig — nach dem Deploy einmal neu anmelden.**
  (c) **Signierter Klartext war vorhersagbar** (nur ein Unix-Zeitstempel) —
  jetzt mit Zufallsanteil, damit ein schwacher `SECRET_KEY` nicht offline gegen
  ein bekanntes Ziel geraten werden kann.
  (d) **Ingest hatte keine Mengengrenze** (500 Einträge je Aufruf, beliebig
  oft) — neu `INGEST_LIMIT_PRO_STUNDE` (Standard 60) über den neuen Baustein
  `_Stundenfenster`, den sich Ingest und Prüfdienst jetzt teilen.
  (e) **CSP und HSTS ergänzt**; HSTS bewusst nur über HTTPS, sonst würde der
  Browser den lokalen Entwicklungs-Port dauerhaft auf HTTPS umbiegen.
  (f) **Bibliotheks-Versionen exakt festgeschrieben** statt frei mitwandernd.
  Getestet: 26 End-to-End-Prüfungen gegen die echte App (Drossel greift trotz
  gefälschtem Header, anderer Absender bleibt frei, Passwortwechsel entwertet
  Cookies, Ingest-Drossel, alle Header, Anmeldung und Oberfläche unverändert).
  Offen und bewusst nicht angefasst: Prompt-Injection über eingelieferte Texte
  (Schutz bleibt Stefans Sichtung vor dem Posten) und die Frage, ob die
  Coolify-Oberfläche öffentlich erreichbar ist.
- **2026-08-20 (2):** **Dienst-Drossel, Tageszähler, Rückfluss** (Details im
  Prüfstand-Abschnitt oben). Neu: Tabelle `dienst_log`, Envs
  `DIENST_LIMIT_PRO_STUNDE` (100) und `DIENST_RUECKFLUSS` (an),
  `counts.dienst_heute` + Briefing-Zeile. Getestet: Drossel greift ab
  Limit+1 (429), GET zählt ohne Drossel, Session-Aufrufe zählen nicht,
  Rückfluss dedupliziert und ersetzt Scores je Persona.
- **2026-08-20:** **Verwertungs-Kennzeichnung.** Stefans Befund: In der Liste
  ist nicht erkennbar, welche Funde schon zu Entwürfen verarbeitet wurden.
  Automatisch aus der bestehenden Verknüpfung `drafts.item_id` abgeleitet
  (kein neues Feld, keine Handarbeit): `db.draft_flags()` liefert je Fund
  `entwurf`/`gepostet`, `/api/items` hängt es als `verwertet` an, die Karte
  zeigt einen klickbaren Chip (grün-Outline „verwertet" bzw. gefüllt
  „gepostet"; Klick springt zum Entwurf im Entwürfe-Tab). Automatismus:
  Entwurf auf „gepostet" → Quell-Fund wandert automatisch aus Neu ins Archiv
  (`item_archiviert` in der PATCH-Antwort; Rücknahme bewusst manuell).

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
- **2026-07-22:** **Update-Erkennung.** Stefans Doppel-Überarbeitungs-Meldung
  entpuppte sich als altes JS in einem seit Stunden offenen PWA-Fenster —
  offene Fenster bekommen Deployments nie mit. Neu: `GET /api/version`
  (SOURCE_COMMIT von Coolify, Fallback Container-Startzeit) + Frontend-Check
  (Start, visibilitychange, alle 15 Min) → Leiste „Neue Version verfügbar —
  Jetzt neu laden / Später" (Später nervt pro Version nur einmal; offener
  Entwurf ist durch die Auto-Sicherung geschützt).
- **2026-07-17 (6):** **Layout-Fix, Schleifen-Stopp, Absturz-Sicherung**
  (Stefans Befunde). (a) Sechs Fußleisten-Knöpfe sprengten das 640px-Panel
  (Screenshot: umgebrochene Riesen-Knöpfe, „Schließen" ragte raus) →
  vw-foot flex-wrap, „Mit Feedback überarbeiten"→„Überarbeiten", Panel-Breite
  hängt an .vw-panel.breit und bleibt während Überarbeitungs-Laden stehen
  (kein Springen 1160↔640). (b) Prüfschleife wirkte endlos/unaufhaltbar
  (3 Prüfer × 3 Runden ≈ 5-7 Min, Karten resetten, Toasts flüchtig; Schleife
  selbst ist hart gedeckelt — Code + Test): Knopf wird während des Laufs zum
  „Stopp" (greift am nächsten Zwischenschritt), Titel zeigt „RUNDE n VON 3"
  und bleibendes Fazit, Karten-Knöpfe während des Laufs gesperrt
  (pruefenLassen-Guard). (c) Chrome-Absturz kostete 4 Runden Arbeit →
  Auto-Sicherung in localStorage (cockpit_vw_autosave, bei jedem
  renderDraft/Tastendruck; bewusstes Schließen räumt auf) + Wiederherstellungs-
  Leiste beim Start („Öffnen"/„Verwerfen", 72h-Verfall).
- **2026-07-17 (5):** **Dritter Prüfer: Markus Leitner** — destilliert und
  hart anonymisiert aus Stefans realem IT-Leiter-Interview vom 17.07.
  (Transkript auf Desktop; Firma/Branche/Namen/Historie im Code bewusst
  entfernt, Tabu-Begriffe-Check gelaufen). Archetyp: KI-affiner
  Erste-100-Tage-Head-of-IT im Mittelstand, Pilot erfolgreich, kämpft mit
  Change-Widerstand der Head-of-Ebene; Struktur SO LESE ICH DAS / WAS ICH
  MITNEHME / WAS MIR FEHLT. Dritte Karte im Prüfstand (grün-teal), Schleife
  fragt jetzt alle drei. Aus dem Interview offen: Transkript-Eingangskanal
  (Stefan hat sich vorerst nur für die Persona entschieden).
- **2026-07-17 (4):** **Verlust-Schutz + Token-Limit-Fix** (Stefans Befunde
  aus Runde 3/4 der Praxis). (a) Klick neben das Modal schließt NICHT mehr;
  explizites Schließen (×, Schließen, Esc) fragt nach, wenn die Prüfschleife
  läuft oder der Entwurf vom letzten gespeicherten Stand abweicht
  (vw.gesichert; openDraft/saveDraft setzen ihn). (b) max_tokens rauf:
  Entwurf/Überarbeiten 2000→6000, Prüfen 2500→4000; Abschnitt-Hinweis wird
  vor der nächsten Runde aus dem Entwurf entfernt; _UEBERARBEITEN_SYSTEM:
  „schärfen, nicht verlängern" gegen rundenweises Aufblähen.
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
