import asyncio
import threading

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app import docker_service
from app.jobs import job_manager
from app.security import get_ws_user

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()

    job = job_manager.get(job_id)
    if job is None:
        await websocket.send_json({"status": "error", "message": "Job non trovato."})
        await websocket.close()
        return

    queue = job.subscribe()
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
            if message["status"] in ("success", "error"):
                break
    except WebSocketDisconnect:
        pass
    else:
        # Starlette non chiude da sola la connessione quando l'handler
        # ritorna: senza close esplicito il socket resta aperto ma muto
        # invece di segnalare al client che non arriverà altro.
        await websocket.close()
    finally:
        # Il job stesso NON viene rimosso qui: continua a girare (e a
        # bufferizzare i suoi messaggi) indipendentemente da questa singola
        # connessione, cosi' un client che si riconnette dopo una caduta di
        # rete puo' ancora recuperare l'esito invece di trovare un job gia'
        # sparito solo perche' la connessione precedente si e' chiusa.
        job.unsubscribe(queue)


@router.websocket("/ws/desktops/{desktop_id}/logs")
async def desktop_logs(websocket: WebSocket, desktop_id: str):
    await websocket.accept()

    user = get_ws_user(websocket)
    if user is None or user["role"] != "admin":
        await websocket.close(code=1008)
        return

    if not docker_service.valid_id(desktop_id):
        await websocket.close(code=1008)
        return

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    stop_event = threading.Event()

    def follow() -> None:
        try:
            for chunk in docker_service.stream_logs(desktop_id, stop_event=stop_event):
                loop.call_soon_threadsafe(queue.put_nowait, chunk)
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, f"[errore log: {exc}]\n")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=follow, daemon=True).start()

    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass
    else:
        # Vedi commento analogo in job_progress: senza questo, quando lo
        # stream Docker finisce da solo (es. container fermo) il socket
        # resta aperto ma muto invece di chiudersi, e il client non ha modo
        # di accorgersi che non arriverà altro finché non lo fa ripartire.
        await websocket.close()
    finally:
        # Senza segnalare lo stop, il thread in follow() resta bloccato in
        # ascolto sullo stream Docker anche dopo che il client si e'
        # disconnesso: ad ogni riconnessione (frequente, dato il retry
        # automatico del frontend) se ne accumulerebbe uno nuovo mai chiuso.
        stop_event.set()
