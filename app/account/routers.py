from fastapi.responses import JSONResponse
from fastapi import APIRouter, HTTPException, status, Depends, Request


from app.account.models import User
from app.db.config import SessionDep
from app.account.deps import get_current_user, require_admin
from app.account.schemas import (
    PasswordChangeRequest,
    PasswordResetEmailRequest,
    PasswordResetRequest,
    UserCreate,
    UserOut,
    UserLogin,
)
from app.account.services import (
    change_password,
    create_user,
    authenticate_user,
    email_verification_send,
    password_reset_email_send,
    verify_email_token,
    verify_password_reset_token,
)
from app.account.utils import create_tokens, revoke_refresh_token, verify_refresh_token
from decouple import config

DEBUG = config("DEBUG")

router = APIRouter()


@router.post("/register", response_model=UserOut)
async def register(session: SessionDep, user: UserCreate):
    """Register a new user."""
    return await create_user(session, user)


@router.post("/login")
async def login(session: SessionDep, user_login: UserLogin):
    """Authenticate user and return access and refresh tokens."""
    user = await authenticate_user(session, user_login)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    tokens = await create_tokens(session, user)
    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=False if DEBUG else True,  # Development: False, Production: True
        samesite="lax",
        max_age=60 * 60 * 24 * 1,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=False if DEBUG else True,  # Development: False, Production: True
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return user


@router.post("/refresh")
async def refresh_token(session: SessionDep, request: Request):
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    user = await verify_refresh_token(session, refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    tokens = await create_tokens(session, user)
    response = JSONResponse(content={"message": "Token refreshed"})
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 1,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return response


@router.post("/send-verification-email")
async def send_verification_email(user: User = Depends(get_current_user)):
    return await email_verification_send(user)


@router.get("/verify-email")
async def verify_email(session: SessionDep, token: str):
    return await verify_email_token(session, token)


@router.post("/change-password")
async def password_change(
    session: SessionDep,
    data: PasswordChangeRequest,
    user: User = Depends(get_current_user),
):
    await change_password(session, user, data)
    return {"msg": "Password changed successfully"}


@router.post("/send-password-reset-email")
async def send_password_reset_email(
    session: SessionDep, data: PasswordResetEmailRequest
):
    return await password_reset_email_send(session, data)


@router.post("/verify-password-reset-token")
async def verify_password_reset_email(session: SessionDep, data: PasswordResetRequest):
    return await verify_password_reset_token(session, data)


@router.get("/admin")
async def admin(user: User = Depends(require_admin)):
    return {"msg": f"Welcome Admin {user.email}"}


@router.post("/logout")
async def logout(
    session: SessionDep, request: Request, user: User = Depends(get_current_user)
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await revoke_refresh_token(session, refresh_token)
    response = JSONResponse(content={"detail": "Logged out"})
    response.delete_cookie("refresh_token")
    response.delete_cookie("access_token")
    return response
