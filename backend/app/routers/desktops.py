import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app import desktops_store, docker_service, sessions_store, settings_store, users_store
from app.jobs import job_manager
from app.schemas import (
    CreateDesktopRequest,
    DeleteDesktopRequest,
    DesktopInfo,
    DesktopLimitsPayload,
    DesktopListResponse,
    DesktopSessionOut,
    DesktopUsage,
    FleetUsage,
    JobStarted,
    OrphanEntry,
)
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/desktops", tags=["desktops"])


def _validate(desktop_id: str) -> None:
    if not docker_service.valid_id(desktop_id):
        raise HTTPException(400, "ID non valido.")


def _require_access(desktop_id: str, user: dict) -> None:
    """Un admin puo' operare su ogni desktop; un utente normale solo sui
    propri (start/stop/restart, mai creazione/eliminazione/log/info)."""
    if user["role"] == "admin":
        return
    if desktops_store.get_owner(desktop_id) != user["username"]:
        raise HTTPException(403, "Non hai accesso a questo desktop.")


@router.get("", response_model=DesktopListResponse)
def list_desktops(user: dict = Depends(get_current_user)):
    owner = None if user["role"] == "admin" else user["username"]
    return docker_service.list_desktops(owner=owner)


@router.get("/orphans", response_model=list[OrphanEntry])
def orphan_ids(admin: dict = Depends(require_admin)):
    return docker_service.orphan_details()


@router.get("/usage", response_model=FleetUsage)
async def fleet_usage(admin: dict = Depends(require_admin)):
    """Uso aggregato di tutti i desktop RUNNING insieme (di ogni utente), per
    l'indicatore complessivo dell'admin oltre a quello per singolo desktop."""
    running_ids = docker_service.list_running_ids()
    if not running_ids:
        return FleetUsage()

    usages = await asyncio.gather(
        *(asyncio.to_thread(docker_service.get_container_usage, i) for i in running_ids)
    )
    limits = [docker_service.get_active_limits(i) for i in running_ids]

    # Un desktop entra nel numeratore (uso) E nel denominatore (tetto) solo
    # se per QUEL desktop e' arrivato in questo giro un campione valido:
    # sommare comunque il suo tetto quando l'uso non e' disponibile (es.
    # container appena avviato, primo campione ancora a zero) produce una
    # frazione incoerente — "100% / 3" quando in realta' solo un desktop da
    # 1 core ha davvero contribuito al numeratore.
    cpu_percent_sum = 0.0
    cpu_cap_sum = 0.0
    has_cpu_sample = False
    mem_used_sum = 0.0
    mem_cap_sum = 0
    has_mem_sample = False

    for usage, limit in zip(usages, limits):
        if usage["cpu_percent"] is not None:
            cpu_percent_sum += usage["cpu_percent"]
            cpu_cap_sum += limit["max_cpus"]
            has_cpu_sample = True
        if usage["mem_used_mb"] is not None:
            mem_used_sum += usage["mem_used_mb"]
            mem_cap_sum += limit["max_ram_mb"]
            has_mem_sample = True

    per_desktop = {
        desktop_id: DesktopUsage(**usage) for desktop_id, usage in zip(running_ids, usages)
    }

    return FleetUsage(
        cpu_percent=round(cpu_percent_sum, 1) if has_cpu_sample else None,
        mem_used_mb=round(mem_used_sum, 1) if has_mem_sample else None,
        max_ram_mb=int(mem_cap_sum),
        max_cpus=round(cpu_cap_sum, 2),
        running_count=len(running_ids),
        per_desktop=per_desktop,
    )


@router.get("/{desktop_id}", response_model=DesktopInfo)
def desktop_info(desktop_id: str, admin: dict = Depends(require_admin)):
    _validate(desktop_id)
    return docker_service.get_desktop_info(desktop_id)


@router.get("/{desktop_id}/usage", response_model=DesktopUsage)
async def desktop_usage(desktop_id: str, user: dict = Depends(get_current_user)):
    _validate(desktop_id)
    _require_access(desktop_id, user)
    usage = await asyncio.to_thread(docker_service.get_container_usage, desktop_id)
    return DesktopUsage(**usage)


@router.post("/{desktop_id}/session", response_model=DesktopSessionOut)
def create_desktop_session(desktop_id: str, user: dict = Depends(get_current_user)):
    """Genera un token di sessione opaco e a scadenza per aprire il desktop
    (stile Kasm): l'url pubblico e' /session/<token>/, mai /desk{id}/ — vedi
    routers/traefik_config.py per come Traefik lo instrada dinamicamente."""
    _validate(desktop_id)
    _require_access(desktop_id, user)
    if docker_service.get_container_status(desktop_id) != "RUNNING":
        raise HTTPException(400, "Il desktop deve essere in esecuzione per aprirlo.")
    token = sessions_store.create_session(desktop_id, user["username"])
    return DesktopSessionOut(url=f"/session/{token}/")


