import os
import re
import shutil
import socket
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import docker
from docker.errors import NotFound

from app import desktops_store
from app.config import settings
from app.schemas import DesktopInfo, DesktopListResponse, DesktopSummary, Status


# L'id del desktop e' uno slug "proprietario-nome" (es. "mario-web"), non piu'
# un contatore numerico: deve restare sicuro da usare sia come nome di
# cartella sia come suffisso di nome container (vedi generate_slug).
ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$")
SLUG_INVALID_RE = re.compile(r"[^a-z0-9]+")
TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z?$")

# Nome dell'account Linux dentro il container: sempre lo stesso per ogni
# desktop, non ha piu' senso farlo scegliere in creazione (non e' mai stato
# altro che "abc" in pratica, e non e' legato in alcun modo all'utente del
# manager che possiede il desktop).
CUSTOM_USER = "abc"

# Periodo di riferimento standard per la CPU quota di Docker (100ms): con
# max_cpus=1.5 la quota diventa 150000, cioe' 1.5 core su questo periodo.
CPU_PERIOD_MICROSECONDS = 100_000

client = docker.from_env()


def valid_id(value: str) -> bool:
    return bool(ID_RE.match(value))


def get_container_name(desktop_id: str) -> str:
    return f"{settings.container_name_prefix}{desktop_id}"


def get_config_dir(desktop_id: str) -> str:
    return f"{settings.data_dir}/{settings.config_dir_prefix}{desktop_id}"


def _mem_kwargs(max_ram_mb: int) -> dict:
    # 0 = nessun limite, sia in creazione (containers.run) che in
    # aggiornamento live (container.update): 0 e' il valore nativo
    # dell'API Docker per "Memory" quando non c'e' un tetto.
    return {"mem_limit": f"{max_ram_mb}m" if max_ram_mb > 0 else 0}


def _cpu_kwargs(max_cpus: float) -> dict:
    if max_cpus <= 0:
        return {"cpu_period": 0, "cpu_quota": 0}
    return {
        "cpu_period": CPU_PERIOD_MICROSECONDS,
        "cpu_quota": int(max_cpus * CPU_PERIOD_MICROSECONDS),
    }


def _find_container(name: str):
    matches = client.containers.list(all=True, filters={"name": f"^{name}$"})
    return matches[0] if matches else None


def container_exists(name: str) -> bool:
    return _find_container(name) is not None


def get_container_status(desktop_id: str) -> Status:
    container = _find_container(get_container_name(desktop_id))
    if container is None:
        return "ORPHAN"
    container.reload()
    return "RUNNING" if container.status == "running" else "STOPPED"


def ensure_proxy_network() -> None:
    try:
        client.networks.get(settings.proxy_network)
    except NotFound:
        client.networks.create(settings.proxy_network, driver="bridge")


def _config_ids() -> set[str]:
    ids = set()
    if os.path.isdir(settings.data_dir):
        for entry in os.scandir(settings.data_dir):
            if entry.is_dir() and entry.name.startswith(settings.config_dir_prefix):
                candidate = entry.name[len(settings.config_dir_prefix):]
                if valid_id(candidate):
                    ids.add(candidate)
    return ids


def config_dir_issue(desktop_id: str) -> Optional[str]:
    """Controlli di sanita' su una cartella di config prima di riusarla per un
    nuovo container. Non tenta alcun recupero: si limita a dire se e' sicuro
    partire o no, cosi' un problema (cartella toccata a mano, proprietario
    sbagliato, symlink fuori da data_dir) viene segnalato chiaramente invece
    di causare un fallimento silenzioso o poco chiaro dentro il container."""
    path = get_config_dir(desktop_id)

    if not os.path.isdir(path):
        return "la cartella di configurazione non esiste piu'."

    real = os.path.realpath(path)
    real_data_dir = os.path.realpath(settings.data_dir)
    if os.path.dirname(real) != real_data_dir:
        return "il percorso non e' una cartella diretta di data_dir (symlink sospetto)."

    try:
        st = os.stat(path)
    except OSError as exc:
        return f"impossibile leggere i permessi della cartella: {exc}"

    if st.st_uid != settings.expected_puid or st.st_gid != settings.expected_pgid:
        return (
            f"proprietario della cartella ({st.st_uid}:{st.st_gid}) diverso da "
            f"quello atteso dal desktop ({settings.expected_puid}:{settings.expected_pgid}); "
            "e' stata modificata da fuori al manager."
        )

    return None


