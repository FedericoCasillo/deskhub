import os
import secrets

import bcrypt
from fastapi import Cookie, Depends, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.websockets import WebSocket

from app import logins_store, users_store
from app.config import settings

COOKIE_NAME = "manager_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 giorni


def _secret_path() -> str:
    return os.path.join(settings.data_dir, ".manager-session-secret")


def _load_or_create_secret() -> str:
    # Generato una volta sola e persistito: se cambiasse ad ogni riavvio,
    # ogni redeploy del manager disconnetterebbe tutti gli utenti.
    path = _secret_path()
    try:
        with open(path) as f:
            secret = f.read().strip()
            if secret:
                return secret
    except FileNotFoundError:
        pass

    secret = secrets.token_hex(32)
    with open(path, "w") as f:
        f.write(secret)
    os.chmod(path, 0o600)
    return secret


_serializer = URLSafeTimedSerializer(_load_or_create_secret(), salt="manager-session")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        # Hash malformato: tratta come credenziale non valida invece di 500.
        return False


def create_session_token(username: str) -> str:
    # Nel cookie solo l'id del login (vedi logins_store): vale finche' il
    # login esiste lato server, non per il solo fatto di essere firmato.
    return _serializer.dumps({"sid": logins_store.create(username)})


def read_session_token(token: str) -> tuple[str, str] | None:
    """(utente, id del login) se il cookie e' valido e il login e' ancora attivo."""
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    sid = data.get("sid") if isinstance(data, dict) else None
    if not sid:
        return None
    username = logins_store.get_username(sid)
    return (username, sid) if username else None


def user_from_token(token: str | None) -> dict | None:
    if token is None:
        return None
    found = read_session_token(token)
    if found is None:
        return None
    username, sid = found
    record = users_store.get_user(username)
    if record is None:
        return None
    return {"username": username, "role": record["role"], "sid": sid}


def get_current_user(manager_session: str | None = Cookie(default=None, alias=COOKIE_NAME)) -> dict:
    user = user_from_token(manager_session)
    if user is None:
        raise HTTPException(401, "Non autenticato.")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Richiesti permessi da amministratore.")
    return user


def get_ws_user(websocket: WebSocket) -> dict | None:
    return user_from_token(websocket.cookies.get(COOKIE_NAME))
