"""IT-Leiter-Pruefstand: Personas bewerten Entwuerfe, Landingpages und Audit-Vorlagen.

Die Personas liegen NICHT mehr im Code. Sie kommen als Markdown-Dateien aus dem Kanon
(Repo wissensbasis, Ordner personas/) und werden vom Generator dort nach
app/personas/<schluessel>.md kopiert, je mit Kopfzeile "Generiert aus wissensbasis@...".
Diese Dateien hier nicht editieren: Der Drift-Check meldet es, der naechste
Generator-Lauf ueberschreibt es. Eine neue Persona ist eine neue Datei, keine
Codeaenderung.

Vertrag je Datei (personas/README.md im Kanon):
  - Frontmatter mit schluessel, name, rolle
  - Abschnitt "## System-Prompt": der Wortlaut fuer die Lesesituation Beitrag
  - Abschnitt "## Rahmen: Seite": Zusatz fuer art=seite (oder "Nicht vorgesehen")
  - Abschnitt "## Rahmen: Audit": Zusatz fuer art=audit (Gremium-Simulation)

Vereinheitlicht ist nur die erste Zeile "SCORE: n" (1-10), damit die UI eine Ampel
zeigen kann; die kommt aus _FORMAT_HINWEIS hier im Code, nicht aus der Persona.
"""

import re
from pathlib import Path

from app.transform import TransformError, _claude_text

PERSONA_ORDNER = Path(__file__).resolve().parent / "personas"
ARTEN = ("beitrag", "seite", "audit")

_FORMAT_HINWEIS = """
Deine Antwort beginnt zwingend mit einer einzelnen Zeile im Format
SCORE: [Zahl 1-10]
Danach folgt deine Bewertung in deiner eigenen Struktur. Antworte immer auf Deutsch."""

_EINLEITUNG = {
    "beitrag": "Hier ist der zu bewertende LinkedIn-Beitrag:",
    "seite": "Hier ist der vollstaendige Text der zu bewertenden Landing Page:",
    "audit": "Hier ist die anonymisierte Entscheidungsvorlage fuer das Gremium:",
}

_FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_ABSCHNITT_RE = re.compile(r"^## (.+?)\s*$", re.M)
_NICHT_VORGESEHEN = "nicht vorgesehen"


def _frontmatter(text):
    """Kleiner Parser fuer 'schluessel: wert'-Zeilen; PyYAML gehoert nicht ins Image."""
    m = _FM_RE.match(text)
    werte = {}
    if not m:
        return werte
    for zeile in m.group(1).splitlines():
        if ":" not in zeile or zeile.startswith(" "):
            continue
        k, _, v = zeile.partition(":")
        werte[k.strip()] = v.strip().strip('"').strip("'")
    return werte


def _abschnitte(text):
    """Alle H2-Abschnitte als {Titel: Inhalt}."""
    treffer = list(_ABSCHNITT_RE.finditer(text))
    ergebnis = {}
    for i, m in enumerate(treffer):
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        ergebnis[m.group(1).strip()] = text[m.end():ende].strip()
    return ergebnis


def _lade_persona(pfad):
    text = pfad.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    abschnitte = _abschnitte(text)
    system = abschnitte.get("System-Prompt", "").strip()
    schluessel = fm.get("schluessel") or pfad.stem
    if not system:
        raise RuntimeError(f"Persona {pfad.name}: Abschnitt '## System-Prompt' fehlt oder ist leer")
    if not fm.get("name"):
        raise RuntimeError(f"Persona {pfad.name}: 'name' fehlt im Frontmatter")

    def rahmen(titel):
        inhalt = abschnitte.get(titel, "").strip()
        if not inhalt or inhalt.lower().startswith(_NICHT_VORGESEHEN):
            return None
        return inhalt

    return schluessel, {
        "name": fm["name"],
        "rolle": fm.get("rolle", ""),
        "system": system + _FORMAT_HINWEIS,
        "rahmen": {"seite": rahmen("Rahmen: Seite"), "audit": rahmen("Rahmen: Audit")},
        "datei": pfad.name,
    }