def _container_ids() -> set[str]:
    ids = set()
    for container in client.containers.list(all=True):
        name = container.name
        if name.startswith(settings.container_name_prefix):
            candidate = name[len(settings.container_name_prefix):]
            if valid_id(candidate):
                ids.add(candidate)
    return ids


def collect_ids() -> list[str]:
    ids = _config_ids() | _container_ids()
    return sorted(ids)


def find_orphan_ids() -> list[str]:
    orphans = [i for i in _config_ids() if i not in _container_ids()]
    return sorted(orphans)


def orphan_details() -> list[dict]:
    return [{"id": i, "warning": config_dir_issue(i)} for i in find_orphan_ids()]


def list_running_ids() -> list[str]:
    return [i for i in collect_ids() if get_container_status(i) == "RUNNING"]


def _slugify(text: str) -> str:
    return SLUG_INVALID_RE.sub("-", text.strip().lower()).strip("-") or "x"


def generate_slug(owner: str, name: str) -> str:
    """Id del nuovo desktop: "proprietario-nome" (es. "mario-web"), deduplicato
    con un suffisso numerico se serve (es. "mario-web-2") controllando gli id
    davvero in uso (config + container), non un contatore separato."""
    base = f"{_slugify(owner)}-{_slugify(name)}"
    used = _config_ids() | _container_ids()
    if base not in used:
        return base
    suffix = 2
    while f"{base}-{suffix}" in used:
        suffix += 1
    return f"{base}-{suffix}"


def list_desktops(owner: Optional[str] = None) -> DesktopListResponse:
    desktops = []
    running = stopped = orphan = 0

    for desktop_id in collect_ids():
        desktop_owner = desktops_store.get_owner(desktop_id)
        if owner is not None and desktop_owner != owner:
            continue

        status = get_container_status(desktop_id)
        has_config = os.path.isdir(get_config_dir(desktop_id))

        if status == "RUNNING":
            running += 1
        elif status == "STOPPED":
            stopped += 1
        else:
            orphan += 1

        # Solo il limite configurato (letto dal container, istantaneo):
        # l'uso live (cpu%/RAM) e' apposta un endpoint a parte, chiamato dal
        # frontend a bassa frequenza per singolo desktop — container.stats()
        # impiega ~1-2s per container (limite del campionamento cgroup di
        # Docker stesso, verificato), inaccettabile nel poll veloce ogni 5s
        # su cui gira questa lista.
        limits = get_active_limits(desktop_id)

        desktops.append(
            DesktopSummary(
                id=desktop_id,
                name=desktops_store.get_name(desktop_id) or desktop_id,
                status=status,
                has_config=has_config,
                owner=desktop_owner,
                max_ram_mb=limits["max_ram_mb"],
                max_cpus=limits["max_cpus"],
            )
        )

    return DesktopListResponse(desktops=desktops, running=running, stopped=stopped, orphan=orphan)


def get_active_limits(desktop_id: str) -> dict:
    """Ritorna {'max_ram_mb', 'max_cpus', 'live'}. live=True se i valori
    vengono letti dal container esistente (quindi sono davvero applicati in
    questo momento, e Docker non permette di azzerarli via update — solo di
    alzarli o abbassarli, vedi apply_desktop_limits); live=False se il
    desktop e' ORPHAN e i valori vengono dalla preferenza salvata (li'
    azzerarli e' libero, contano solo alla prossima creazione)."""
    container = _find_container(get_container_name(desktop_id))
    if container is None:
        return {**desktops_store.get_limits(desktop_id), "live": False}

    container.reload()
    host_config = container.attrs.get("HostConfig", {}) or {}
    memory = host_config.get("Memory") or 0
    cpu_quota = host_config.get("CpuQuota") or 0
    cpu_period = host_config.get("CpuPeriod") or 0
    return {
        "max_ram_mb": memory // (1024 * 1024) if memory else 0,
        "max_cpus": round(cpu_quota / cpu_period, 2) if cpu_period else 0,
        "live": True,
    }


