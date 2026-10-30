# Format-Experiment: Erzählung gegen Lehrstück

Stand: 2026-10-11 · Laufzeit: acht Beiträge, etwa drei Wochen · Auswertung: `GET /api/experiment`
und die Karte oben im Entwürfe-Tab.

## Hypothese

Die Beiträge aus dem Cockpit bekommen seit Juli weniger Reaktion als die Beiträge vom
Frühjahr: Kommentare je Beitrag von 2,0 auf 0,2, Likes-Median von 6 auf 3, Engagement-Median
von 2,8 % auf 1,4 %. Zwei Belege sprechen dafür, dass es am Format liegt, nicht am Thema:
Die drei reichweitenstärksten Cockpit-Beiträge entstanden am 16. Juli, vor der Qualitätslatte
mit ihrem Pflicht-Prüfraster; und die geeichte Claudia trennt sechs Cockpit-Beiträge kaum,
weil sie einander textlich zu ähnlich sind. Hypothese: Das Erzählformat des Frühjahrs (Szene,
ein Satz je Zeile, Du-Ansprache, Pointe statt Raster) bringt bei gleichen Themen mehr
Kommentare und eine höhere Engagement-Rate als das Lehrstück.

## Design

| | Arm A, Kontrolle | Arm B, Testarm |
|---|---|---|
| Format-Chip | Lehrstück | Erzählung |
| Prompt | heutiges Format mit Qualitätslatte, wörtlich unverändert | Szene, kurze Zeilen, Du, 700 bis 1.300 Zeichen, Pointe; drei eigene Anfänge als Maßstab |
| Beiträge | vier | vier |
| Reihenfolge | B, A, B, A, B, A, B, A, je Posting-Slot abwechselnd (Start mit B am 2026-10-11) | |
| Gleich halten | Posting-Zeit (05:45), Bild ja/nein, Säulen-Mischung, kein Poll, kein Dokument-Post | |
| Themen | aus dem Posteingang wie bisher; kein Thema mit großem Firmennamen in nur einem Arm | |

Das Format wird im Entwurfs-Fenster gewählt (Chips unter der Quellzeile) und beim Speichern
am Entwurf abgelegt. Ohne Speichern gibt es keine Zuordnung und keine Messung.

## Ablauf je Beitrag

1. Fund im Posteingang wählen, Feder klicken.
2. Format-Chip nach Plan setzen (Wechsel erzeugt den Entwurf neu).
3. Einmal prüfen lassen, alle drei Prüfer, als Dokumentation der Teilnoten. **Keine
   Prüfschleife und keine automatische Überarbeitung im Experiment:** Die Prüfer tragen die
   Werte des Lehrstücks (Raster, Fragen, Werkzeug) und würden den Testarm zurückziehen.
   Handarbeit am Text ist erlaubt, solange das Format bleibt.
4. Speichern (Etikett und Teilnoten landen am Entwurf), Text kopieren, in ContentIn für den
   nächsten Slot planen.
5. Nichts weiter: Der Rückkanal markiert am selben Morgen (07:10 UTC) „gepostet" und holt die Kennzahlen, 30 Tage
   lang täglich frisch.

## Messung

Je Beitrag gelten die Kennzahlen sieben Tage nach Veröffentlichung als belastbar; die
Auswertung läuft, sobald alle acht Beiträge sieben Tage alt sind. Gemessen wird je Arm:

- Kommentare je Beitrag (wichtigste Größe, sie zeigt Gespräch)
- Anteil der Beiträge mit mindestens einem Kommentar
- Engagement-Median (Likes plus Kommentare je Impression, aus ContentIn)
- Likes-Median
- Impressionen-Median (nur zur Einordnung; ein Ausreißer wie Mercedes sagt nichts über das Format)

Die Teilnoten der Prüfer werden daneben gelegt, nicht als Maßstab: Interessant ist, ob ein
Kriterium die echte Reaktion vorhersagt. Nach der Eichung streute „Verwertbar Richtung
Vorstand" am stärksten.

## Entscheidungsregel

- **B gewinnt**, wenn Kommentare je Beitrag und Engagement-Median beide höher sind als in A.
  Dann wird Erzählung das Standardformat, und die Qualitätslatte des Lehrstücks wird in die
  Sprache des Erzählformats übersetzt (Pointe statt Raster), die Prüfer-Kriterien folgen.
