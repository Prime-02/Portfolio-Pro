from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, Optional, Union
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import and_, cast, Boolean, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import re
from typing import Optional
from app.config import settings
from app.database import get_db
from app.dependencies import get_db
from app.models.db_models import User, UserSettings
from app.models.schemas import DBUser, UserWithSettings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# In your security.py or dependencies.py
async def optional_oauth2_scheme(request: Request) -> Optional[str]:
    try:
        return await oauth2_scheme(request)
    except HTTPException:
        return None  # Instead of raising 401


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
    Creates a JWT access token with proper expiration handling.
    """
    to_encode = data.model_dump().copy()

    # Handle both timedelta and integer expiration
    expire = to_encode.pop("exp", None)

    if expire is None:
        expire = timedelta(minutes=15)

    if isinstance(expire, timedelta):
        expire = datetime.now(timezone.utc) + expire
    elif isinstance(expire, int):
        # If it's a timestamp, use it directly
        pass
    else:
        raise ValueError("exp must be either timedelta or int")

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_password_reset_token(email: str) -> str:
    """Generates a JWT token for password reset.
    Args:
        email: User's email address
    Returns:
        JWT token as a string
    """
    expiration = timedelta(hours=1)  # Token valid for 1 hour
    data = TokenData(sub=email, exp=get_expiration_timestamp(expiration))
    return create_access_token(data)


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
        if not isinstance(username, str):  # Correct way to check type
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    strict: bool = False,  # New parameter to control error behavior
) -> Optional[User]:
    """
    Get authenticated user with error control.

    Args:
        strict: If True, raises 401 on failure. If False, returns None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        username: Any = payload.get("sub")
        if not username:
            if strict:
                raise credentials_exception
            return None

        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None and strict:
            raise credentials_exception
        return user

    except JWTError:
        if strict:
            raise credentials_exception
        return None


async def optional_current_user(
    token: Annotated[str, Depends(optional_oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    if not token:  # Early exit if no token provided
        return None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if not username:
            return None
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    except JWTError:
        return None


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
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserSettings:
    """
    Gets user settings for the authenticated user.
    """
    # Refresh the user with settings eagerly loaded
    result = await db.execute(
        select(User)
        .options(selectinload(User.settings))
        .where(User.id == current_user.id)
    )
    user = result.scalars().first()

    if not user or not user.settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User settings not found"
        )
    return user.settings


async def get_user_with_settings(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserWithSettings:
    """
    Gets the current user with their settings loaded.
    """
    # Re-query with settings loaded to avoid lazy loading issues
    stmt = (
        select(User)
        .options(selectinload(User.settings))
        .where(
            and_(
                User.id == current_user.id,
                User.is_active,
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
) -> Optional[User]:
    """
    Authenticate user with either username or email and verify password.
    """
    # Try to find user by username or email
    result = await db.execute(
        select(User).where(
            or_(
                User.username == username_or_email,
                User.email == username_or_email,
            )
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not verify_password(password, str(user.hashed_password)):
        return None

    return user


def validate_username(username: str) -> bool:
    """
    Validate a username for authentication purposes.

    Rules:
    - Length between 3 and 30 characters
    - Only contains alphanumeric characters, underscores, hyphens, and periods
    - Starts and ends with alphanumeric character
    - No consecutive special characters (__ or -- or .. etc.)
    - Not a reserved word (admin, root, etc.)

    Returns:
    - True if username is valid
    - False if invalid
    """
    if not isinstance(username, str):
        return False

    username = username.strip()

    # Length check
    if len(username) < 3 or len(username) > 30:
        return False

    # Character set check
    if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        return False

    # Start/end check
    if not username[0].isalnum() or not username[-1].isalnum():
        return False

    # Consecutive special characters check
    if re.search(r"[_\.-]{2,}", username):
        return False

    # Reserved words check
    reserved_words = {
        "admin",
        "administrator",
        "root",
        "system",
        "null",
        "undefined",
        "moderator",
        "guest",
        "user",
        "owner",
        "me",
        "self",
    }
    if username.lower() in reserved_words:
        return False

    # No whitespace check
    if " " in username:
        return False

    return True
