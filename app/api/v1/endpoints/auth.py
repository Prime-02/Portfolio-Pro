from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from app.database import get_db
from app.core import get_password_hash
from app.models.schemas import DBUser, UserCreate
from sqlalchemy import cast, Boolean
from typing import Annotated, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import BaseModel, EmailStr
from app.core.security import generate_password_reset_token, verify_token
from datetime import timedelta
from app.models.db_models import User, UserSettings
from app.services.gmail_utils import send_email


from app.core.security import (
    authenticate_user,
    create_access_token,
    TokenData,
    get_expiration_timestamp,
)
from app.config import settings
from app.database import get_db
from app.models.schemas import DBUser
from sqlalchemy import cast, Boolean


router = APIRouter(prefix="/auth", tags=["users"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_info: Dict[str, Any]


class ForgottenPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgotten-password", status_code=status.HTTP_200_OK)
async def forgotten_password(
    request: ForgottenPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Initiate password reset process for a user.
    """
    # Check if user exists
    result = await db.execute(
        select(User).where(cast(User.email == request.email, Boolean) == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal whether user exists for security reasons
        return {
            "message": "If this email is registered, you'll receive a password reset link"
        }

    # Generate password reset token
    reset_token = generate_password_reset_token(email=str(user.email))

    # Send password reset email
    send_email(
        to=str(user.email),
        subject=f"Password Reset Request",
        body=f"Follow the link: https://www.lawchecks.com/{reset_token}/reset-password to reset your password.",
    )

    return {
        "message": "If this email is registered, you'll receive a password reset link"
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Complete password reset process using the provided token.
    """
    # Verify token and get email (implementation depends on your token system)
    token_payload = await verify_token(str(request.token))
    if not token_payload or "sub" not in token_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
    email = str(token_payload["sub"])

    # Update user password
    result = await db.execute(
        select(User).where(cast(User.email == email, Boolean) == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return {"message": "Password updated successfully"}


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Authenticate user
    user: DBUser | None = await authenticate_user(
        db=db,
        username_or_email=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect details",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Type-safe active check
    if not bool(user.is_active):  # Explicit conversion for type safety
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Token generation - fix the duplicate assignment
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    exp_timestamp = get_expiration_timestamp(access_token_expires)

    token_data = TokenData(
        sub=str(user.username),
        exp=exp_timestamp,
    )

    access_token: str = create_access_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_info={
            "username": str(user.username),
            "email": str(user.email),
            "role": str(user.role),
        },
    )


@router.post("/signup", response_model=DBUser, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)) -> DBUser:
    # 1. Check existing user
    result = await db.execute(
        select(User).where(
            or_(
                cast(User.email == user.email, Boolean) == True,
                cast(User.username == user.username, Boolean) == True,
            )
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )

    # 2. Create new user
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        is_active=True,
        role="user",
    )
    db.add(db_user)
    await db.flush()

    db_settings = UserSettings(
        language="en", theme="light", primary_theme="#000000", owner_id=db_user.id
    )
    db.add(db_settings)

    await db.commit()
    await db.refresh(db_user)
    return DBUser.model_validate(db_user)
