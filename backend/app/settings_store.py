import json
import os
from threading import Lock

from app.config import settings

_LOCK = Lock()
_DEFAULTS = {"idle_timeout_minutes": 0, "default_max_ram_mb": 1024, "default_max_cpus": 1.0}


def _path() -> str:
    return os.path.join(settings.data_dir, ".manager-settings.json")


def get() -> dict:
    with _LOCK:
        try:
            with open(_path()) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return dict(_DEFAULTS)
    return {**_DEFAULTS, **data}


def update(idle_timeout_minutes: int, default_max_ram_mb: int, default_max_cpus: float) -> dict:
    data = {
        "idle_timeout_minutes": idle_timeout_minutes,
        "default_max_ram_mb": default_max_ram_mb,
        "default_max_cpus": default_max_cpus,
    }
    with _LOCK:
        with open(_path(), "w") as f:
            json.dump(data, f)
    return data
