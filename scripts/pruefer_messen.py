"""Persona-Messung im Produktions-Container: ruft Claude, kostet Geld, aendert nichts.

Misst, wie trennscharf eine Persona wirklich urteilt: Jeder genannte Entwurf wird
einmal bewertet, ausgegeben werden SCORE, die echten LinkedIn-Reaktionen (falls der
Rueckkanal Kennzahlen abgelegt hat) und die Teilnoten; am Ende die Zahl verschiedener
Noten. Eine Persona, die fuer alles dieselbe Note vergibt, misst nichts.

Aufruf per SSH und docker exec im Container (Arbeitsverzeichnis /srv/news-cockpit):

    python scripts/pruefer_messen.py claudia 7 4 18 20 2 11

Erste Messung am 2026-10-11 (Claudia nach der Eichung): Noten 7 7 7 6 6 7 bei Entwuerfen,
die vorher 7 7 8 8 8 8 bekamen. Nur lesend an der Datenbank.
"""

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, pruefer  # noqa: E402


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    persona, ids = argv[0], [int(x) for x in argv[1:]]
    noten = []
    for i in ids:
        d = db.get_draft(i)
        if not d:
            print(f"Entwurf {i}: nicht gefunden")
            continue
        r = pruefer.pruefen(d["text"], persona)
        k = json.loads(d["kennzahlen"] or "{}")
        dims = " | ".join(f"{t['name'][:26]} {t['score']}" for t in r["dimensionen"])
        noten.append(r["score"])
        print(f"Entwurf {i:3d} | SCORE {r['score']} | eng {k.get('engagement')}% "
              f"komm {k.get('comments')} | {dims}")
    if noten:
        print(f"\n{len(noten)} Entwuerfe, {len(set(noten))} verschiedene Noten, "
              f"Schnitt {statistics.mean(noten):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
