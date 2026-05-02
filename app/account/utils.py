import uuid

from decouple import config
from sqlalchemy import select
from fastapi import HTTPException
from passlib.context import CryptContext
from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from app.account.models import RefreshToken, User

JWT_SECRET_KEY = config("JWT_SECRET_KEY")
JWT_ALGORITHM = config("JWT_ALGORITHM")
JWT_ACCESS_TOKEN_TIME_MIN = config("JWT_ACCESS_TOKEN_TIME_MIN", cast=int)
JWT_REFRESH_TOKEN_TIME_DAY = config("JWT_REFRESH_TOKEN_TIME_DAY", cast=int)
EMAIL_VERIFICATION_TOKEN_TIME_HOUR = config(
    "EMAIL_VERIFICATION_TOKEN_TIME_HOUR", cast=int
)
EMAIL_PASSWORD_RESET_TOKEN_TIME_HOUR = config(
    "EMAIL_PASSWORD_RESET_TOKEN_TIME_HOUR", cast=int
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    """
    Hashes the given password using bcrypt and returns the hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """Verifies that the given plain password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Creates a JWT access token with the given data and expiration time."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_TIME_MIN)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, JWT_ALGORITHM)


async def create_tokens(session: AsyncSession, user: User):
    """
    Creates both access and refresh tokens for the given user and stores the
    refresh token in the database.
    """
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_TIME_DAY)

    refresh_token = RefreshToken(
        user_id=user.id, token=refresh_token_str, expires_at=expires_at
    )
    session.add(refresh_token)
    await session.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
    }


def decode_token(token: str):
    """
    Decodes the given JWT token and returns the payload if valid, otherwise
    raises an HTTPException.
    """
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=JWT_ALGORITHM)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_refresh_token(session: AsyncSession, token: str):
    """
    Verifies the given refresh token by checking its existence, revocation
    status, and expiration in the database. If valid, returns the associated
    user; otherwise, returns None.
    """
    stmt = select(RefreshToken).where(RefreshToken.token == token)
    result = await session.scalars(stmt)
    db_refresh_token = result.first()

    if db_refresh_token and not db_refresh_token.revoked:
        expires_at = db_refresh_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc):
            user_stmt = select(User).where(User.id == db_refresh_token.user_id)
            user_result = await session.scalars(user_stmt)
            return user_result.first()

    return None


def create_email_verification_token(user_id: int):
    """
    Creates a JWT token for email verification with the given user ID and a
    specific expiration time. The token includes the user ID as the subject
    and a type indicating it's for email verification.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        hours=EMAIL_VERIFICATION_TOKEN_TIME_HOUR
    )
    to_encode = {"sub": str(user_id), "type": "verify_email", "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_email_token_and_get_user_id(token: str, token_type: str):
    """
    Verifies the given email token by decoding it and checking its type.
    If the token is valid and of the expected type, returns the user ID
    from the token's subject; otherwise, returns None.
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != token_type:
        return None
    return int(payload.get("sub"))


async def get_user_by_email(session: AsyncSession, email: str):
    """
    Retrieves a user from the database based on the provided email address.
    Executes a SQL query to find the user with the matching email and returns
    the user object if found; otherwise, returns None.
    """
    stmt = select(User).where(User.email == email)
    result = await session.scalars(stmt)
    return result.first()


def create_password_reset_token(user_id: int):
    """
    Creates a JWT token for password reset with the given user ID and a
    specific expiration time. The token includes the user ID as the subject
    and a type indicating it's for password reset.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        hours=EMAIL_PASSWORD_RESET_TOKEN_TIME_HOUR
    )
    to_encode = {"sub": str(user_id), "type": "password_reset", "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


async def revoke_refresh_token(session: AsyncSession, token: str):
    """
    Revokes the given refresh token by marking it as revoked in the database.
    Executes a SQL query to find the refresh token with the matching token
    string, and if found, updates its revoked status to True and commits the
    change to the database.
    """
    stmt = select(RefreshToken).where(RefreshToken.token == token)
    result = await session.scalars(stmt)
    db_refresh_token = result.first()

    if db_refresh_token:
        db_refresh_token.revoked = True
        await session.commit()
