"""
Professional Skills API Router

This module provides CRUD (Create, Read, Update, Delete) operations for managing professional skills
through a FastAPI interface. The router is protected by OAuth2 authentication and requires a valid
access token for all operations.

Routes:
    POST /skills/ - Create a new professional skill
    GET /skills/ - Get all professional skills for the authenticated user
    GET /skills/{skill_id} - Get a specific professional skill by ID
    PUT /skills/{skill_id} - Update an existing professional skill
    DELETE /skills/{skill_id} - Delete a professional skill

Dependencies:
    - OAuth2PasswordBearer: For handling OAuth2 token authentication
    - AsyncSession: For asynchronous database operations
    - get_current_user: For retrieving the authenticated user from the token

Models:
    - ProfessionalSkillsCreate: Pydantic model for skill creation
    - ProfessionalSkillsBase: Base Pydantic model for skill representation
    - ProfessionalSkillsUpdate: Pydantic model for skill updates

The router uses an asynchronous database session and requires all operations to be performed by
an authenticated user. Each skill is associated with the user who created it.

Security:
    All endpoints require authentication via OAuth2 bearer token. The token should be included
    in the Authorization header as: 'Bearer {token}'

Error Responses:
    - 401 Unauthorized: If no valid token is provided
    - 403 Forbidden: If user tries to access/modify skills they don't own
    - 404 Not Found: If a skill with the specified ID doesn't exist
    - 422 Unprocessable Entity: If request data validation fails

Example Usage:
    # Create a new skill
    POST /skills/
    Headers: Authorization: Bearer {access_token}
    Body: {"skill_name": "Python", "proficiency_level": "Advanced"}

    # Get all skills
    GET /skills/
    Headers: Authorization: Bearer {access_token}

    # Get specific skill
    GET /skills/123e4567-e89b-12d3-a456-426614174000
    Headers: Authorization: Bearer {access_token}

    # Update a skill
    PUT /skills/123e4567-e89b-12d3-a456-426614174000
    Headers: Authorization: Bearer {access_token}
    Body: {"proficiency_level": "Expert"}

    # Delete a skill
    DELETE /skills/123e4567-e89b-12d3-a456-426614174000
    Headers: Authorization: Bearer {access_token}
"""





from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, status, Depends
from typing import Dict, Union, List
from app.models.schemas import (
    ProfessionalSkillsCreate,
    ProfessionalSkillsBase,
    ProfessionalSkillsUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.skills import (
    add_skill,
    get_all_skills as core_get_all_skills,
    get_skill_by_id as core_get_skill_by_id,
    update_skill as core_update_skill,
    delete_skill as core_delete_skill,
)
from app.models.db_models import User
from app.core.security import get_current_user
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
router = APIRouter(prefix="/skills", tags=["skills"])

@router.post(
    "/",
    response_model=ProfessionalSkillsCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new professional skill",
)
async def create_skill_route(
    skill_data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new professional skill for the authenticated user.

    - **skill_name**: (required) Name of the skill
    - **proficiency_level**: (optional) Proficiency level (default: 'Beginner')
    """
    commons = {"data": skill_data, "user": user, "db": db}
    return await add_skill(commons)

@router.get(
    "/",
    response_model=List[ProfessionalSkillsBase],
    summary="Get all professional skills",
)
async def get_all_skills_route(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all professional skills for the authenticated user.
    """
    return await core_get_all_skills(user=user, db=db)

@router.get(
    "/{skill_id}",
    response_model=ProfessionalSkillsBase,
    summary="Get a specific professional skill",
)
async def get_skill_by_id_route(
    skill_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a specific professional skill by ID.

    - **skill_id**: UUID of the skill to retrieve
    """
    return await core_get_skill_by_id(skill_id, user=user, db=db)

@router.put(
    "/{skill_id}",
    response_model=ProfessionalSkillsBase,
    summary="Update a professional skill",
)
async def update_skill_route(
    skill_id: UUID,
    skill_data: ProfessionalSkillsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a professional skill.

    - **skill_id**: UUID of the skill to update
    - **skill_name**: (optional) New name for the skill
    - **proficiency_level**: (optional) New proficiency level
    """
    return await core_update_skill(skill_id, skill_data, user=user, db=db)

@router.delete(
    "/{skill_id}",
    response_model=Dict[str, Union[bool, str]],
    summary="Delete a professional skill",
)
async def delete_skill_route(
    skill_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a professional skill.

    - **skill_id**: UUID of the skill to delete
    """
    return await core_delete_skill(skill_id, user=user, db=db)