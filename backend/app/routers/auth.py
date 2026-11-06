import time
from threading import Lock

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from app import logins_store, users_store
from app.schemas import LoginRequest, MeOut, SetPasswordRequest
from app.security import (
    COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    get_current_user,
    hash_password,
    user_from_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Freno ai tentativi di password: dopo MAX_FAILURES errori di fila su un nome
# utente, altri tentativi su quel nome vengono rifiutati per LOCK_SECONDS
# (anche con la password giusta). Breve apposta: rallenta chi prova password
# a raffica senza poter tenere fuori a lungo l'utente vero.
MAX_FAILURES = 5
LOCK_SECONDS = 60
_failures: dict[str, tuple[int, float]] = {}
_failures_lock = Lock()


def _locked(username: str) -> bool:
    with _failures_lock:
        count, last = _failures.get(username, (0, 0.0))
        return count >= MAX_FAILURES and time.time() - last < LOCK_SECONDS


def _record_failure(username: str) -> None:
    with _failures_lock:
        count, last = _failures.get(username, (0, 0.0))
        if time.time() - last >= LOCK_SECONDS:
            count = 0
        _failures[username] = (count + 1, time.time())


@router.post("/login", response_model=MeOut)
def login(payload: LoginRequest, response: Response):
    if _locked(payload.username):
        raise HTTPException(429, "Troppi tentativi sbagliati: riprova tra un minuto.")
    record = users_store.get_user(payload.username)
    if record is None or not verify_password(payload.password, record["password_hash"]):
        _record_failure(payload.username)
        raise HTTPException(401, "Nome utente o password non validi.")
    with _failures_lock:
        _failures.pop(payload.username, None)

    token = create_session_token(payload.username)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return MeOut(username=payload.username, role=record["role"])


@router.post("/logout")
def logout(response: Response, manager_session: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    # Chiude il login lato server: il cookie, anche se copiato, non vale piu'.
    user = user_from_token(manager_session)
    if user is not None:
        logins_store.revoke(user["sid"])
    response.delete_cookie(COOKIE_NAME)
    return {}


@router.get("/me", response_model=MeOut)
def me(user: dict = Depends(get_current_user)):
    return MeOut(**user)


@router.post("/change-password")
def change_password(payload: SetPasswordRequest, user: dict = Depends(get_current_user)):
    users_store.set_password(user["username"], hash_password(payload.password))
    # Le altre sessioni dell'utente (altri dispositivi, cookie rubato) si
    # chiudono; quella da cui ha cambiato la password resta aperta.
    logins_store.revoke_user(user["username"], keep=user["sid"])
    return {}