- **A gewinnt**, wenn beide Größen in A höher sind. Dann bleibt das Lehrstück, und der
  nächste Hebel ist das Thema (Fall mit Namen und Zahl im Opener), nicht die Form.
- **Unentschieden** (eine Größe je Arm oder Unterschiede unter 30 %): Vier weitere Beiträge
  je Arm, dann neu entscheiden. Nicht vorher am Prompt drehen.

## Laufzettel

Die App führt die Zahlen; die Tabelle dient der Planung der Slots.

| Nr. | Slot | Arm | Fund | Entwurf-Nr. | gepostet | 7 Tage um |
|---|---|---|---|---|---|---|
| 1 | Mo 19.10. 07:45 (ContentIn 350681) | B | 636, Haftung bei KI-Agenten | 33 | 19.10., mit Bild | 26.10. |
| 2 | Mi 21.10. 07:45 (ContentIn 350682) | A | 634, Business Judgment Rule | 34 | 21.10., mit Bild | 28.10. |
| 3 | Mo 26.10. 07:45 (ContentIn 353892) | B | 711, Schatten-KI fliegt auf | 35 | 26.10., mit Bild | 02.11. |
| 4 | Mi 28.10. 07:45 (ContentIn 353893) | A | 710, Schatten-KI, Fachbereiche | 36 | 28.10., mit Bild | 04.11. |
| 5 | Mo 02.11. 07:45 (ContentIn 353894) | B | 691, CFO zückt den Taschenrechner | 37 | | 09.11. |
| 6 | Mi 04.11. 07:45 (ContentIn 353895) | A | 699, CFO-Kill-Review | 38 | | 11.11. |
| 7 | Mo 09.11. 07:45 (ContentIn 355778) | B | 700, ERP von 2004 | 40 | | 16.11. |
| 8 | Mi 11.11. 07:45 (ContentIn 355779) | A | 694, GFT: 84 Prozent stoppten | 41 | | 18.11. |

Beitrag 1 (Entwurf 33, erzeugt am 2026-10-11, 996 Zeichen, 20 Zeilen): Ronny 3, Claudia 5,
Markus 3. Erwartet, siehe Schritt 3: Die Prüfer verlangen Raster, These in Zeile eins und ein
Werkzeug, also das Lehrstück. Der Text bleibt, wie er ist; gemessen wird die Reaktion der Leser.

Beitrag 2 (Entwurf 34, Lehrstück, erzeugt am 2026-10-11, 1.602 Zeichen, 227 Wörter): Ronny 5,
Claudia 7, Markus 5. Dieselben Prüfer, dasselbe Thema, zwei Punkte mehr je Stimme für das
Format, dessen Werte sie tragen. Genau dieser Abstand wird nach sieben Tagen gegen die
Reaktion der Leser gelegt.

Beitrag 3 (Entwurf 35, Erzählung, 832 Zeichen, 14 Zeilen) und Beitrag 4 (Entwurf 36,
Lehrstück, 1.271 Zeichen, 193 Wörter), erzeugt am 2026-10-22: Stefan fand den Aufbau beider
Erstfassungen teils unklar. Beide wurden einmal mit Regie-Anweisung überarbeitet (Aufbau,
nicht Inhalt; ohne Prüfer-Feedback, damit die Erzählung Erzählung bleibt) und danach neu
bewertet: Erzählung Ronny 2, Claudia 4, Markus 4; Lehrstück Ronny 3, Claudia 6, Markus 5.
Die Erstfassung des Lehrstücks endete mit einer Hashtag-Zeile, die keiner der 26 bisherigen
Beiträge trägt; in der Endfassung ist sie weg. Beide ohne Bild geplant, Bilder ergänzt
Stefan in ContentIn bei beiden oder bei keinem.

Beitrag 5 (Entwurf 37, Erzählung, 939 Zeichen, 16 Zeilen) und Beitrag 6 (Entwurf 38,
Lehrstück, 1.332 Zeichen), erzeugt am 2026-10-22, Thema CFO im Gremium: Erzählung Ronny 3,
Claudia 6, Markus 5; Lehrstück Ronny 3, Claudia 6, Markus 4. Zwei Handgriffe von Stefan
freigegeben, ohne Nachbewertung: In der Erzählung „Donnerstag, 9 Uhr" statt „Dienstag,
14 Uhr", weil Beitrag 3 denselben Einstieg hatte; im Lehrstück der Absicherungssatz vor der
Schlussfrage gestrichen. Die Noten beziehen sich auf die erzeugte Fassung.

