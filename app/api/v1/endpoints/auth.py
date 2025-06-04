from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from uuid import UUID
from app.models.schemas import User, UserCreate
from app.database import get_db
from app.core import get_password_hash
from app.models.schemas import User as DBUser
from app.core.security import get_current_user
from sqlalchemy import cast, Boolean
from typing import Annotated, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from pydantic import BaseModel
from uuid import UUID
from datetime import timedelta



from app.core.security import authenticate_user, create_access_token, TokenData, get_expiration_timestamp
from app.config import settings
from app.database import get_db
from app.models.schemas import User as DBUser
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


@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user with either email or username and password.
    Returns an access token for successful authentication.

    Args:
        form_data: OAuth2 password form containing username/email and password
        db: Async database session

    Returns:
        TokenResponse containing access token and user info

    Raises:
        HTTPException: 401 for invalid credentials, 400 for inactive users
    """
    # Validate input types
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid input format",
        )

    # Authenticate user
    user: DBUser | None = await authenticate_user(
        db=db,
        username_or_email=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Type-safe active check
    if not bool(user.is_active):  # Explicit conversion for type safety
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Token generation
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_expires = timedelta(minutes=30)
    exp_timestamp = get_expiration_timestamp(access_token_expires)


    token_data = TokenData(
        sub=user.username,
        exp=exp_timestamp,
    )

    access_token: str = create_access_token(
        data=token_data.model_dump()
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_info={
            "username": str(user.username),
            "email": str(user.email),
            "role": str(user.role),
        },
    )


@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """
    Create a new user account with hashed password.
    Default role is 'user' and is_active is True.
    """
    # Check if user already exists by email or username
    existing_user = await db.execute(
        select(DBUser).where(
            or_(
                cast(DBUser.email == user.email, Boolean) == True,
                cast(DBUser.username == user.username, Boolean) == True,
            )
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )

    # Create new user with hashed password
    db_user = DBUser(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        is_active=True,
        role="user",  # Default role
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.get("/{user_id}/user-data", response_model=User)
async def read_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
) -> User:
    """
    Get user details by ID (requires authentication).
    Users can only access their own data unless they're admin.
    """
    # Admins can access any user, regular users only their own
    if str(user_id) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user",
        )

    user = await db.get(DBUser, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.patch("/{user_id}/deactivate", response_model=User)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: DBUser = Depends(get_current_user),
) -> User:
    """
    Deactivate a user account (admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can deactivate users",
        )

    user = await db.get(DBUser, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    return user
