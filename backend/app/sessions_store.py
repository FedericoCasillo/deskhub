import secrets
import time
from threading import Lock

# Token di sessione per l'apertura dei desktop (stile Kasm): niente path
# statico e prevedibile (/desk{id}/), un token opaco generato al click su
# "Apri", legato a un desktop preciso, con scadenza. Volutamente in memoria
# (non su file): sono pensati per durare quanto una sessione d'uso, non
# sopravvivere a un riavvio del manager, e un'eventuale perdita al riavvio
# e' innocua (l'utente riclicca "Apri" e ne ottiene uno nuovo).

SESSION_TTL_SECONDS = 12 * 60 * 60  # 12 ore

_LOCK = Lock()
_SESSIONS: dict[str, dict] = {}


def create_session(desktop_id: str, username: str) -> str:
    token = secrets.token_urlsafe(24)
    with _LOCK:
        _SESSIONS[token] = {
            "desktop_id": desktop_id,
            "username": username,
            "expires_at": time.time() + SESSION_TTL_SECONDS,
        }
    return token


def get_session(token: str) -> dict | None:
    with _LOCK:
        session = _SESSIONS.get(token)
        if session is None:
            return None
        if session["expires_at"] < time.time():
            del _SESSIONS[token]
            return None
        return session


def revoke_for_desktop(desktop_id: str) -> None:
    with _LOCK:
        for token in [t for t, s in _SESSIONS.items() if s["desktop_id"] == desktop_id]:
            del _SESSIONS[token]


def all_active() -> dict:
    """Ritorna le sessioni valide, ripulendo di passaggio quelle scadute
    (nessun task periodico dedicato: con volumi personali/piccoli non serve,
    la pulizia lazy ad ogni lettura basta)."""
    with _LOCK:
        now = time.time()
        for token in [t for t, s in _SESSIONS.items() if s["expires_at"] < now]:
            del _SESSIONS[token]
        return dict(_SESSIONS)
