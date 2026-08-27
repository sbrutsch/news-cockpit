# Änderungsprotokoll — News-Cockpit

Vollständige Geschichte des Projekts, neueste Einträge zuerst. Jeder Eintrag
nennt Befund, Ursache und was danach geprüft wurde — das ist der eigentliche
Wert, deshalb wird hier nicht gekürzt.

Ausgelagert am 2026-08-26 aus `CLAUDE.md`: Das Protokoll war dort auf 161 von
321 Zeilen gewachsen und stand damit vor allem den projektaktuellen Regeln im
Weg, die Claude bei jeder Sitzung liest. In `CLAUDE.md` stehen jetzt nur noch
die letzten drei Einträge plus ein Verweis hierher.

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
