from app.models.schemas import EducationBase, EducationCreate, EducationUpdate
from app.models.db_models import User, Education
from typing import Dict, Union, List, Optional
from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.database import get_db
from sqlalchemy.future import select
from sqlalchemy import func, or_
from uuid import UUID


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": data, "user": user, "db": db}


async def add_education(commons: dict = Depends(get_common_params)) -> EducationCreate:
    education_data = commons["data"]
    user = commons["user"]
    db: AsyncSession = commons["db"]

    if not education_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No institution data provided",
        )

    if "institution" not in education_data or "degree" not in education_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name of institution and degree is required",
        )

    existing_education = await db.execute(
        select(Education)
        .where(Education.user_id == user.id)
        .where(Education.institution == str(education_data["institution"]))
        .where(Education.degree == str(education_data["degree"]))
    )
    if existing_education.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Education already exists for this user",
        )

    new_education = Education(
        user_id=user.id,
        institution=education_data["institution"],
        degree=education_data["degree"],
        field_of_study=education_data.get("field_of_study"),
        start_year=education_data.get("start_year"),
        end_year=education_data.get("end_year"),
        is_current=education_data.get("is_current", False),
        description=education_data.get("description"),
    )

    db.add(new_education)
    await db.commit()
    await db.refresh(new_education)

    return EducationCreate(
        user_id=user.id,
        institution=education_data["institution"],
        degree=education_data["degree"],
        field_of_study=education_data.get("field_of_study"),
        start_year=education_data.get("start_year"),
        end_year=education_data.get("end_year"),
        is_current=education_data.get("is_current", False),
        description=education_data.get("description"),
    )


