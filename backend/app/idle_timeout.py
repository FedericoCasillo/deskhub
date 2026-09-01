import asyncio

from app import docker_service

CHECK_INTERVAL_SECONDS = 60


async def idle_timeout_loop() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            stopped = await asyncio.to_thread(docker_service.stop_expired_desktops)
            for desktop_id in stopped:
                print(f"[idle-timeout] desktop {desktop_id} fermato automaticamente per timeout")
        except Exception as exc:
            print(f"[idle-timeout] errore nel controllo periodico: {exc}")
