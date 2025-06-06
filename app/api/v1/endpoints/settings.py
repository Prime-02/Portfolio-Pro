from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordBearer
from app.models.schemas import (
    UserSettings as DBSettings,
    DBUser,
    UserUpdateRequest,
    UserProfileRequest,
)
from app.models.db_models import UserSettings, User
from app.core.security import get_user_settings, get_current_user
from typing import Annotated, Union
from app.core.user import update_user_info, create_profile
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", status_code=status.HTTP_200_OK, response_model=DBSettings)
async def get_user_settings(
    settings: Annotated[UserSettings, Depends(get_user_settings)],
) -> DBSettings:
    """
    Retrieve user settings.
    """

    return settings


@router.get("/info", status_code=status.HTTP_200_OK, response_model=DBUser)
async def get_user_info(
    current_user: Annotated[DBUser, Depends(get_current_user)],
) -> DBUser:
    """
    Retrieve user information.
    """
    return current_user


@router.put("/info", status_code=status.HTTP_200_OK, response_model=DBUser)
async def user_info_update(
    update_data: UserUpdateRequest,
    current_user: Annotated[Union[DBUser, User], Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> DBUser:
    update_dict = update_data.model_dump(exclude_unset=True)

    # Create the commons dictionary with correct key names
    commons = {
        "data": update_dict,  # Must match what get_common_params expects
        "user": current_user,
        "db": db,
    }

    return await update_user_info(commons)


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
