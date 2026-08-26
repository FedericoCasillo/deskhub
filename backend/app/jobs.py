import asyncio
import uuid
from typing import Any, Callable, Optional


JOB_RETENTION_SECONDS = 300


class Job:
    """Il job vive indipendentemente da qualunque connessione websocket che
    lo osserva: 'history' conserva tutti i messaggi emessi finora, cosi' un
    client che si connette (o riconnette dopo una caduta di rete) li vede
    tutti subito invece di perdere quelli emessi mentre non era in ascolto,
    e i nuovi arrivano via una coda dedicata per ogni sottoscrittore."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.history: list[dict] = []
        self.done = False
        self._loop = loop
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        for message in self.history:
            queue.put_nowait(message)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def progress(self, message: str) -> None:
        self._emit({"status": "progress", "message": message})

    def _emit(self, payload: dict) -> None:
        def apply() -> None:
            self.history.append(payload)
            if payload["status"] in ("success", "error"):
                self.done = True
            for queue in self._subscribers:
                queue.put_nowait(payload)

        self._loop.call_soon_threadsafe(apply)


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._tasks: set[asyncio.Task] = set()

    def start(self, func: Callable[[Job], Any]) -> str:
        job_id = uuid.uuid4().hex
        loop = asyncio.get_running_loop()
        job = Job(loop)
        self._jobs[job_id] = job

        async def runner() -> None:
            try:
                result = await asyncio.to_thread(func, job)
                job._emit({"status": "success", "message": "Operazione completata.", "result": result})
            except Exception as exc:
                job._emit({"status": "error", "message": str(exc)})
            # Il job resta disponibile ancora un po' dopo aver finito, cosi'
            # un client riconnesso in ritardo (o che si connette solo dopo che
            # l'operazione e' gia' completata) trova comunque l'esito finale
            # invece di un generico "Job non trovato".
            loop.call_later(JOB_RETENTION_SECONDS, self._jobs.pop, job_id, None)

        # Un task creato senza tenerne un riferimento puo' essere raccolto dal
        # garbage collector prima di completare (asyncio tiene solo riferimenti
        # deboli): lo teniamo in _tasks finche' non finisce.
        task = asyncio.create_task(runner())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job_id

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)


job_manager = JobManager()
