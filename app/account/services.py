from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks, HTTPException, status

from app.account.models import User
from app.account.schemas import (
    PasswordChangeRequest,
    PasswordResetEmailRequest,
    PasswordResetRequest,
    UserCreate,
    UserLogin,
)
from app.account.utils import (
    create_email_verification_token,
    create_password_reset_token,
    get_user_by_email,
    hash_password,
    verify_email_token_and_get_user_id,
    verify_password,
    send_email,
)

from decouple import config

FRONTEND_URL = config("FRONTEND_URL")


async def create_user(session: AsyncSession, user: UserCreate):
    """Create a new user in the database."""
    stmt = select(User).where(User.email == user.email)
    result = await session.scalars(stmt)
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


async def authenticate_user(session: AsyncSession, user_login: UserLogin):
    """Authenticate a user and return the user object if successful."""
    stmt = select(User).where(User.email == user_login.email)
    result = await session.scalars(stmt)
    user = result.first()
    if not user or not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return user


async def email_verification_send(
    user: User, background_tasks: BackgroundTasks
):  # bg task
    """Generate an email verification token for the user."""
    token = create_email_verification_token(user.id)
    link = f"{FRONTEND_URL}/user/verify-email?token={token}"
    print(f"Email verification link for {user.email}: {link}")
    background_tasks.add_task(
        send_email,
        subject="Verify your email",
        recipient=[user.email],
        body=f"Please click the following link to verify your email: {link}",
    )
    return {"msg": "Verification email sent (check console for link)"}


async def verify_email_token(session: AsyncSession, token: str):
    """Verify the email verification token and activate the user's account."""
    user_id = verify_email_token_and_get_user_id(token, "verify_email")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    stmt = select(User).where(User.id == user_id)
    result = await session.scalars(stmt)
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_verified = True
    session.add(user)
    await session.commit()
    return {"msg": "Email verified successfully"}


async def change_password(
    session: AsyncSession, user: User, data: PasswordChangeRequest
):
    """Change the user's password."""
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect",
        )

    user.hashed_password = hash_password(data.new_password)
    session.add(user)
    await session.commit()
    return {"msg": "Password changed successfully"}


async def password_reset_email_send(
    session: AsyncSession,
    data: PasswordResetEmailRequest,
    background_tasks: BackgroundTasks,
):
    """Generate a password reset token and send it to the user's email."""
    user = await get_user_by_email(session, data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found",
        )

    token = create_password_reset_token(user.id)
    link = f"{FRONTEND_URL}/account/password-reset?token={token}"
    print(f"Password reset link for {user.email}: {link}")
    background_tasks.add_task(
        send_email,
        subject="Reset your password",
        recipient=[user.email],
        body=f"Please click the following link to reset your password: {link}",
    )
    return {"msg": "Password reset email sent (check console for link)"}


async def verify_password_reset_token(
    session: AsyncSession, data: PasswordResetRequest
):
    """Verify the password reset token and reset the user's password."""
    user_id = verify_email_token_and_get_user_id(data.token, "password_reset")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    stmt = select(User).where(User.id == user_id)
    result = await session.scalars(stmt)
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    user.hashed_password = hash_password(data.new_password)
    session.add(user)
    await session.commit()
    return {"msg": "Password reset successfully"}
