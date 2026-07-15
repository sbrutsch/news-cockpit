"""Erzeugt einen APP_PASSWORD_HASH für das News-Cockpit.

Zwei Wege, aus dem Projektordner:

1. Aus der Zwischenablage (empfohlen bei Passwort-Managern wie Bitwarden):
   Passwort in Bitwarden kopieren, dann:

     Get-Clipboard | python scripts/make_password_hash.py

   Das Passwort taucht dabei weder in der Befehlszeile noch in der
   PowerShell-History auf.

2. Interaktiv (verdeckte Eingabe):

     python scripts/make_password_hash.py

   Hinweis: Einfügen funktioniert auch im verdeckten Prompt — im
   Windows-Terminal mit Strg+V, in der klassischen Konsole per Rechtsklick.
   Es wird nichts angezeigt, aber es kommt an.

Das Passwort NIE als Kommandozeilen-Argument übergeben — Argumente landen
im Klartext in der Shell-History.
"""

import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import hash_password  # noqa: E402

MIN_LAENGE = 10


def read_password():
    if not sys.stdin.isatty():
        # Gepipte Eingabe (z. B. Get-Clipboard | ...): erste Zeile ist das Passwort.
        pw = sys.stdin.readline().rstrip("\r\n")
        if not pw:
            print("Kein Passwort über die Pipe erhalten — abgebrochen.")
            sys.exit(1)
        return pw
    pw1 = getpass.getpass("Neues Passwort: ")
    pw2 = getpass.getpass("Wiederholen:    ")
    if pw1 != pw2:
        print("Passwörter stimmen nicht überein — abgebrochen.")
        sys.exit(1)
    return pw1


def main():
    pw = read_password()
    if len(pw) < MIN_LAENGE:
        print(f"Bitte mindestens {MIN_LAENGE} Zeichen verwenden — abgebrochen.")
        sys.exit(1)
    print("\nIn Coolify als Umgebungsvariable setzen (Haken 'Is Literal?' aktivieren!):\n")
    print(f"APP_PASSWORD_HASH={hash_password(pw)}")


if __name__ == "__main__":
    main()
