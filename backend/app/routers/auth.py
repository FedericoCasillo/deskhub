from fastapi import APIRouter, Depends, HTTPException, Response

from app import users_store
from app.schemas import LoginRequest, MeOut, SetPasswordRequest
from app.security import (
    COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=MeOut)
def login(payload: LoginRequest, response: Response):
    record = users_store.get_user(payload.username)
    if record is None or not verify_password(payload.password, record["password_hash"]):
        raise HTTPException(401, "Nome utente o password non validi.")

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
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {}


@router.get("/me", response_model=MeOut)
def me(user: dict = Depends(get_current_user)):
    return MeOut(**user)


@router.post("/change-password")
def change_password(payload: SetPasswordRequest, user: dict = Depends(get_current_user)):
    users_store.set_password(user["username"], hash_password(payload.password))
    return {}
