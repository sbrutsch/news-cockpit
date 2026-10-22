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
5. Nichts weiter: Der Rückkanal markiert am selben Morgen (06:10 UTC) „gepostet" und holt die Kennzahlen, 30 Tage
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
| 2 | Mi 21.10. 07:45 (ContentIn 350682) | A | 634, Business Judgment Rule | 34 | | 28.10. |
| 3 | Mo 26.10. 07:45 (ContentIn 353892) | B | 711, Schatten-KI fliegt auf | 35 | | 02.11. |
| 4 | Mi 28.10. 07:45 (ContentIn 353893) | A | 710, Schatten-KI, Fachbereiche | 36 | | 04.11. |
| 5 | | B | | | | |
| 6 | | A | | | | |
| 7 | | B | | | | |
| 8 | | A | | | | |

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

## Störgrößen, die man kennen sollte

Reichweite hängt am Thema (ein Konzernname bringt Impressionen, nicht Gespräch), am Wochentag
und daran, ob ein Bild dabei ist. Deshalb sind Kommentare und Engagement-Rate die Zielgrößen,
nicht Impressionen, und deshalb wechseln die Arme sich ab, statt zwei Wochen am Stück zu
laufen. Acht Beiträge sind wenig; das Ergebnis ist eine Richtung, kein Beweis. Es reicht, um
zu entscheiden, womit die nächsten zwanzig Beiträge geschrieben werden.