Beitrag 7 (Entwurf 40, Erzählung, 795 Zeichen, 18 Zeilen) und Beitrag 8 (Entwurf 41,
Lehrstück, 1.507 Zeichen, 234 Wörter), erzeugt am 2026-10-30, Thema Altsysteme: Erzählung
Ronny 2, Claudia 3, Markus 4; Lehrstück Ronny 3, Claudia 6, Markus 3. Die Erzählung begann
erzeugt wieder mit „Vorstand. Dienstag. 9 Uhr.", wie die drei davor; eine Regie-Runde nur für
den Einstieg hat den Auftakt auf den Satz im Raum umgestellt, geprüft wurde die Fassung danach.

## Probe vor dem Start (2026-10-11)

Fund 636 (Post-Idee zur Haftung bei KI-Agenten), beide Formate aus demselben Fund im
Produktions-Container erzeugt, nichts gespeichert:

| | Lehrstück | Erzählung |
|---|---|---|
| Zeichen | 1.324 | 910 (Nachprobe 899) |
| Zeilen | 9 | 16 |
| Zeilenlänge, Median | 122 | 50 |
| Aufzählungen | keine, aber Drei-Fragen-Raster am Schluss | keine |
| Einstieg | Behauptung mit Erklärung | Szene: „Vorstandssitzung. Donnerstag. 16:40 Uhr." |