def get_desktop_info(desktop_id: str) -> DesktopInfo:
    container_name = get_container_name(desktop_id)
    config_dir = get_config_dir(desktop_id)
    container = _find_container(container_name)

    network_present = False
    if container is not None:
        container.reload()
        networks = container.attrs.get("NetworkSettings", {}).get("Networks", {}) or {}
        network_present = settings.proxy_network in networks

    limits = get_active_limits(desktop_id)

    return DesktopInfo(
        id=desktop_id,
        name=desktops_store.get_name(desktop_id) or desktop_id,
        status=get_container_status(desktop_id),
        container_name=container_name,
        config_dir=config_dir,
        config_present=os.path.isdir(config_dir),
        container_present=container is not None,
        network_present=network_present,
        owner=desktops_store.get_owner(desktop_id),
        max_ram_mb=limits["max_ram_mb"],
        max_cpus=limits["max_cpus"],
    )


def get_container_usage(desktop_id: str) -> dict:
    """Uso live (CPU%, RAM in MB) del container. Chiamata bloccante (~1-2s,
    Docker campiona due istanti di cgroup per calcolare un delta) — il
    chiamante deve eseguirla in un thread separato (asyncio.to_thread), mai
    direttamente nell'event loop."""
    container = _find_container(get_container_name(desktop_id))
    if container is None:
        return {"cpu_percent": None, "mem_used_mb": None}

    try:
        raw = container.stats(stream=False)
    except Exception:
        return {"cpu_percent": None, "mem_used_mb": None}

    cpu_stats = raw.get("cpu_stats", {}) or {}
    precpu_stats = raw.get("precpu_stats", {}) or {}
    cpu_usage = cpu_stats.get("cpu_usage", {}) or {}
    precpu_usage = precpu_stats.get("cpu_usage", {}) or {}

    cpu_delta = cpu_usage.get("total_usage", 0) - precpu_usage.get("total_usage", 0)
    system_delta = (cpu_stats.get("system_cpu_usage") or 0) - (precpu_stats.get("system_cpu_usage") or 0)
    online_cpus = cpu_stats.get("online_cpus") or len(cpu_usage.get("percpu_usage") or [1])

    cpu_percent = None
    if system_delta > 0 and cpu_delta >= 0:
        cpu_percent = round((cpu_delta / system_delta) * online_cpus * 100, 1)

    memory_stats = raw.get("memory_stats", {}) or {}
    usage = memory_stats.get("usage")
    detail = memory_stats.get("stats", {}) or {}
    # cgroup v2 riporta "inactive_file", cgroup v1 "cache": pagine di
    # file-cache che il kernel puo' riusare a piacere, sottratte anche da
    # "docker stats" per mostrare la memoria davvero occupata dal processo.
    cache = detail.get("inactive_file", detail.get("cache", 0)) or 0
    mem_used_mb = round(max(usage - cache, 0) / (1024 * 1024), 1) if usage is not None else None

    return {"cpu_percent": cpu_percent, "mem_used_mb": mem_used_mb}


def apply_desktop_limits(desktop_id: str, max_ram_mb: int, max_cpus: float) -> None:
    """Salva la preferenza (usata per gli ORPHAN, che non hanno un container
    da interrogare) e applica subito al container se esiste. max_ram_mb/
    max_cpus sono sempre > 0 (validato dallo schema della richiesta): nessuna
    risorsa illimitata, quindi qui non si azzera mai un limite gia' attivo."""
    desktops_store.set_limits(desktop_id, max_ram_mb, max_cpus)
    container = _find_container(get_container_name(desktop_id))
    if container is not None:
        container.update(**_mem_kwargs(max_ram_mb), **_cpu_kwargs(max_cpus))


def get_desktop_logs(desktop_id: str, tail: int = 200) -> str:
    container = _find_container(get_container_name(desktop_id))
    if container is None:
        return "Il container non esiste. Il desktop e' ORPHAN, nessun log Docker disponibile."

    raw = container.logs(tail=tail, stdout=True, stderr=True)
    text = raw.decode(errors="replace").strip()
    return text or "Nessun log disponibile."


def stream_logs(desktop_id: str, tail: int = 200, stop_event=None):
    container = _find_container(get_container_name(desktop_id))
    if container is None:
        yield "Il container non esiste. Il desktop e' ORPHAN, nessun log Docker disponibile.\n"
        return

    for chunk in container.logs(stream=True, follow=True, tail=tail):
        if stop_event is not None and stop_event.is_set():
            return
        yield chunk.decode(errors="replace")


