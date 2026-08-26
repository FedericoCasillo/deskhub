from fastapi import APIRouter, Depends, HTTPException

from app import users_store
from app.schemas import CreateUserRequest, SetPasswordRequest, UserOut
from app.security import hash_password, require_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(admin: dict = Depends(require_admin)):
    return [UserOut(username=username, role=record["role"]) for username, record in users_store.list_users().items()]


@router.post("", response_model=UserOut)
def create_user(payload: CreateUserRequest, admin: dict = Depends(require_admin)):
    try:
        users_store.create_user(payload.username, hash_password(payload.password), payload.role)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return UserOut(username=payload.username, role=payload.role)


@router.put("/{username}/password", response_model=UserOut)
def set_password(username: str, payload: SetPasswordRequest, admin: dict = Depends(require_admin)):
    record = users_store.get_user(username)
    if record is None:
        raise HTTPException(404, "Utente non trovato.")
    users_store.set_password(username, hash_password(payload.password))
    return UserOut(username=username, role=record["role"])


@router.delete("/{username}")
def delete_user(username: str, admin: dict = Depends(require_admin)):
    record = users_store.get_user(username)
    if record is None:
        raise HTTPException(404, "Utente non trovato.")

    if username == admin["username"]:
        raise HTTPException(400, "Non puoi eliminare l'utente con cui hai fatto login.")

    if record["role"] == "admin" and users_store.count_admins() <= 1:
        raise HTTPException(400, "Non puoi eliminare l'ultimo amministratore rimasto.")

    users_store.delete_user(username)
    return {}
