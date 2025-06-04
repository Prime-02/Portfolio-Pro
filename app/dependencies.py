from typing import Union
import bcrypt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.database import get_db

# Security scheme for OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# --------------------------
# Password Hashing Utilities
# --------------------------


def get_password_hash(password: Union[str, bytes]) -> str:
    """
    Hashes a password using bcrypt with a randomly generated salt.

    Args:
        password: Plain-text password (as string or bytes)

    Returns:
        Hashed password as a string (UTF-8 encoded)
    """
    if isinstance(password, str):
        password = password.encode("utf-8")

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password, salt)
    return hashed_password.decode("utf-8")


def verify_password(
    plain_password: Union[str, bytes], hashed_password: Union[str, bytes]
) -> bool:
    """
    Verifies a plain-text password against a bcrypt hash.
    """
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")

    return bcrypt.checkpw(plain_password, hashed_password)


async def get_db_session(
    db: Union[AsyncSession, Session] = Depends(get_db),
) -> Union[AsyncSession, Session]:
    """Dependency that can work with both sync and async sessions"""
    return db
