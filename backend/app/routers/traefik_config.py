import re
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Query, Response

from app import desktops_store, docker_service, sessions_store
from app.config import settings
from app.security import COOKIE_NAME, user_from_token

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
    # Ogni richiesta verso un desktop passa prima dal manager (forwardAuth):
    # il token nel percorso da solo non basta, serve anche il login.
    auth = "deskhub-session-auth"
    middlewares: dict = {
        auth: {
            "forwardAuth": {
                "address": f"{settings.manager_internal_url}/internal/session-auth"
                f"?secret={quote(settings.traefik_internal_secret or '', safe='')}"
            }
        }
    }
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
            "middlewares": [auth, name],
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


SESSION_PATH_RE = re.compile(r"^/session/([A-Za-z0-9_-]+)/")


@router.get("/internal/session-auth")
def session_auth(
    secret: str | None = Query(default=None),
    x_forwarded_uri: str = Header(default=""),
    cookie: str | None = Header(default=None),
):
    """forwardAuth di Traefik per /session/<token>/: passa solo se il token e'
    valido E il browser ha un login attivo dello stesso utente che ha aperto
    la sessione, con accesso ancora valido al desktop. Un link copiato o
    finito in mano ad altri non apre niente senza quel login; un logout o un
    cambio password chiudono anche l'accesso ai desktop."""
    _check_secret(secret)
    match = SESSION_PATH_RE.match(x_forwarded_uri)
    session = sessions_store.get_session(match.group(1)) if match else None
    if session is None:
        raise HTTPException(401, "Sessione non valida.")
    token = None
    for part in (cookie or "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == COOKIE_NAME:
            token = value
    user = user_from_token(token)
    if user is None or user["username"] != session["username"]:
        raise HTTPException(401, "Accesso al desktop non autorizzato.")
    if user["role"] != "admin" and desktops_store.get_owner(session["desktop_id"]) != user["username"]:
        raise HTTPException(401, "Accesso al desktop non autorizzato.")
    return Response(status_code=200)
