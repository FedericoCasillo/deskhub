import asyncio

from app import docker_service, settings_store

CHECK_INTERVAL_SECONDS = 60


async def idle_timeout_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            minutes = settings_store.get()["idle_timeout_minutes"]
            stopped = await asyncio.to_thread(docker_service.stop_expired_desktops, minutes)
            for desktop_id in stopped:
                print(f"[idle-timeout] desktop {desktop_id} fermato automaticamente dopo {minutes} minuti")
        except Exception as exc:
            print(f"[idle-timeout] errore nel controllo periodico: {exc}")
