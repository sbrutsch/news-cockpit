"""Authentifizierung: Passwort-Hashing, signierte Session-Cookies, Login-Drossel.

Nur Standardbibliothek. Secrets kommen ausschließlich aus Umgebungsvariablen
(Governance-Regel: nie in Dateien, die in Git/OneDrive liegen).
"""

import base64
import hashlib
import hmac
import os
import secrets
import time

SESSION_COOKIE = "nc_session"
SESSION_TTL = 60 * 60 * 24 * 30  # 30 Tage

# Ohne SECRET_KEY funktioniert alles, aber Sessions überleben keinen Neustart.
SECRET_KEY = os.environ.get("SECRET_KEY", "")
SECRET_KEY_IS_EPHEMERAL = not SECRET_KEY
if SECRET_KEY_IS_EPHEMERAL:
    SECRET_KEY = secrets.token_hex(32)

_pw_hash_cache = None

# Login-Drossel: max. Fehlversuche pro IP und Zeitfenster
MAX_ATTEMPTS = 10
WINDOW_SECONDS = 900
_attempts = {}  # ip -> (fehlversuche, fensterstart)


def _b64e(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password, iterations=600_000):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64e(salt)}${_b64e(dk)}"


def verify_password(password, stored):
    try:
        algo, iters, salt_s, hash_s = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64d(salt_s), int(iters))
        return hmac.compare_digest(dk, _b64d(hash_s))
    except Exception:
        return False


def get_password_hash():
    """APP_PASSWORD_HASH bevorzugt; APP_PASSWORD (Klartext-Env) als Komfort-Fallback."""
    global _pw_hash_cache
    if _pw_hash_cache is None:
        h = os.environ.get("APP_PASSWORD_HASH", "").strip()
        if not h:
            pw = os.environ.get("APP_PASSWORD", "")
            h = hash_password(pw) if pw else ""
        _pw_hash_cache = h
    return _pw_hash_cache


def create_session_token(now=None):
    exp = str(int((now or time.time()) + SESSION_TTL)).encode()
    sig = hmac.new(SECRET_KEY.encode(), exp, hashlib.sha256).digest()
    return f"{_b64e(exp)}.{_b64e(sig)}"


def verify_session_token(token):
    try:
        payload_s, sig_s = token.split(".")
        payload = _b64d(payload_s)
        expected = hmac.new(SECRET_KEY.encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_s)):
            return False
        return int(payload) > time.time()
    except Exception:
        return False


def verify_ingest_token(candidate):
    expected = os.environ.get("INGEST_TOKEN", "")
    if not expected or not candidate:
        return False
    return hmac.compare_digest(candidate, expected)


def login_allowed(ip):
    count, start = _attempts.get(ip, (0, time.time()))
    if time.time() - start > WINDOW_SECONDS:
        return True
    return count < MAX_ATTEMPTS


def register_failure(ip):
    now = time.time()
    count, start = _attempts.get(ip, (0, now))
    if now - start > WINDOW_SECONDS:
        count, start = 0, now
    _attempts[ip] = (count + 1, start)
    if len(_attempts) > 10_000:  # Speicher-Schutz
        _attempts.clear()


def clear_failures(ip):
    _attempts.pop(ip, None)
