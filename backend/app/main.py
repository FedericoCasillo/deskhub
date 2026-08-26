import asyncio
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import users_store
from app.config import settings
from app.idle_timeout import idle_timeout_loop
from app.routers import auth, desktops, settings as settings_router, traefik_config, users, ws
from app.security import hash_password

if not os.path.isdir(settings.data_dir):
    sys.exit(
        f"DATA_DIR non valido: '{settings.data_dir}' non esiste dentro il container.\n"
        f"Controlla che DATA_DIR in .env corrisponda a una cartella reale sull'host "
        f"(quella dedicata alle cartelle di config dei desktop) e che il volume in "
        f"compose.yml monti lo STESSO path, non un path diverso. Nota: se il path e' "
        f"sbagliato, Docker crea comunque una cartella vuota per il bind mount invece "
        f"di fallire da solo — questo controllo esiste apposta per intercettarlo."
    )

if not os.access(settings.data_dir, os.W_OK):
    sys.exit(
        f"DATA_DIR non scrivibile: '{settings.data_dir}'. "
        f"Il manager deve poter creare/rimuovere le cartelle di config dei desktop."
    )

dockerfile_path = os.path.join(settings.webtop_build_context, "Dockerfile")
if not os.path.isfile(dockerfile_path):
    sys.exit(
        f"Immagine del manager corrotta o incompleta: '{dockerfile_path}' non trovato. "
        f"webtop-image/ dovrebbe essere sempre presente (viene copiato nell'immagine "
        f"in fase di build, vedi Dockerfile) — ricostruisci l'immagine del manager."
    )

app = FastAPI(title="DeskHub")


@app.exception_handler(LookupError)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.on_event("startup")
async def bootstrap_admin() -> None:
    if users_store.list_users():
        return

    if not (settings.manager_initial_admin_user and settings.manager_initial_admin_password):
        print(
            "[bootstrap] ATTENZIONE: nessun utente esiste e "
            "MANAGER_INITIAL_ADMIN_USER/MANAGER_INITIAL_ADMIN_PASSWORD non sono "
            "impostate: nessuno potra' accedere alla webapp finche' non vengono "
            "impostate in .env e il manager riavviato."
        )
        return

    users_store.ensure_bootstrap_admin(
        settings.manager_initial_admin_user,
        hash_password(settings.manager_initial_admin_password),
    )
    print(f"[bootstrap] creato utente amministratore iniziale '{settings.manager_initial_admin_user}'.")


@app.on_event("startup")
async def start_background_tasks() -> None:
    # Riferimento tenuto su app.state: un task creato senza riferimenti forti
    # puo' essere raccolto dal garbage collector prima di completare.
    app.state.idle_timeout_task = asyncio.create_task(idle_timeout_loop())


app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(desktops.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(traefik_config.router)
app.include_router(ws.router)

static_dir = Path(settings.static_dir)
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
