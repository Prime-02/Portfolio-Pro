from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any,  Union

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import  select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import and_
from sqlalchemy import or_
from app.config import settings
from app.dependencies import get_db
from app.models.db_models import User as DBUser, UserSettings
from sqlalchemy import cast, Boolean
from typing import Annotated
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.schemas import User as DBUser
from pydantic import BaseModel




oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


class TokenData(BaseModel):
    sub: str  # username
    exp: Optional[int] = None  # Now expects Unix timestamp (int or None)

def get_expiration_timestamp(expires_delta: timedelta) -> int:
    """Converts a timedelta to a future Unix timestamp"""
    return int((datetime.now(timezone.utc) + expires_delta).timestamp())



def create_access_token(data: TokenData) -> str:
    """
    Creates a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.model_dump().copy()
    expire = datetime.now(timezone.utc) + to_encode.pop("exp", timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(data.model_dump(), settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def verify_token(token: str = Depends(oauth2_scheme)) -> Dict[str, int]:
    """
    Verifies JWT token and returns decoded payload.

    Args:
        token: JWT token to verify

    Returns:
        Decoded token payload

    Raises:
        HTTPException: 401 if token is invalid/expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: Any = payload.get("sub")
        if username is type(str):
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DBUser:
    """
    Get the current authenticated user from JWT token.

    Args:
        token: JWT access token
        db: Async database session

    Returns:
        Authenticated user

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},  # Disable audience verification if not used
        )
        username: Any = payload.get("sub")
        if not username:  # More explicit than 'is None'
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e  # Preserve exception chain

    # Use scalar() instead of scalar_one_or_none() for better error handling
    result = await db.execute(select(DBUser).where(DBUser.username == username))
    user = result.scalar()

    if user is None:
        raise credentials_exception

    # Optional: Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: DBUser = Depends(get_current_user),
) -> DBUser:
    """
    Gets the current active user (additional layer for explicit active check).

    Args:
        current_user: Current user from get_current_user

    Returns:
        Active user

    Raises:
        HTTPException: 400 if user is inactive
    """
    if bool(current_user.is_active):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_user_settings(
    current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserSettings:
    """
    Gets user settings for the authenticated user.

    Args:
        current_user: Current authenticated user
        db: Async database session

    Returns:
        User settings object

    Raises:
        HTTPException: 404 if settings not found
    """
    # Try to get settings using user's ID
    settings = await db.get(UserSettings, current_user.id)

    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User settings not found"
        )

    return settings


async def get_user_with_settings(
    current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DBUser:
    """
    Gets the current user with their settings loaded.

    Args:
        current_user: Current authenticated user
        db: Async database session

    Returns:
        User with settings relationship loaded

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Re-query with settings loaded to avoid lazy loading issues
    stmt= (
        select(DBUser)
        .options(selectinload(DBUser.settings))
        .where(
            and_(
                cast(DBUser.id == current_user.id, Boolean) == True,
                cast(DBUser.is_active, Boolean) == True,
            )
        )
    )

    result = await db.execute(stmt)
    user_with_settings = result.scalar_one_or_none()

    if user_with_settings is None:
        raise credentials_exception

    return user_with_settings


def get_password_hash(password: Union[str, bytes]) -> str:
    """
    Hashes a password using bcrypt with a randomly generated salt.

    Args:
        password: Plain-text password (as string or bytes)

    Returns:
        Hashed password as a string (UTF-8 encoded)

    Raises:
        ValueError: If password is empty or None
    """
    if not password:
        raise ValueError("Password cannot be empty")

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

    Args:
        plain_password: Input password to check
        hashed_password: Stored bcrypt hash

    Returns:
        bool: True if password matches, False otherwise

    Raises:
        ValueError: If either password is empty or None
    """
    if not plain_password or not hashed_password:
        return False

    try:
        if isinstance(plain_password, str):
            plain_password = plain_password.encode("utf-8")
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")

        return bcrypt.checkpw(plain_password, hashed_password)
    except (ValueError, TypeError):
        # Handle any bcrypt-related errors gracefully
        return False


async def authenticate_user(
    db: AsyncSession, username_or_email: str, password: str
) -> Optional[DBUser]:
    """
    Authenticate user with either username or email and verify password.
    """
    # Try to find user by username or email
    user = await db.execute(
        select(DBUser).where(
            or_(
                cast(DBUser.username == username_or_email, Boolean) == True,
                cast(DBUser.username == username_or_email, Boolean) == True,
            )
        )
    )
    user = user.scalar_one_or_none()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
