"""Verwerten & Einordnen: KI-Funktionen des News-Cockpits.

- linkedin_entwurf(item): LinkedIn-Post-Entwurf aus einem Eintrag
- einordnung(item): Resümee, wie wichtig ein Fund für Stefans Geschäft
  und seine IT-Leiter-Zielgruppe ist (Relevanz hoch/mittel/gering)

Läuft serverseitig über die offizielle Anthropic-SDK; der API-Key kommt aus
der Umgebungsvariable ANTHROPIC_API_KEY (Coolify), nie aus dem Browser.
Modell per TRANSFORM_MODEL übersteuerbar (Standard: claude-sonnet-5 —
Stefans Standardmodell für Content-Erzeugung, gutes Kosten/Qualitäts-Maß
für einen Klick-Workflow).
"""

import json
import os

import anthropic

MODEL = os.environ.get("TRANSFORM_MODEL", "claude-sonnet-5")

_client = None


class TransformError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


SYSTEM = """Du schreibst LinkedIn-Posts für Stefan Brutscher — Sparringspartner für IT-Leiter, deren wichtige Entscheidungen im Management-Gremium zu scheitern drohen.

Positionierung (verbindlich): Entscheidungssicherheit in kritischen Managementmomenten. Fokus auf Durchsetzung, Klarheit und Wirkung im Gremium — nicht auf Technik. Tagline: "Damit Entscheidungen durchgehen." Zielgruppe: IT-Leiter, CIOs und IT-Bereichsleiter im DACH-Raum — fachlich stark, aber unter Druck im Management. Core Values: Klarheit vor Harmonie, Wirkung vor Theorie, Verantwortung vor Komfort.

Schreibregeln:
- Deutsch. Direkt, präzise, auf Augenhöhe. Ziel-Reaktion des Lesers: "Das ist genau meine Situation."
- Hook in der ersten Zeile: eine konkrete Situation oder eine überraschende Zahl. Danach kurze Absätze mit viel Weißraum. 120 bis 220 Wörter.
- Keine Emojis. Höchstens 1-2 dezente Hashtags am Ende, gerne auch keine. Kein Motivations-Pathos, keine KI-Floskeln ("In der heutigen schnelllebigen Welt...", "Lassen Sie uns ehrlich sein").
- Die Quelle nicht nacherzählen: den Entscheidungs- und Gremien-Winkel herausarbeiten. Der Leser soll sich wiedererkennen, nicht informiert fühlen.
- Ende: eine Frage oder pointierte These, die Kommentare von IT-Leitern provoziert — kein Verkaufs-Aufruf.
- Antworte NUR mit dem Post-Text. Keine Anführungszeichen drumherum, kein Kommentar, keine Überschrift."""

_KIND_ANWEISUNG = {
    "news": "Nutze die Meldung als Aufhänger und übertrage sie in die Gremien-Realität eines IT-Leiters.",
    "idee": "Führe diese Content-Idee als fertigen Post aus — sie ist der rote Faden, du gibst ihr Form.",
    "zitat": "Nutze das Zitat als Einstieg (typografisch als Zitat gesetzt) und entwickle daraus den Post.",
}

_KIND_LABEL = {"news": "Meldung", "idee": "Content-Idee", "zitat": "Zitat/Pain-Point"}


def _user_content(item):
    teile = [
        f"Art des Fundstücks: {_KIND_LABEL.get(item['kind'], 'Meldung')}",
        f"Content-Säule: {item['pillar'] or 'keine zugeordnet'}",
        f"Titel: {item['title']}",
    ]
    if item.get("source"):
        teile.append(f"Quelle: {item['source']} ({item['url']})")
    if item.get("summary"):
        teile.append(f"Kern: {item['summary']}")
    if item.get("assessment"):
        teile.append(f"Einordnung (Relevanz {item.get('relevance') or 'unbewertet'}): {item['assessment']}")
    if item.get("note"):
        teile.append(f"Stefans eigene Notiz zu diesem Fund: {item['note']}")
    teile.append("")
    teile.append(_KIND_ANWEISUNG.get(item["kind"], _KIND_ANWEISUNG["news"]))
    if item.get("note"):
        teile.append("Wichtig: Stefans Notiz ist der gewünschte Winkel — baue den Post um diesen Gedanken, nicht um die Zusammenfassung.")
    return "\n".join(teile)


def _claude_text(system, user_content, max_tokens):
    """Gemeinsamer, fehlerfest verpackter Claude-Aufruf; liefert den Antworttext."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise TransformError("ANTHROPIC_API_KEY ist nicht gesetzt — KI-Funktionen sind noch nicht freigeschaltet.", status=503)
    try:
        msg = _get_client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.AuthenticationError:
        raise TransformError("Claude-API: Der hinterlegte API-Key wurde abgelehnt.", status=502)
    except anthropic.RateLimitError:
        raise TransformError("Claude-API ist gerade ausgelastet — bitte kurz warten und erneut versuchen.", status=429)
    except anthropic.APIStatusError as e:
        raise TransformError(f"Claude-API-Fehler ({e.status_code}) — bitte erneut versuchen.", status=502)
    except anthropic.APIConnectionError:
        raise TransformError("Keine Verbindung zur Claude-API — bitte erneut versuchen.", status=502)

    if msg.stop_reason == "refusal":
        raise TransformError("Claude hat die Anfrage abgelehnt (refusal).", status=502)

    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    if not text:
        raise TransformError("Leere Antwort von der Claude-API.", status=502)
    if msg.stop_reason == "max_tokens":
        text += "\n\n[Hinweis: Antwort wurde am Token-Limit abgeschnitten]"
    return text


def linkedin_entwurf(item):
    return _claude_text(SYSTEM, _user_content(item), max_tokens=2000)


EINORDNUNG_SYSTEM = """Du bewertest Fundstücke für Stefan Brutscher — Sparringspartner für IT-Leiter, deren wichtige Entscheidungen im Management-Gremium zu scheitern drohen. Positionierung: Entscheidungssicherheit in kritischen Managementmomenten, "Damit Entscheidungen durchgehen." Zielgruppe: IT-Leiter, CIOs, IT-Bereichsleiter im DACH-Raum — fachlich stark, unter Druck im Management.

Bewerte das Fundstück in zwei Dimensionen:
1. Nutzen für Stefans Geschäft: Taugt es als Content-Aufhänger, Gesprächseinstieg im Sparring, Keynote-Material oder Sichtbarkeits-Thema?
2. Betroffenheit seiner Zielgruppe: Berührt es die Gremien-Realität von IT-Leitern — Budgetkonflikte, Durchsetzung, Machtdynamik, Rechtfertigungsdruck?

Sei ehrlich und streng: "hoch" nur, wenn es direkt auf Entscheidungs- und Gremien-Momente einzahlt. Generische IT-Trends ohne Entscheidungswinkel sind "gering" — auch wenn sie technisch spannend sind. Keine Gefälligkeitsbewertung.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Markdown, ohne Kommentar:
{"relevanz": "hoch" oder "mittel" oder "gering", "resumee": "2 bis 4 Sätze auf Deutsch: Was bedeutet das konkret für Stefans Geschäft und seine IT-Leiter? Direkt und konkret, keine Floskeln. Bei gering: kurz begründen, warum es nicht einzahlt."}"""


def einordnung(item):
    """Bewertet einen Eintrag; liefert (relevanz, resumee)."""
    text = _claude_text(EINORDNUNG_SYSTEM, _user_content(item), max_tokens=1000)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise TransformError("Einordnung nicht lesbar (kein JSON in der Antwort).", status=502)
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        raise TransformError("Einordnung nicht lesbar (JSON-Fehler).", status=502)
    relevanz = data.get("relevanz", "")
    resumee = (data.get("resumee") or "").strip()
    if relevanz not in ("hoch", "mittel", "gering") or not resumee:
        raise TransformError("Einordnung unvollständig — bitte erneut versuchen.", status=502)
    return relevanz, resumee[:2000]