Befund: Der Themenscout gibt in vielen Ideen eine Schlussfrage in Sie-Form vor („Schluss mit
konkreter Frage an die Leser: …"). Beide Formate übernahmen sie wörtlich. Im Lehrstück passt
das, in der Erzählung brach es die Du-Ansprache. Der Testarm-Prompt verlangt seit `a70e268`
Du bis zur letzten Zeile und übersetzt vorgeschlagene Schlussfragen in die Szene; die
Nachprobe endete mit „Wer in deinem Gremium würde heute geradestehen, wenn die Maschine
falsch entscheidet?". Für die Auswertung heißt das: Eine ähnliche Schlussfrage in beiden
Armen ist kein Zufall, sondern die Vorgabe des Funds. Die Arme unterscheiden sich im Weg
dorthin.

## Zwischenstand 2026-10-30

Vier von acht Beiträgen sind draußen, zwei davon älter als sieben Tage. Stand 30.10., 08:50
UTC, Kennzahlen aus ContentIn; die Spalte „bei 48 h" zeigt Impressionen, Likes und
Kommentare zum gleichen Alter, damit die Beiträge vergleichbar sind.

| Beitrag | Arm | Alter | Impressionen | Erreicht | Likes | Kommentare | Engagement | bei 48 h |
|---|---|---|---|---|---|---|---|---|
| 1, Haftung bei KI-Agenten | B | 11 Tage | 531 | 407 | 5 | 1 | 1,13 % | 379 / 2 / 1 |
| 2, Business Judgment Rule | A | 9 Tage | 84 | 56 | 3 | 0 | 3,57 % | 48 / 1 / 0 |
| 3, Schatten-KI fliegt auf | B | 4 Tage | 124 | 83 | 1 | 0 | 0,81 % | 117 / 1 / 0 |
| 4, Schatten-KI, Fachbereiche | A | 2 Tage | 79 | 59 | 2 | 0 | 2,53 % | 79 / 2 / 0 |

Vergleichsbasis: die 14 Cockpit-Lehrstücke vom 24.08. bis 14.10. (ohne Etikett), Median
163 Impressionen, 2 Likes, 1,31 % Engagement, 2 von 14 mit Kommentar.

Lesart, bewusst vorsichtig:

- Reichweite: Erzählung vorn (Median 328 gegen 82), getragen von Beitrag 1. Beitrag 3 blieb
  mit 124 weit darunter, lag bei 48 Stunden aber immer noch über beiden Lehrstücken.
- Beide Lehrstücke des Experiments (84, 79) liegen am unteren Rand der Vergleichsbasis; nur
  der 14.10. (80) war ähnlich schwach. Die Reichweite der Lehrstücke fällt seit Oktober
  (176, 160, 80, 84, 79), das begann vor dem Experiment.
- Kommentare: 1 gegen 0. Der einzige Kommentar seit dem 28.09. kam auf die erste Erzählung,
  gut zwei Stunden nach dem Posten. Wer ihn schrieb, weiß ContentIn nicht.
- Engagement-Rate: Lehrstück vorn (3,05 % gegen 0,97 %), aber auf 80 Impressionen zählen
  zwei Likes 2,5 Prozentpunkte. Die Rate belohnt kleine Reichweite.
- Nach der Entscheidungsregel: eine Größe je Arm, also unentschieden. Bei zwei Beiträgen je
  Arm war nichts anderes zu erwarten.
- Prüfer gegen Leser: Claudia gab dem Lehrstück 2 die beste Note (7), es hat die wenigsten
  Impressionen. Erzählung 1 (Ronny 3, Claudia 5, Markus 3) hat die meisten. Vier Punkte sind
  keine Statistik, sie zeigen aber in dieselbe Richtung wie der Befund vom 11.10.

Konsequenz: nichts am Prompt ändern, Beitrag 5 bis 8 wie geplant, Auswertung nach Beitrag 8
am 18.11. Bleibt es dann bei „eine Größe je Arm", greift die Regel: vier weitere je Arm.

## Nach der Auswertung: Fürsprache-Probe (beschlossen am 2026-10-30)

Anlass: ein gesponserter Beitrag in Stefans Feed (Workwize, „Your IT manager deserves a 200%
raise", 2.109 Reaktionen, 103 Kommentare, 130 Reposts). Die Reichweite war gekauft, der
Mechanismus nicht: These mit Zahl in Zeile eins, an den Chef des Lesers adressiert; eine Liste
von Rollen, in denen sich jeder IT-Leiter wiedererkennt, statt einer Anleitung; Fürsprache, die
IT-Leiter in die eigene Firma weiterreichen; und Kommentare, die die Liste ergänzen („I would
add Facilities manager"), also leicht und ungefährlich. Unsere Schlussfragen verlangen dagegen
ein öffentliches Bekenntnis („Wer in deinem Gremium würde heute geradestehen?"), in beiden
Armen. Das würde erklären, warum beide Arme kaum Kommentare bekommen.

Plan, nach dem 18.11., wenn das Experiment ausgewertet ist:

1. Ein Probe-Beitrag „Fürsprache": Stefan spricht für IT-Leiter in Richtung Gremium
   (Arbeitstitel „Was der Vorstand nicht sieht, wenn er die IT-Vorlage ablehnt"), mit
   Erkennungsliste und einer Ergänzungsfrage am Schluss. Die Probe entsteht als Einzelstück
   (Skript im Container, eigener Prompt, nichts gespeichert außer dem Entwurf); ein drittes
   Format `fuersprache` im Code gibt es erst, wenn die Probe trägt.
2. Die drei Prüfer urteilen zur Dokumentation. Erwartung: niedrige Noten, weil Erkennung
   statt Umsetzbarkeit. Genau das ist der Punkt; die Leser entscheiden.
3. Getrennt davon die Schlussfrage als eigene Variable: Bekenntnisfrage gegen
   Ergänzungsfrage, je zwei Beiträge im Siegerformat des Experiments. Billig, trennbar,
   zielt auf die Kommentare.
4. Nicht übernehmen: Englisch, globale Zielgruppe, Produkt-Link am Ende, gekaufte Reichweite.

Geplant wird nichts ohne Freigabe; die Probe wird vorgelegt wie jeder Experiment-Beitrag.

Die Auswertung selbst läuft am 18.11. um 09:00 als einmalige Desktop-Routine
`format-experiment-auswertung` (nur lesend: ContentIn und dieser Laufzettel; Bericht nach
`assistenz\berichte\format-experiment-auswertung.md`; Master in
`skills-bibliothek\claude-desktop-routinen`, Eintrag in `assistenz\REGISTER.md`). Sie stößt
die Sitzung für die Probe an, macht sie aber nicht.

## Störgrößen, die man kennen sollte

Reichweite hängt am Thema (ein Konzernname bringt Impressionen, nicht Gespräch), am Wochentag
und daran, ob ein Bild dabei ist. Deshalb sind Kommentare und Engagement-Rate die Zielgrößen,
nicht Impressionen, und deshalb wechseln die Arme sich ab, statt zwei Wochen am Stück zu
laufen. Acht Beiträge sind wenig; das Ergebnis ist eine Richtung, kein Beweis. Es reicht, um
zu entscheiden, womit die nächsten zwanzig Beiträge geschrieben werden.
