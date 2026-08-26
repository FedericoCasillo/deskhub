import json
import os
from threading import Lock

from app.config import settings

_LOCK = Lock()


def _path() -> str:
    return os.path.join(settings.data_dir, ".manager-users.json")


def _load() -> dict:
    try:
        with open(_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    # Scrittura su file temporaneo + rename atomico: evita un users.json
    # a meta' scritto se il processo muore proprio durante il salvataggio.
    tmp_path = _path() + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, _path())


def list_users() -> dict:
    with _LOCK:
        return _load()


def get_user(username: str) -> dict | None:
    with _LOCK:
        return _load().get(username)


def create_user(username: str, password_hash: str, role: str) -> None:
    with _LOCK:
        data = _load()
        if username in data:
            raise ValueError(f"L'utente '{username}' esiste gia'.")
        data[username] = {"password_hash": password_hash, "role": role}
        _save(data)


def set_password(username: str, password_hash: str) -> None:
    with _LOCK:
        data = _load()
        if username not in data:
            raise KeyError(username)
        data[username]["password_hash"] = password_hash
        _save(data)


def delete_user(username: str) -> None:
    with _LOCK:
        data = _load()
        if username not in data:
            raise KeyError(username)
        del data[username]
        _save(data)


def count_admins() -> int:
    with _LOCK:
        return sum(1 for u in _load().values() if u.get("role") == "admin")


def ensure_bootstrap_admin(username: str, password_hash: str) -> bool:
    """Crea l'admin iniziale solo se non esiste ancora nessun utente. Ritorna
    True se l'ha creato, False se ha trovato utenti gia' presenti (percorso
    normale ai riavvii successivi al primo)."""
    with _LOCK:
        data = _load()
        if data:
            return False
        data[username] = {"password_hash": password_hash, "role": "admin"}
        _save(data)
        return True
