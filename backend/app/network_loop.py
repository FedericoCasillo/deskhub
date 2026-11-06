import asyncio

from app import docker_service

# Breve: un Traefik ricreato (docker compose up del reverse proxy) perde i
# collegamenti alle reti dei desktop, e finche' non li riprende le sessioni
# aperte non arrivano al desktop.
CHECK_INTERVAL_SECONDS = 10


async def network_reconcile_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(docker_service.reconcile_networks)
        except Exception as exc:
            print(f"[rete] errore nel controllo periodico delle reti dei desktop: {exc}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
