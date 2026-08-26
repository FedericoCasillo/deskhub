import json
import os
from threading import Lock

from app.config import settings

_LOCK = Lock()


def _path() -> str:
    return os.path.join(settings.data_dir, ".manager-desktops.json")


def _load() -> dict:
    try:
        with open(_path()) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    tmp_path = _path() + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, _path())


def get_owner(desktop_id: str) -> str | None:
    with _LOCK:
        return _load().get(desktop_id, {}).get("owner")


def set_owner(desktop_id: str, owner: str) -> None:
    with _LOCK:
        data = _load()
        entry = data.setdefault(desktop_id, {})
        entry["owner"] = owner
        _save(data)


def get_name(desktop_id: str) -> str | None:
    with _LOCK:
        return _load().get(desktop_id, {}).get("name")


def set_name(desktop_id: str, name: str) -> None:
    with _LOCK:
        data = _load()
        entry = data.setdefault(desktop_id, {})
        entry["name"] = name
        _save(data)


def get_limits(desktop_id: str) -> dict:
    with _LOCK:
        entry = _load().get(desktop_id, {})
        return {"max_ram_mb": entry.get("max_ram_mb", 0), "max_cpus": entry.get("max_cpus", 0)}


def set_limits(desktop_id: str, max_ram_mb: int, max_cpus: float) -> None:
    with _LOCK:
        data = _load()
        entry = data.setdefault(desktop_id, {})
        entry["max_ram_mb"] = max_ram_mb
        entry["max_cpus"] = max_cpus
        _save(data)


def remove(desktop_id: str) -> None:
    with _LOCK:
        data = _load()
        if data.pop(desktop_id, None) is not None:
            _save(data)
