from fastapi import APIRouter, status, Depends
from typing import Dict, Union, List
from app.models.schemas import (
    SocialLinksCreate,
    SocialLinksBase,
    SocialLinksUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.socials import (
    add_social,
    get_all_socials as core_get_all_socials,
    get_social_by_id as core_get_social_by_id,
    update_social as core_update_social,
    delete_social as core_delete_social,
)
from app.models.db_models import User
from app.core.security import get_current_user
from app.database import get_db

router = APIRouter(prefix="/socials", tags=["socials"])

@router.post(
    "/",
    response_model=SocialLinksCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new social link",
)
async def create_social_route(
    social_data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new social link for the authenticated user.

    - **platform_name**: (required) Name of the social platform (e.g., 'Twitter', 'LinkedIn')
    - **profile_url**: (required) URL to the user's profile on this platform
    """
    commons = {"data": social_data, "user": user, "db": db}
    return await add_social(commons)

@router.get(
    "/",
    response_model=List[SocialLinksBase],
    summary="Get all social links",
)
async def get_all_socials_route(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all social links for the authenticated user.
    """
    return await core_get_all_socials(user=user, db=db)

@router.get(
    "/{social_id}",
    response_model=SocialLinksBase,
    summary="Get a specific social link",
)
async def get_social_by_id_route(
    social_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a specific social link by ID.

    - **social_id**: UUID of the social link to retrieve
    """
    return await core_get_social_by_id(social_id, user=user, db=db)

@router.put(
    "/{social_id}",
    response_model=SocialLinksBase,
    summary="Update a social link",
)
async def update_social_route(
    social_id: UUID,
    social_data: SocialLinksUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a social link.

    - **social_id**: UUID of the social link to update
    - **platform_name**: (optional) New name for the social platform
    - **profile_url**: (optional) New profile URL
    """
    return await core_update_social(social_id, social_data, user=user, db=db)

@router.delete(
    "/{social_id}",
    response_model=Dict[str, Union[bool, str]],
    summary="Delete a social link",
)
async def delete_social_route(
    social_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a social link.

    - **social_id**: UUID of the social link to delete
    """
    return await core_delete_social(social_id, user=user, db=db)