def get_container_ip(desktop_id: str) -> Optional[str]:
    """IP del container sulla rete proxy, usato dal provider HTTP di Traefik
    per instradare le sessioni /session/<token>/ (routing dinamico generato
    da sessions_store, non piu' via label statiche per-desktop: niente path
    prevedibile /desk{id}/ esposto esternamente, vedi routers/sessions.py)."""
    container = _find_container(get_container_name(desktop_id))
    if container is None:
        return None
    container.reload()
    networks = container.attrs.get("NetworkSettings", {}).get("Networks", {}) or {}
    network = networks.get(settings.proxy_network) or {}
    return network.get("IPAddress") or None


def _wait_running(container, progress: Callable[[str], None], attempts: int = 15) -> bool:
    for attempt in range(attempts):
        container.reload()
        if container.status == "running":
            return True
        progress(f"Attendo avvio del container... ({attempt + 1}/{attempts})")
        time.sleep(1)
    container.reload()
    return container.status == "running"


def _wait_service_ready(container, progress: Callable[[str], None], attempts: int = 30) -> None:
    """Docker puo' segnare il container come 'running' prima ancora che il
    servizio interno (nginx + Selkies, porta 3000) sia in ascolto: aprire il
    desktop nel browser in quella finestra produce un errore del proxy
    websocket e uno schermo nero che il client non recupera sempre da solo,
    costringendo a chiudere e riaprire la scheda. Aspettando qui che la porta
    risponda prima di segnalare l'operazione come riuscita, quella finestra si
    chiude: se il servizio non risponde entro il timeout non blocchiamo
    comunque l'operazione (il container e' comunque partito), ma avvisiamo."""
    container.reload()
    networks = container.attrs.get("NetworkSettings", {}).get("Networks", {}) or {}
    network = networks.get(settings.proxy_network) or {}
    ip = network.get("IPAddress")
    if not ip:
        return

    for attempt in range(attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.connect((ip, 3000))
                return
            except OSError:
                pass
        progress(f"Attendo che il servizio desktop sia pronto... ({attempt + 1}/{attempts})")
        time.sleep(1)

    progress(
        "Il servizio desktop non ha risposto entro il timeout atteso: il "
        "container e' comunque avviato, ma la prima apertura nel browser "
        "potrebbe richiedere qualche secondo in piu' o un ricaricamento."
    )


def _pull_pinned_image(progress: Callable[[str], None]) -> bool:
    """Tenta di scaricare lo snapshot pinnato pubblicato dal progetto. Ritorna
    True se riuscito (e l'immagine e' stata taggata come settings.webtop_image),
    False se il pull fallisce per qualsiasi motivo (nessuna connessione,
    registry irraggiungibile, ecc.) cosi' il chiamante puo' passare al
    fallback di build locale senza interrompere la creazione del desktop."""
    progress(f"Scarico l'immagine pinnata {settings.webtop_pinned_image}...")
    try:
        # Niente split manuale di repository/tag qui: webtop_pinned_image puo'
        # essere sia "repo:tag" che "repo@sha256:digest" (pin per digest,
        # davvero immutabile a differenza di un tag). docker-py capisce gia'
        # da solo entrambe le forme se gli si passa la stringa cosi' com'e'.
        last_status = ""
        for chunk in client.api.pull(settings.webtop_pinned_image, stream=True, decode=True):
            if "error" in chunk:
                raise RuntimeError(chunk["error"])
            status = chunk.get("status", "")
            if status and status != last_status:
                progress(status)
                last_status = status

        image_name, _, image_tag = settings.webtop_image.partition(":")
        client.api.tag(settings.webtop_pinned_image, image_name, image_tag or "latest")
        return True
    except Exception as exc:
        progress(f"Pull dell'immagine pinnata non riuscito ({exc}), passo alla build locale...")
        return False


def _build_image(progress: Callable[[str], None]) -> None:
    progress(f"Build di {settings.webtop_image} da webtop-image/Dockerfile...")

    last_line = ""
    for chunk in client.api.build(
        path=settings.webtop_build_context,
        tag=settings.webtop_image,
        rm=True,
        decode=True,
    ):
        if "error" in chunk:
            raise RuntimeError(chunk["error"])
        line = chunk.get("stream", "").strip()
        if line and line != last_line:
            progress(line)
            last_line = line


def ensure_image(progress: Callable[[str], None]) -> None:
    if settings.webtop_source == "pull":
        # A differenza del branch "build", qui riproviamo il pull anche se
        # l'immagine locale esiste gia': altrimenti, una volta creato un tag
        # locale (anche da un pull/build precedente non aggiornato), il
        # manager lo riuserebbe per sempre senza mai allinearsi alla nuova
        # immagine pinnata pubblicata dal progetto.
        if _pull_pinned_image(progress):
            return
        try:
            client.images.get(settings.webtop_image)
            progress("Pull non riuscito: uso l'immagine locale gia' presente.")
            return
        except NotFound:
            pass
        _build_image(progress)
        return

    try:
        client.images.get(settings.webtop_image)
        return
    except NotFound:
        pass

    progress(f"Immagine {settings.webtop_image} non trovata.")
    _build_image(progress)


def create_desktop(
    desktop_id: str,
    max_ram_mb: int,
    max_cpus: float,
    progress: Callable[[str], None],
) -> dict:
    ensure_proxy_network()
    ensure_image(progress)

    container_name = get_container_name(desktop_id)
    config_dir = get_config_dir(desktop_id)

    config_preexisting = os.path.isdir(config_dir)

    if config_preexisting:
        issue = config_dir_issue(desktop_id)
        if issue:
            raise RuntimeError(
                f"Configurazione {desktop_id} non sicura da riusare: {issue} "
                "Nessun dato e' stato toccato: il container non e' stato creato."
            )
    else:
        os.makedirs(config_dir, exist_ok=True)

    progress(f"Creazione del container {container_name}...")

    try:
        container = client.containers.run(
            settings.webtop_image,
            name=container_name,
            detach=True,
            environment={
                "CUSTOM_USER": CUSTOM_USER,
                # Niente PASSWORD: l'unico effetto nell'immagine webtop e'
                # abilitare la sua Basic Auth nginx interna, ridondante con
                # l'autorizzazione gia' fatta all'emissione del token di
                # sessione (verificato nello script di init dell'immagine:
                # PASSWORD non tocca l'account Linux, solo /etc/nginx/.htpasswd).
                "PUID": "1000",
                "PGID": "1000",
                # Niente SUBFOLDER: il container serve sempre se stesso sulla
                # root (default dell'immagine quando la variabile e' assente).
                # Non ha piu' bisogno di un percorso proprio, univoco per
                # desktop: e' Traefik a distinguere i desktop per IP del
                # container nel routing dinamico per-sessione (vedi
                # routers/traefik_config.py), non piu' per path.
            },
            volumes={config_dir: {"bind": "/config", "mode": "rw"}},
            shm_size="1g",
            restart_policy={"Name": "unless-stopped"},
            network=settings.proxy_network,
            **_mem_kwargs(max_ram_mb),
            **_cpu_kwargs(max_cpus),
        )
    except Exception as exc:
        if not config_preexisting:
            shutil.rmtree(config_dir, ignore_errors=True)
        raise RuntimeError(f"Errore nella creazione del container: {exc}") from exc

    if not _wait_running(container, progress):
        logs = container.logs(tail=50).decode(errors="replace")
        container.remove(force=True)
        if not config_preexisting:
            shutil.rmtree(config_dir, ignore_errors=True)
        raise RuntimeError(f"Il container non risulta RUNNING.\n\nUltimi log:\n{logs}")

    _wait_service_ready(container, progress)

    return {"id": desktop_id}


def start_desktop(desktop_id: str, progress: Callable[[str], None]) -> dict:
    ensure_proxy_network()

    container_name = get_container_name(desktop_id)
    container = _find_container(container_name)
    if container is None:
        raise LookupError(f"Il container {container_name} non esiste.")

    config_dir = get_config_dir(desktop_id)
    if not os.path.isdir(config_dir):
        raise LookupError(f"La configurazione del desktop {desktop_id} non esiste: {config_dir}")

    container.reload()
    if container.status == "running":
        return {"already_running": True}

    issue = config_dir_issue(desktop_id)
    if issue:
        raise RuntimeError(
            f"Avvio bloccato per il desktop {desktop_id}: {issue} "
            "Nessun dato e' stato toccato: verifica manualmente la cartella prima di riprovare."
        )

    progress("Avvio del desktop...")
    container.start()

    if not _wait_running(container, progress):
        logs = container.logs(tail=50).decode(errors="replace")
        raise RuntimeError(f"Il container non risulta RUNNING.\n\nUltimi log:\n{logs}")

    _wait_service_ready(container, progress)

    return {}


def stop_desktop(desktop_id: str, progress: Callable[[str], None]) -> dict:
    container_name = get_container_name(desktop_id)
    container = _find_container(container_name)
    if container is None:
        raise LookupError(f"Il container {container_name} non esiste.")

    container.reload()
    if container.status != "running":
        raise RuntimeError(f"Il desktop {desktop_id} non e' RUNNING.")

    progress("Arresto del desktop...")
    container.stop()
    container.reload()

    if container.status == "running":
        raise RuntimeError("Il desktop non risulta STOPPED.")

    return {}


def restart_desktop(desktop_id: str, progress: Callable[[str], None]) -> dict:
    container_name = get_container_name(desktop_id)
    container = _find_container(container_name)
    if container is None:
        raise LookupError(f"Il container {container_name} non esiste.")

    container.reload()
    if container.status != "running":
        raise RuntimeError(f"Il desktop {desktop_id} non e' RUNNING.")

    progress("Riavvio del desktop...")
    container.restart()

    if not _wait_running(container, progress):
        logs = container.logs(tail=50).decode(errors="replace")
        raise RuntimeError(f"Il container non risulta RUNNING dopo il riavvio.\n\nUltimi log:\n{logs}")

    _wait_service_ready(container, progress)

    return {}


def delete_desktop(desktop_id: str, remove_config: bool, progress: Callable[[str], None]) -> dict:
    container_name = get_container_name(desktop_id)
    config_dir = get_config_dir(desktop_id)

    container = _find_container(container_name)
    has_container = container is not None
    has_config = os.path.isdir(config_dir)

    if not has_container and not has_config:
        raise LookupError(f"Il desktop {desktop_id} non esiste piu'.")

    if not has_container and has_config:
        if not remove_config:
            return {"container_removed": False, "config_removed": False}
        shutil.rmtree(config_dir)
        desktops_store.remove(desktop_id)
        return {"container_removed": False, "config_removed": True}

    progress(f"Rimozione del container {container_name}...")
    container.remove(force=True)

    if _find_container(container_name) is not None:
        raise RuntimeError(f"Il container non e' stato rimosso: {container_name}")

    if not has_config:
        desktops_store.remove(desktop_id)
        return {"container_removed": True, "config_removed": False}

    if not remove_config:
        return {"container_removed": True, "config_removed": False}

    shutil.rmtree(config_dir, ignore_errors=True)
    config_removed = not os.path.isdir(config_dir)
    if config_removed:
        desktops_store.remove(desktop_id)
    return {"container_removed": True, "config_removed": config_removed}


def _parse_docker_timestamp(value: str) -> datetime:
    match = TIMESTAMP_RE.match(value)
    if not match:
        return datetime.now(timezone.utc)
    base, frac = match.groups()
    microseconds = int((frac or "0")[:6].ljust(6, "0"))
    return datetime.fromisoformat(base).replace(tzinfo=timezone.utc, microsecond=microseconds)


def stop_expired_desktops(minutes: int) -> list[str]:
    """Ferma i desktop RUNNING da almeno `minutes` minuti. Nessun controllo di
    inattivita' reale: Selkies non espone un segnale di attivita' utente
    utilizzabile, quindi il timeout e' sul tempo di esecuzione continuo."""
    if minutes <= 0:
        return []

    threshold = timedelta(minutes=minutes)
    now = datetime.now(timezone.utc)
    stopped = []

    for desktop_id in collect_ids():
        container = _find_container(get_container_name(desktop_id))
        if container is None:
            continue

        container.reload()
        if container.status != "running":
            continue

        started = _parse_docker_timestamp(container.attrs["State"]["StartedAt"])
        if now - started >= threshold:
            container.stop()
            stopped.append(desktop_id)

    return stopped
