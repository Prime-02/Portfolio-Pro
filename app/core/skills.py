from typing import Dict, Union, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import User, ProfessionalSkills
from app.models.schemas import (
    ProfessionalSkillsCreate,
    ProfessionalSkillsBase,
    ProfessionalSkillsUpdate,
)
from fastapi import HTTPException, status, Depends
from app.core.security import get_current_user
from app.database import get_db
from sqlalchemy.future import select
import uuid
from datetime import datetime


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": data, "user": user, "db": db}


async def add_skill(
    commons: dict = Depends(get_common_params),
) -> ProfessionalSkillsCreate:
    skill_data = commons["data"]
    user = commons["user"]
    db: AsyncSession = commons["db"]
    
    if not skill_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No skill data provided"
        )

    if "skill_name" not in skill_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Skill name is required"
        )

    existing_skill = await db.execute(
        select(ProfessionalSkills)
        .where(ProfessionalSkills.user_id == user.id)
        .where(ProfessionalSkills.skill_name == str(skill_data["skill_name"]))
    )
    if existing_skill.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already exists for this user",
        )

    skill_id = uuid.uuid4()
    created_at = datetime.now()

    new_skill = ProfessionalSkills(
        id=skill_id,
        user_id=user.id,
        skill_name=str(skill_data["skill_name"]),
        proficiency_level=str(skill_data.get("proficiency_level", "Beginner")),
        created_at=created_at,
    )

    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)

    return ProfessionalSkillsCreate(
        # id=uuid.UUID(str(skill_id)),
        user_id=uuid.UUID(str(user.id)),
        skill_name=str(new_skill.skill_name),
        proficiency_level=str(new_skill.proficiency_level),
        # created_at=datetime.fromisoformat(new_skill.created_at.isoformat()),
    )


async def get_all_skills(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProfessionalSkillsBase]:
    result = await db.execute(
        select(ProfessionalSkills).where(ProfessionalSkills.user_id == user.id)
    )
    skills = result.scalars().all()

    return [
        ProfessionalSkillsBase(
            # id=uuid.UUID(str(skill.id)),
            skill_name=str(skill.skill_name),
            proficiency_level=str(skill.proficiency_level),
            # created_at=datetime.fromisoformat(skill.created_at.isoformat()),
        )
        for skill in skills
    ]


async def get_skill_by_id(
    skill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfessionalSkillsBase:
    result = await db.execute(
        select(ProfessionalSkills)
        .where(ProfessionalSkills.id == skill_id)
        .where(ProfessionalSkills.user_id == user.id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    return ProfessionalSkillsBase(
        # id=uuid.UUID(str(skill.id)),
        skill_name=str(skill.skill_name),
        proficiency_level=str(skill.proficiency_level),
        # created_at=datetime.fromisoformat(skill.created_at.isoformat()),
    )


async def update_skill(
    skill_id: uuid.UUID,
    skill_data: ProfessionalSkillsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfessionalSkillsBase:
    result = await db.execute(
        select(ProfessionalSkills)
        .where(ProfessionalSkills.id == skill_id)
        .where(ProfessionalSkills.user_id == user.id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    # Check if the new skill name already exists (if it's being updated)
    if skill_data.skill_name and skill_data.skill_name != skill.skill_name:
        existing_skill = await db.execute(
            select(ProfessionalSkills)
            .where(ProfessionalSkills.user_id == user.id)
            .where(ProfessionalSkills.skill_name == skill_data.skill_name)
            .where(ProfessionalSkills.id != skill_id)
        )
        if existing_skill.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skill with this name already exists for this user",
            )

    # Update fields if they are provided in the update data
    if skill_data.skill_name is not None:
        skill.skill_name = skill_data.skill_name
    if skill_data.proficiency_level is not None:
        skill.proficiency_level = skill_data.proficiency_level

    await db.commit()
    await db.refresh(skill)

    return ProfessionalSkillsBase(
        # id=uuid.UUID(str(skill.id)),
        skill_name=str(skill.skill_name),
        proficiency_level=str(skill.proficiency_level),
        # created_at=datetime.fromisoformat(skill.created_at.isoformat()),
    )


async def delete_skill(
    skill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[bool, str]]:
    result = await db.execute(
        select(ProfessionalSkills)
        .where(ProfessionalSkills.id == skill_id)
        .where(ProfessionalSkills.user_id == user.id)
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    await db.delete(skill)
    await db.commit()

    return {"success": True, "message": "Skill deleted successfully"}