async def get_all_educations(
    user: User, 
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10
) -> Dict[str, Union[List[EducationBase], int, None]]:
    """Get all educations for the current user with pagination"""
    
    # Get total count
    count_result = await db.execute(
        select(func.count(Education.id)).where(Education.user_id == user.id)
    )
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        select(Education)
        .where(Education.user_id == user.id)
        .offset(skip)
        .limit(limit)
        .order_by(Education.start_year.desc().nulls_last())
    )
    educations = result.scalars().all()

    return {
        "educations": [
            EducationBase(
                id=edu.id,
                institution=edu.institution,
                degree=edu.degree,
                field_of_study=edu.field_of_study,
                start_year=edu.start_year,
                end_year=edu.end_year,
                is_current=edu.is_current,
                description=edu.description,
                user_id=edu.user_id
            ) for edu in educations
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


async def get_all_educations_public(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    institution: Optional[str] = None,
    degree: Optional[str] = None,
    field_of_study: Optional[str] = None
) -> Dict[str, Union[List[EducationBase], int, None]]:
    """Get all educations (public access) with filtering and pagination"""
    
    # Build query with optional filters
    query = select(Education)
    
    if institution:
        query = query.where(Education.institution.ilike(f"%{institution}%"))
    if degree:
        query = query.where(Education.degree.ilike(f"%{degree}%"))
    if field_of_study:
        query = query.where(Education.field_of_study.ilike(f"%{field_of_study}%"))
    
    # Get total count with filters
    count_query = select(func.count(Education.id))
    if institution:
        count_query = count_query.where(Education.institution.ilike(f"%{institution}%"))
    if degree:
        count_query = count_query.where(Education.degree.ilike(f"%{degree}%"))
    if field_of_study:
        count_query = count_query.where(Education.field_of_study.ilike(f"%{field_of_study}%"))
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query
        .offset(skip)
        .limit(limit)
        .order_by(Education.start_year.desc().nulls_last())
    )
    educations = result.scalars().all()

    return {
        "educations": [
            EducationBase(
                id=edu.id,
                institution=edu.institution,
                degree=edu.degree,
                field_of_study=edu.field_of_study,
                start_year=edu.start_year,
                end_year=edu.end_year,
                is_current=edu.is_current,
                description=edu.description,
                user_id=edu.user_id
            ) for edu in educations
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


async def get_education_by_id(
    education_id: UUID,
    user: User,
    db: AsyncSession
) -> EducationBase:
    """Get a specific education by ID (must belong to current user)"""
    
    result = await db.execute(
        select(Education)
        .where(Education.id == education_id)
        .where(Education.user_id == user.id)
    )
    education = result.scalar_one_or_none()
    
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )
    
    return EducationBase(
        id=education.id,
        institution=education.institution,
        degree=education.degree,
        field_of_study=education.field_of_study,
        start_year=education.start_year,
        end_year=education.end_year,
        is_current=education.is_current,
        description=education.description,
        user_id=education.user_id
    )


async def get_education_by_id_public(
    education_id: UUID,
    db: AsyncSession
) -> EducationBase:
    """Get a specific education by ID (public access)"""
    
    result = await db.execute(
        select(Education).where(Education.id == education_id)
    )
    education = result.scalar_one_or_none()
    
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )
    
    return EducationBase(
        id=education.id,
        institution=education.institution,
        degree=education.degree,
        field_of_study=education.field_of_study,
        start_year=education.start_year,
        end_year=education.end_year,
        is_current=education.is_current,
        description=education.description,
        user_id=education.user_id
    )


async def update_education(
    education_id: UUID,
    education_data: Dict[str, Union[str, bool, int]],
    user: User,
    db: AsyncSession
) -> EducationBase:
    """Update an education record"""
    
    # Get existing education
    result = await db.execute(
        select(Education)
        .where(Education.id == education_id)
        .where(Education.user_id == user.id)
    )
    education = result.scalar_one_or_none()
    
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )
    
    # Check for duplicate if institution or degree is being updated
    if "institution" in education_data or "degree" in education_data:
        new_institution = education_data.get("institution", education.institution)
        new_degree = education_data.get("degree", education.degree)
        
        # Only check for duplicates if values are actually changing
        if new_institution != education.institution or new_degree != education.degree:
            existing_check = await db.execute(
                select(Education)
                .where(Education.user_id == user.id)
                .where(Education.institution == str(new_institution))
                .where(Education.degree == str(new_degree))
                .where(Education.id != education_id)
            )
            if existing_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Education with this institution and degree already exists"
                )
    
    # Update fields
    for field, value in education_data.items():
        if hasattr(education, field):
            setattr(education, field, value)
    
    await db.commit()
    await db.refresh(education)
    
    return EducationBase(
        id=education.id,
        institution=education.institution,
        degree=education.degree,
        field_of_study=education.field_of_study,
        start_year=education.start_year,
        end_year=education.end_year,
        is_current=education.is_current,
        description=education.description,
        user_id=education.user_id
    )


async def delete_education(
    education_id: UUID,
    user: User,
    db: AsyncSession
) -> Dict[str, str]:
    """Delete an education record"""
    
    result = await db.execute(
        select(Education)
        .where(Education.id == education_id)
        .where(Education.user_id == user.id)
    )
    education = result.scalar_one_or_none()
    
    if not education:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education record not found"
        )
    
    await db.delete(education)
    await db.commit()
    
    return {"message": "Education record deleted successfully"}


async def get_educations_by_user_id(
    user_id: UUID,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10
) -> Dict[str, Union[List[EducationBase], int, None]]:
    """Get all educations for a specific user (public access)"""
    
    # Get total count
    count_result = await db.execute(
        select(func.count(Education.id)).where(Education.user_id == user_id)
    )
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        select(Education)
        .where(Education.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(Education.start_year.desc().nulls_last())
    )
    educations = result.scalars().all()

    return {
        "educations": [
            EducationBase(
                id=edu.id,
                institution=edu.institution,
                degree=edu.degree,
                field_of_study=edu.field_of_study,
                start_year=edu.start_year,
                end_year=edu.end_year,
                is_current=edu.is_current,
                description=edu.description,
                user_id=edu.user_id
            ) for edu in educations
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }