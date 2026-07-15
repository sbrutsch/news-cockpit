"""Verwerten: Aus einem Cockpit-Eintrag einen LinkedIn-Post-Entwurf erzeugen.

Läuft serverseitig über die offizielle Anthropic-SDK; der API-Key kommt aus
der Umgebungsvariable ANTHROPIC_API_KEY (Coolify), nie aus dem Browser.
Modell per TRANSFORM_MODEL übersteuerbar (Standard: claude-sonnet-5 —
Stefans Standardmodell für Content-Erzeugung, gutes Kosten/Qualitäts-Maß
für einen Klick-Workflow).
"""

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
    teile.append("")
    teile.append(_KIND_ANWEISUNG.get(item["kind"], _KIND_ANWEISUNG["news"]))
    return "\n".join(teile)


def linkedin_entwurf(item):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise TransformError("ANTHROPIC_API_KEY ist nicht gesetzt — Verwerten ist noch nicht freigeschaltet.", status=503)
    try:
        msg = _get_client().messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            messages=[{"role": "user", "content": _user_content(item)}],
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
        text += "\n\n[Hinweis: Entwurf wurde am Token-Limit abgeschnitten]"
    return text
