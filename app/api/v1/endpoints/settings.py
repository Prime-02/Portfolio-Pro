"""
User Settings and Profile Management Routes

This module provides API endpoints for managing user settings, profile information,
and account details. All routes require authentication.

Routes:

SETTINGS OPERATIONS:
1. GET /settings/
   - Summary: Retrieve user settings
   - Description: Returns all settings for the authenticated user
   - Response Model: DBSettings
   - Returns: Complete user settings object

2. PUT /settings/
   - Summary: Update user settings
   - Description: Modifies user settings with provided data (partial updates supported)
   - Request Body: UserSettingsBase (all fields optional)
   - Response Model: UserSettingsBase
   - Returns: Updated settings object

USER INFORMATION OPERATIONS:
3. GET /settings/info
   - Summary: Get user account information
   - Description: Returns core account details (username, email, etc.)
   - Response Model: UserUpdateRequest
   - Returns: Complete user information object

4. PUT /settings/info
   - Summary: Update user account information
   - Description: Modifies user account details (partial updates supported)
   - Request Body: UserUpdateRequest (all fields optional)
   - Response Model: UserUpdateRequest
   - Returns: Updated user information

PROFILE OPERATIONS:
5. GET /settings/profile
   - Summary: Get user profile
   - Description: Returns public profile information (bio, social links, etc.)
   - Response Model: UserProfileRequest
   - Returns: Complete profile object

6. PUT /settings/profile
   - Summary: Update user profile
   - Description: Creates or modifies public profile information
   - Request Body: UserProfileRequest
   - Response Model: UserProfileRequest
   - Returns: Updated profile object

Authentication:
- All routes require valid JWT token in Authorization header
- Token can be obtained from /auth/token endpoint

Error Responses:
- 401 Unauthorized: Missing or invalid credentials
- 403 Forbidden: Insufficient permissions
- 422 Unprocessable Entity: Invalid request data

Request Behavior:
- PUT endpoints support partial updates (omit unchanged fields)
- All sensitive fields are automatically filtered from responses
- Profile and settings are created automatically with default values if missing
"""


from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordBearer
from app.models.schemas import (
    UserSettings as DBSettings,
    UserSettingsBase,
    DBUser,
    UserUpdateRequest,
    UserProfileRequest,
)
from app.models.db_models import UserSettings, User
from app.core.security import get_user_settings, get_current_user
from typing import Annotated, Union
from app.core.user import (
    update_user_info,
    create_profile,
    get_profile,
    get_user_info,
    update_user_settings,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=DBSettings)
async def user_settings(
    settings: Annotated[UserSettings, Depends(get_user_settings)],
) -> DBSettings:
    """
    Retrieve user settings.
    """

    return settings


@router.put("/", status_code=status.HTTP_200_OK, response_model=UserSettingsBase)
async def update_settings(
    update_data: UserSettingsBase,
    current_user: Annotated[Union[DBUser, User], Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserSettingsBase:
    commons = {
        "data": update_data.model_dump(exclude_unset=True),
        "user": current_user,
        "db": db,
    }
    return await update_user_settings(commons)


@router.get("/info", status_code=status.HTTP_200_OK, response_model=UserUpdateRequest)
async def user_info_get(
    current_user: Annotated[UserUpdateRequest, Depends(get_current_user)],
) -> UserUpdateRequest:
    """
    Retrieve user information.
    """
    return current_user


@router.put("/info", status_code=status.HTTP_200_OK, response_model=UserUpdateRequest)
async def user_info_update(
    update_data: UserUpdateRequest,
    current_user: Annotated[Union[UserUpdateRequest, User], Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserUpdateRequest:
    commons = {
        "data": update_data.model_dump(exclude_unset=True),
        "user": current_user,
        "db": db,
    }
    return await update_user_info(commons)


@router.get("/info", response_model=UserUpdateRequest)
async def view_info(profile: UserUpdateRequest = Depends(get_user_info)):
    """Get the current user's profile"""
    return profile


@router.put(
    "/profile", status_code=status.HTTP_200_OK, response_model=UserProfileRequest
)
async def user_profile_update(
    update_data: UserProfileRequest,
    current_user: Annotated[Union[DBUser, User], Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserProfileRequest:
    update_dict = update_data.model_dump(exclude_unset=False)
    commons = {
        "update_data": update_dict,  # Must match what get_common_params expects
        "user": current_user,
        "db": db,
    }

    return await create_profile(commons)


@router.get("/profile", response_model=UserProfileRequest)
async def view_profile(
    current_user: Annotated[Union[DBUser, User], Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserProfileRequest:
    """Get the current user's profile"""
    commons = {
        "user": current_user,
        "db": db,
    }
    return await get_profile(commons)
