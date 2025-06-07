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