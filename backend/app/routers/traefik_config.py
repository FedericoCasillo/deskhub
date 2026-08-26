import secrets

from fastapi import APIRouter, HTTPException, Query

from app import docker_service, sessions_store
from app.config import settings

router = APIRouter()


def _check_secret(secret: str | None) -> None:
    # Questo endpoint ritorna, in chiaro, la mappa completa token->desktop
    # attualmente valida: deve restare irraggiungibile da chiunque non sia
    # Traefik stesso (nessun router pubblico lo espone, ma la difesa vera e'
    # questo segreto condiviso solo con il provider HTTP di Traefik, passato
    # come query string nell'endpoint configurato in deploy/traefik/compose.yml).
    if not settings.traefik_internal_secret or not secret:
        raise HTTPException(401, "Non autorizzato.")
    if not secrets.compare_digest(secret, settings.traefik_internal_secret):
        raise HTTPException(401, "Non autorizzato.")


@router.get("/internal/traefik-config")
def traefik_dynamic_config(secret: str | None = Query(default=None)):
    """Configurazione dinamica per il provider HTTP di Traefik: una route
    per ogni sessione /session/<token>/ ancora valida, che toglie il prefisso
    di sessione e instrada il resto del path al container sulla sua radice
    (ogni container serve se stesso su /, non ha un percorso proprio: e' il
    routing dinamico a distinguerli per IP, non piu' per path). Nessun path
    prevedibile: chi non ha un token valido (emesso da
    POST /api/desktops/{id}/session dopo verifica di sessione+ownership) non
    ha alcuna route disponibile per raggiungere quel desktop."""
    _check_secret(secret)

    routers: dict = {}
    middlewares: dict = {}
    services: dict = {}

    for token, session in sessions_store.all_active().items():
        desktop_id = session["desktop_id"]
        ip = docker_service.get_container_ip(desktop_id)
        if ip is None:
            continue

        name = f"session-{token}"
        middlewares[name] = {"stripPrefix": {"prefixes": [f"/session/{token}"]}}
        routers[name] = {
            "rule": f"PathPrefix(`/session/{token}/`)",
            "entryPoints": ["websecure"],
            "tls": {},
            "middlewares": [name],
            "service": name,
        }
        services[name] = {"loadBalancer": {"servers": [{"url": f"http://{ip}:3000"}]}}

    # Traefik rifiuta sia una mappa vuota-ma-presente ("middlewares cannot
    # be a standalone element") sia un "http" vuoto-ma-presente ("http
    # cannot be a standalone element") — verificato in pratica contro
    # Traefik reale. Quando non c'e' nessuna sessione attiva, la risposta
    # valida e' un oggetto completamente vuoto, non {"http": {}}.
    if not routers:
        return {}

    return {
        "http": {
            "routers": routers,
            "middlewares": middlewares,
            "services": services,
        }
    }