@router.get("/{desktop_id}/logs")
def desktop_logs(desktop_id: str, tail: int = 200, admin: dict = Depends(require_admin)):
    _validate(desktop_id)
    return {"logs": docker_service.get_desktop_logs(desktop_id, tail)}


@router.post("", response_model=JobStarted)
async def create_desktop(payload: CreateDesktopRequest, admin: dict = Depends(require_admin)):
    if users_store.get_user(payload.owner) is None:
        raise HTTPException(400, "L'utente proprietario indicato non esiste.")

    if payload.reuse_id is not None:
        _validate(payload.reuse_id)
        if payload.reuse_id not in docker_service.find_orphan_ids():
            raise HTTPException(400, "L'ID selezionato non e' disponibile per il riutilizzo.")
        target_id = payload.reuse_id
        # Il nome resta quello del desktop originale a cui appartiene questa
        # cartella di configurazione: non e' rinominabile in fase di
        # ricreazione, altrimenti si perderebbe il legame con l'identita'
        # gia' associata a quei dati. Fallback al nome inviato solo per il
        # caso limite di una cartella orfana mai tracciata nello store.
        name = desktops_store.get_name(target_id) or payload.name
    else:
        target_id = docker_service.generate_slug(payload.owner, payload.name)
        name = payload.name

    defaults = settings_store.get()
    max_ram_mb = payload.max_ram_mb if payload.max_ram_mb is not None else defaults["default_max_ram_mb"]
    max_cpus = payload.max_cpus if payload.max_cpus is not None else defaults["default_max_cpus"]
    idle_timeout_minutes = (
        payload.idle_timeout_minutes if payload.idle_timeout_minutes is not None else defaults["idle_timeout_minutes"]
    )

    desktops_store.set_owner(target_id, payload.owner)
    desktops_store.set_name(target_id, name)
    desktops_store.set_limits(target_id, max_ram_mb, max_cpus, idle_timeout_minutes)

    job_id = job_manager.start(
        lambda job: docker_service.create_desktop(target_id, max_ram_mb, max_cpus, job.progress)
    )
    return JobStarted(job_id=job_id)


@router.put("/{desktop_id}/limits", response_model=DesktopInfo)
def set_desktop_limits(desktop_id: str, payload: DesktopLimitsPayload, admin: dict = Depends(require_admin)):
    _validate(desktop_id)
    if desktop_id not in docker_service.collect_ids():
        raise HTTPException(404, "Desktop non trovato.")

    docker_service.apply_desktop_limits(
        desktop_id, payload.max_ram_mb, payload.max_cpus, payload.idle_timeout_minutes
    )
    return docker_service.get_desktop_info(desktop_id)


@router.post("/{desktop_id}/start", response_model=JobStarted)
async def start_desktop(desktop_id: str, user: dict = Depends(get_current_user)):
    _validate(desktop_id)
    _require_access(desktop_id, user)
    job_id = job_manager.start(lambda job: docker_service.start_desktop(desktop_id, job.progress))
    return JobStarted(job_id=job_id)


@router.post("/{desktop_id}/stop", response_model=JobStarted)
async def stop_desktop(desktop_id: str, user: dict = Depends(get_current_user)):
    _validate(desktop_id)
    _require_access(desktop_id, user)
    sessions_store.revoke_for_desktop(desktop_id)
    job_id = job_manager.start(lambda job: docker_service.stop_desktop(desktop_id, job.progress))
    return JobStarted(job_id=job_id)


@router.post("/{desktop_id}/restart", response_model=JobStarted)
async def restart_desktop(desktop_id: str, user: dict = Depends(get_current_user)):
    _validate(desktop_id)
    _require_access(desktop_id, user)
    # L'IP interno del container puo' cambiare al riavvio: le sessioni gia'
    # aperte puntano (nel routing dinamico di Traefik) al vecchio IP, meglio
    # invalidarle e far riaprire un "Apri" nuovo dopo il riavvio.
    sessions_store.revoke_for_desktop(desktop_id)
    job_id = job_manager.start(lambda job: docker_service.restart_desktop(desktop_id, job.progress))
    return JobStarted(job_id=job_id)


@router.delete("/{desktop_id}", response_model=JobStarted)
async def delete_desktop(desktop_id: str, payload: DeleteDesktopRequest, admin: dict = Depends(require_admin)):
    _validate(desktop_id)
    sessions_store.revoke_for_desktop(desktop_id)
    job_id = job_manager.start(
        lambda job: docker_service.delete_desktop(desktop_id, payload.remove_config, job.progress)
    )
    return JobStarted(job_id=job_id)
