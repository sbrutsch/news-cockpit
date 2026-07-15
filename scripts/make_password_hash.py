"""Erzeugt einen APP_PASSWORD_HASH für das News-Cockpit.

Aufruf aus dem Projektordner:  python scripts/make_password_hash.py
Das Passwort wird verdeckt eingegeben und erscheint nirgends im Klartext.
"""

import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import hash_password  # noqa: E402


def main():
    pw1 = getpass.getpass("Neues Passwort: ")
    pw2 = getpass.getpass("Wiederholen:    ")
    if pw1 != pw2:
        print("Passwörter stimmen nicht überein — abgebrochen.")
        sys.exit(1)
    if len(pw1) < 10:
        print("Bitte mindestens 10 Zeichen verwenden — abgebrochen.")
        sys.exit(1)
    print("\nIn Coolify (oder .env) als Umgebungsvariable setzen:\n")
    print(f"APP_PASSWORD_HASH={hash_password(pw1)}")


if __name__ == "__main__":
    main()
