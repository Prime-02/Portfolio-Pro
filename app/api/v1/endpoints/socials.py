"""
Social Links API Router
=======================

This module provides API endpoints to manage social media links for authenticated users.
It allows users to create, retrieve, update, and delete their social profile URLs on platforms
like Twitter, LinkedIn, GitHub, etc.

Endpoints
---------

1. POST `/socials/`
    - Summary: Add a new social link.
    - Description: Creates a new social link associated with the authenticated user.
    - Request Body:
        - platform_name (str): Name of the social platform (e.g., Twitter, LinkedIn). **Required**.
        - profile_url (str): The full URL to the user's profile on the specified platform. **Required**.
    - Response: The created social link object.
    - Status Codes:
        - 201: Created successfully.
        - 400: Invalid input.

2. GET `/socials/`
    - Summary: Get all social links.
    - Description: Retrieves a list of all social links belonging to the authenticated user.
    - Response: List of social link objects.
    - Status Codes:
        - 200: Success.
        - 401: Unauthorized (if not authenticated).

3. GET `/socials/{social_id}`
    - Summary: Get a specific social link.
    - Description: Fetches a social link by its UUID. Ensures the link belongs to the current user.
    - Path Parameters:
        - social_id (UUID): The ID of the social link to retrieve.
    - Response: The requested social link object.
    - Status Codes:
        - 200: Success.
        - 404: Not found (if the link doesn't exist or doesn’t belong to the user).

4. PUT `/socials/{social_id}`
    - Summary: Update a social link.
    - Description: Updates an existing social link with new data such as a new platform name or profile URL.
    - Path Parameters:
        - social_id (UUID): The ID of the social link to update.
    - Request Body:
        - platform_name (str, optional): Updated platform name.
        - profile_url (str, optional): Updated profile URL.
    - Response: The updated social link object.
    - Status Codes:
        - 200: Updated successfully.
        - 404: Not found or access denied.

5. DELETE `/socials/{social_id}`
    - Summary: Delete a social link.
    - Description: Deletes a social link belonging to the authenticated user.
    - Path Parameters:
        - social_id (UUID): The ID of the social link to delete.
    - Response: A message indicating whether the deletion was successful.
    - Status Codes:
        - 200: Deleted successfully.
        - 404: Not found or access denied.

Security
--------
All endpoints require authentication via a valid JWT token.
The current user is resolved using the `get_current_user` dependency.

Models
------
- `SocialLinksCreate`: Schema used for creating new social links.
- `SocialLinksBase`: Schema used for reading/displaying social links.
- `SocialLinksUpdate`: Schema used for updating existing links.

Dependencies
------------
- `get_current_user`: Retrieves the authenticated user from the request.
- `get_db`: Provides an asynchronous SQLAlchemy database session.

"""


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