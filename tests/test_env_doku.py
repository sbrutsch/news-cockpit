"""Code und Env-Doku dürfen nicht auseinanderlaufen.

`CLAUDE.md` erklärt die Env-Tabelle in `README.md` zur einzigen maßgeblichen
Liste. Bis 2026-08-26 gab es dort eine zweite, kürzere Liste — und die war
zurückgeblieben (`ANTHROPIC_API_KEY` und `DIENST_TOKEN` fehlten, obwohl beides
Secrets sind). Eine Regel, die niemand prüft, verfällt genauso; deshalb prüft
sie dieser Test.

Geprüft wird ausdrücklich die **erste Spalte der Tabelle**, nicht die Datei als
Ganzes: Ein Variablenname, der irgendwo im Fließtext auftaucht, ist nicht
dokumentiert. (Genau daran ist die erste Fassung dieses Tests gescheitert — sie
suchte im ganzen README und liess sich von einer Erwähnung im Fliesstext
täuschen.)
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parent.parent

# os.environ["X"] · os.environ.get("X") · os.getenv("X")
_ENV_RE = re.compile(
    r"""(?:os\.environ(?:\.get)?\(|os\.environ\[|getenv\()\s*["']([A-Z][A-Z0-9_]*)["']""")
_NAME_RE = re.compile(r"`([A-Z][A-Z0-9_]*)`")


def _gelesene_variablen():
    """Was die Module unter app/ wirklich aus der Umgebung lesen."""
    namen = set()
    for datei in sorted((WURZEL / "app").glob("*.py")):
        namen |= set(_ENV_RE.findall(datei.read_text(encoding="utf-8")))
    return namen


def _dokumentierte_variablen():
    """Erste Spalte der Env-Tabelle — nur echte Tabellenzeilen zählen."""
    namen, im_abschnitt = set(), False
    for zeile in (WURZEL / "README.md").read_text(encoding="utf-8").splitlines():
        if zeile.startswith("## "):
            im_abschnitt = zeile.startswith("## Konfiguration")
            continue
        if im_abschnitt and zeile.startswith("|"):
            namen |= set(_NAME_RE.findall(zeile.split("|")[1]))
    return namen


def test_jede_gelesene_variable_steht_in_der_readme_tabelle():
    gelesen = _gelesene_variablen()
    assert gelesen, "Regex findet keine Variablen mehr — der Test wäre wertlos"

    fehlend = sorted(gelesen - _dokumentierte_variablen())
    assert not fehlend, (
        "Diese Variablen liest der Code, aber die Env-Tabelle in README.md "
        f"kennt sie nicht: {fehlend}")


def test_env_beispiel_erfindet_nichts():
    """Gegenrichtung: `.env.example` darf keine toten Variablen nennen."""
    genannt = set()
    for zeile in (WURZEL / ".env.example").read_text(encoding="utf-8").splitlines():
        treffer = re.match(r"^#?\s*([A-Z][A-Z0-9_]*)=", zeile.strip())
        if treffer:
            genannt.add(treffer.group(1))
    assert genannt, "Aus .env.example wurde keine Variable gelesen"

    tot = sorted(genannt - _gelesene_variablen())
    assert not tot, f".env.example nennt Variablen, die kein Modul liest: {tot}"
