"""
Authentication and User Management API

This module provides endpoints for user authentication, account management, and device registration.
All sensitive operations require authentication unless otherwise noted.

Authentication Flow:
1. User signs up via /auth/signup
2. User logs in via /auth/login to get access token
3. Token is used in Authorization header for protected routes

Routes:

AUTHENTICATION ENDPOINTS:

1. POST /auth/login
   - Summary: User login
   - Description: Authenticates user and returns JWT access token
   - Request Body:
     - username: str (username or email)
     - password: str
     - grant_type: str (should be "password")
   - Returns:
     - access_token: JWT token for authorization
     - token_type: "bearer"
     - user_info: Basic user details

2. POST /auth/signup
   - Summary: User registration
   - Description: Creates new user account
   - Request Body:
     - username: str (3-30 chars, specific format rules)
     - email: valid email format
     - password: str
   - Returns: Newly created user details
   - Auto-creates:
     - Default user settings
     - Welcome email

PASSWORD RECOVERY:

3. POST /auth/forgotten-password
   - Summary: Initiate password reset
   - Description: Sends password reset email if account exists
   - Request Body:
     - email: registered email address
   - Returns: Generic success message (security purposes)

4. POST /auth/reset-password
   - Summary: Complete password reset
   - Description: Sets new password using valid reset token
   - Request Body:
     - token: Valid password reset token
     - new_password: str
   - Returns: Success message

DEVICE MANAGEMENT:

5. POST /auth/register-device
   - Summary: Register user device
   - Description: Records new device for authenticated user
   - Requires: Valid JWT token
   - Request Body:
     - device_name: str
     - device_type: str
   - Returns: Registered device details
   - Triggers: Security notification email

Security Features:
- Password hashing (bcrypt)
- JWT token expiration
- Device registration alerts
- Secure password reset flow
- Username validation rules

Error Responses:
- 400 Bad Request: Invalid input data
- 401 Unauthorized: Invalid credentials
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Resource not found
- 409 Conflict: Duplicate entry (username/email/device)

Rate Limiting:
- 5 requests/minute for sensitive endpoints
- 20 requests/minute for other endpoints

Email Notifications:
- Account creation
- Password changes
- New device registration
"""



from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from app.database import get_db
from app.core import get_password_hash
from app.models.schemas import DBUser, UserCreate, UserDevicesRequest
from sqlalchemy import cast, Boolean
from typing import Annotated, Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import BaseModel, EmailStr
from app.core.security import (
    generate_password_reset_token,
    verify_token,
    get_current_user,
    validate_username,
)
from datetime import timedelta
from app.models.db_models import User, UserSettings, UserDevices
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
from uuid import UUID

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
    id: Optional[UUID] = None


class ForgottenPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str


class DBUserId(DBUser):
    id: Optional[int] = None


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
        select(User).where(User.email == request.email)
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
        select(User).where(User.email == email)
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
    access_token_expires = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
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
        id=UUID(str(user.id))
    )


@router.post("/signup", response_model=DBUser, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)) -> DBUser:
    # 1. Check existing user
    result = await db.execute(
        select(User).where(
            or_(
                User.email == user.email,
                User.username == user.username,
            )
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )
    if not validate_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 30 characters, must start with alphanumeric characters, no consecutive special characters (__ or -- or .. etc.), can only contain letters, numbers, underscores, periods and hyphens, ensure it doesnt have special words like 'admin', 'root', 'user', 'test', 'guest' etc.",
        )

    # 2. Create new user
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        is_active=True,
        role="user",
        is_superuser=False
    )
    db.add(db_user)
    await db.flush()

    db_settings = UserSettings(
        language="en",
        theme="light",
        primary_theme="#000000",
        owner_id=db_user.id,
        secondary_theme="#ffffff",
        layout_style="default",
    )
    db.add(db_settings)
    await db.commit()
    await db.refresh(db_user)
    send_email(
        to=str(user.email),
        subject=f"We are happy to have you on board, {user.username}!",
        body=f"Welcome to Portfolio Pro, Your account has been created successfully. You can now log in and start using our services.",
    )
    return DBUser.model_validate(db_user)


@router.post(
    "/register-device",
    status_code=status.HTTP_200_OK,
    response_model=UserDevicesRequest,
)
async def register_device(
    device: UserDevicesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: DBUserId = Depends(get_current_user),
) -> UserDevicesRequest:
    # Check if the device already exists for this user
    existing_device_result = await db.execute(
        select(UserDevices).where(
            UserDevices.device_name == device.device_name,
            UserDevices.user_id == current_user.id,
        )
    )
    existing_device = existing_device_result.scalar_one_or_none()

    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device already registered for this user",
        )

    # Create new device
    new_device = UserDevices(
        device_name=device.device_name,
        device_type=device.device_type,
        user_id=current_user.id,
        # Add any other device attributes here
    )

    db.add(new_device)
    await db.commit()
    await db.refresh(new_device)
    send_email(
        to=str(current_user.email),
        subject=f"Device Registered Successfully",
        body=f"A new device '{device.device_name}'was used to access your account.",
    )
    return new_device