def lade_personas(ordner=PERSONA_ORDNER):
    """Liest alle app/personas/*.md. Reihenfolge: Dateiname, damit die UI stabil bleibt."""
    personas = {}
    for pfad in sorted(Path(ordner).glob("*.md")):
        if pfad.name.upper() == "README.MD":
            continue
        schluessel, daten = _lade_persona(pfad)
        personas[schluessel] = daten
    if not personas:
        raise RuntimeError(f"Keine Personas unter {ordner} gefunden (Generator aus wissensbasis laufen lassen)")
    return personas


PRUEFER = lade_personas()


def arten_fuer(key):
    """Welche Lesesituationen eine Persona beherrscht (fuer GET /api/pruefer)."""
    p = PRUEFER[key]
    return ["beitrag"] + [art for art in ("seite", "audit") if p["rahmen"].get(art)]


_SCORE_RE = re.compile(r"SCORE:\s*(\d{1,2})", re.IGNORECASE)

# Teilnoten der Bauart "- Umsetzbarkeit: 8 - Begruendung".
# Bewusst allgemein gehalten: sobald eine andere Persona denselben Aufbau
# ausgibt, wird sie ohne Codeaenderung mitgelesen.
_DIM_RE = re.compile(
    r"^[ \t]*[-*•]\s*"          # Aufzaehlungszeichen
    r"([^:\n\[\]]{2,60}?)\s*:\s*"    # Name der Dimension
    r"\[?\s*(\d{1,2})\s*\]?"         # Note, Klammern optional (Vorlage nutzt [n])
    r"\s*(?:[-–—]\s*(.*))?$",  # Begruendung, freiwillig
    re.MULTILINE,
)


def parse_dimensionen(text):
    """Teilnoten aus dem Fliesstext holen.

    Gibt eine Liste aus {name, score, begruendung} zurueck. Der Text bleibt
    unangetastet — die Zeilen stehen weiterhin im Feedback, damit die
    bestehende Oberflaeche unveraendert weiterlaeuft.
    """
    gefunden = []
    gesehen = set()
    for m in _DIM_RE.finditer(text):
        name = " ".join(m.group(1).split())
        wert = int(m.group(2))
        # Nur 1 bis 10 gilt als Note. Alles andere ist eine Zahl im Fliesstext,
        # etwa ein Preis oder eine Jahreszahl.
        if not 1 <= wert <= 10:
            continue
        schluessel = name.casefold()
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        begruendung = (m.group(3) or "").strip().strip("[]").strip()
        gefunden.append({"name": name, "score": wert, "begruendung": begruendung})
    return gefunden


def parse_score(text):
    """Erste SCORE-Zeile extrahieren; Rest bleibt Feedback. (None, text) wenn keine gefunden."""
    m = _SCORE_RE.search(text)
    if not m:
        return None, text.strip()
    score = max(1, min(10, int(m.group(1))))
    rest = (text[:m.start()] + text[m.end():]).strip()
    return score, rest


def system_prompt(key, art="beitrag"):
    """System-Prompt der Persona fuer eine Lesesituation. Prueft VOR jedem Modellaufruf."""
    if key not in PRUEFER:
        raise TransformError("Unbekannter Pruefer.", status=400)
    if art not in ARTEN:
        raise TransformError("Unbekannte Lesesituation.", status=400)
    p = PRUEFER[key]
    if art == "beitrag":
        return p["system"]
    rahmen = p["rahmen"].get(art)
    if not rahmen:
        raise TransformError(f"{p['name']} bewertet keine Lesesituation '{art}'.", status=400)
    return p["system"] + "\n\n" + rahmen


def pruefen(entwurf, key, art="beitrag"):
    system = system_prompt(key, art)
    text = _claude_text(
        system,
        f"{_EINLEITUNG[art]}\n\n{entwurf}",
        max_tokens=4000,
    )
    score, feedback = parse_score(text)
    return {"pruefer": key, "name": PRUEFER[key]["name"], "rolle": PRUEFER[key]["rolle"],
            "score": score, "feedback": feedback,
            "dimensionen": parse_dimensionen(feedback)}
