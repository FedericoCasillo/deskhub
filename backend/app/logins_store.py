import json
import os
import secrets
import time
from threading import Lock

from app.config import settings

# Login attivi sul manager, lato server: il cookie porta solo un id casuale
# (firmato), valido finche' e' qui dentro. Cosi' "Esci" chiude davvero la
# sessione (un cookie copiato prima non vale piu'), e un cambio o reset di
# password chiude le altre sessioni dell'utente. Su file, non in memoria: un
# riavvio del manager non deve disconnettere tutti.

LOGIN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 giorni, come la durata del cookie

_LOCK = Lock()


def _path() -> str:
    return os.path.join(settings.data_dir, ".manager-logins.json")


def _load() -> dict:
    try:
        with open(_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    tmp_path = _path() + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, _path())


def _purge(data: dict) -> dict:
    now = time.time()
    return {sid: s for sid, s in data.items() if s.get("expires_at", 0) > now}


def create(username: str) -> str:
    sid = secrets.token_urlsafe(24)
    with _LOCK:
        data = _purge(_load())
        data[sid] = {"username": username, "expires_at": time.time() + LOGIN_TTL_SECONDS}
        _save(data)
    return sid


def get_username(sid: str) -> str | None:
    with _LOCK:
        session = _load().get(sid)
    if session is None or session.get("expires_at", 0) <= time.time():
        return None
    return session.get("username")


def revoke(sid: str) -> None:
    with _LOCK:
        data = _load()
        if data.pop(sid, None) is not None:
            _save(data)


def revoke_user(username: str, keep: str | None = None) -> None:
    """Chiude tutti i login dell'utente, tranne eventualmente quello in uso."""
    with _LOCK:
        data = _purge(_load())
        data = {sid: s for sid, s in data.items() if s.get("username") != username or sid == keep}
        _save(data)
