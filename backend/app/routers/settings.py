from fastapi import APIRouter, Depends

from app import settings_store
from app.schemas import SettingsPayload
from app.security import require_admin

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsPayload)
def get_settings(admin: dict = Depends(require_admin)):
    return settings_store.get()


@router.put("", response_model=SettingsPayload)
def update_settings(payload: SettingsPayload, admin: dict = Depends(require_admin)):
    return settings_store.update(payload.idle_timeout_minutes, payload.default_max_ram_mb, payload.default_max_cpus)
