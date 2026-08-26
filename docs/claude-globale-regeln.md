# Arbeitsregeln für Claude Code — zum Einfügen in `~/.claude/CLAUDE.md`

Diese Datei liegt hier nur zum Abholen. Ihr Platz ist die **globale**
`CLAUDE.md` auf der Workstation (`~/.claude/CLAUDE.md`, unter Windows
`%USERPROFILE%\.claude\CLAUDE.md`) — dort gilt sie für alle Projekte
gleichzeitig. In einzelne Projekt-Dateien kopiert würde sie auseinanderdriften,
so wie es bei der Secrets-Liste des News-Cockpits passiert ist.

**Herkunft:** geprüfte Auswahl aus `multica-ai/andrej-karpathy-skills` (MIT).
Von sechzehn Regeln dort sind vier übrig — die anderen stehen entweder ohnehin
schon in Claude Codes Vorgaben oder ziehen aktiv in die falsche Richtung.

---

## Die vier Regeln

- **Vereinfachen statt nachbessern.** Sieht die fertige Lösung komplizierter aus
  als der offensichtliche einfache Weg, wird sie weggeworfen und neu
  geschrieben — nicht Stück für Stück entschärft.

- **Nur entfernen, was die eigene Änderung verwaist hat.** Importe, Variablen,
  Funktionen: weg darf, was durch diese Änderung überflüssig wurde. Sonst
  nichts.

- **Vorgefundenen toten Code benennen, nicht mitnehmen.** Wer beim Arbeiten auf
  Altlasten stößt, sagt es — und lässt sie liegen, bis sie beauftragt sind.

- **Erst das Prüfkriterium, dann die Arbeit.** Vor dem Anfangen steht, woran
  sich das Ergebnis messen lässt; nach dem Fertigwerden wird genau daran
  gemessen und das Ergebnis genannt. „Sieht gut aus" ist kein Kriterium,
  „`pytest -q` läuft grün und Fall X gibt jetzt 429" ist eins.

---

## Bewusst NICHT übernommen

Damit diese drei beim nächsten Durchsehen nicht doch wieder hereinrutschen:

- **„Bei Unklarheit nachfragen"** und **„mehrere Deutungen vorlegen statt still
  zu wählen".** Claude Code bringt dafür bereits eine kalibrierte Fassung mit:
  Routine-Entscheidungen selbst treffen, nur dann rückfragen, wenn verschiedene
  Lesarten zu materiell verschiedener Arbeit führen. Die schärfere Fassung
  erzeugt einen Agenten, der stehenbleibt — und zwar auch dort, wo niemand
  antwortet: in n8n-Routinen, in Web-Sessions, in `/loop`-Läufen, beim
  automatischen Nacharbeiten an einem Pull Request.

- **„Keine Fehlerbehandlung für Fälle, die nicht eintreten können".** Bei
  öffentlich erreichbaren Schnittstellen trägt „kann nicht eintreten" zu viel
  Gewicht — es ist selbst eine ungeprüfte Annahme und widerspricht damit dem
  ersten Prinzip derselben Vorlage.

Ebenfalls nicht übernommen wurde die angebotene Plugin-Installation. Sie hängt
alle Projekte an ein fremdes Repository, das nicht nur Text nachlädt, sondern
auch Skills und Hooks. Bei Projekten mit Tokens und API-Schlüsseln in der
Umgebung ist das die falsche Vertrauensrichtung — Text lesen und abschreiben
kostet einmal fünf Minuten und bleibt kontrollierbar.

---

## Faustregel für weitere Regeln

Eine Regel ist ihren Platz nur wert, wenn sie das Verhalten ändert.
„Denk nach, bevor du programmierst" ändert wenig — das Modell versucht es
ohnehin. „Nach jeder Änderung an `app/*.py`: `python -m py_compile app/*.py`"
ändert etwas, weil sie prüfbar ist. **Prüfbare Regeln schlagen
Haltungsregeln** — und Haltungsregeln, die den Vorgaben widersprechen, sind
schlechter als gar keine.
