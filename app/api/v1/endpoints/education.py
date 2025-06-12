from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, Union, List, Optional
from app.models.schemas import EducationBase, EducationCreate, EducationUpdate
from app.models.db_models import User
from app.core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from uuid import UUID
from app.core.coreeducation import (
    add_education,
    get_all_educations,
    get_all_educations_public,
    get_education_by_id,
    get_education_by_id_public,
    update_education,
    delete_education,
    get_educations_by_user_id,
    get_common_params
)

router = APIRouter(prefix="/education", tags=["education"])


@router.post(
    "/",
    response_model=EducationCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new education record",
    description="Create a new education record for the authenticated user"
)
async def create_education(
    education_data: EducationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new education record"""
    data_dict = education_data.dict(exclude={"user_id"})  # Exclude user_id from input
    commons = await get_common_params(data_dict, user, db)
    return await add_education(commons)


@router.get(
    "/me",
    response_model=Dict[str, Union[List[EducationBase], int]],
    summary="Get current user's education records",
    description="Get all education records for the authenticated user with pagination"
)
async def get_my_educations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all education records for the current user"""
    return await get_all_educations(user, db, skip, limit)


@router.get(
    "/public",
    response_model=Dict[str, Union[List[EducationBase], int]],
    summary="Get all education records (public)",
    description="Get all education records with optional filtering and pagination"
)
async def get_all_educations_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    institution: Optional[str] = Query(None, description="Filter by institution name"),
    degree: Optional[str] = Query(None, description="Filter by degree"),
    field_of_study: Optional[str] = Query(None, description="Filter by field of study"),
    db: AsyncSession = Depends(get_db)
):
    """Get all education records with filtering and pagination"""
    return await get_all_educations_public(
        db, skip, limit, institution, degree, field_of_study
    )


@router.get(
    "/user/{user_id}",
    response_model=Dict[str, Union[List[EducationBase], int]],
    summary="Get education records by user ID",
    description="Get all education records for a specific user"
)
async def get_user_educations(
    user_id: UUID = Path(..., description="User ID to get education records for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get all education records for a specific user"""
    return await get_educations_by_user_id(user_id, db, skip, limit)


@router.get(
    "/me/{education_id}",
    response_model=EducationBase,
    summary="Get specific education record (owner)",
    description="Get a specific education record that belongs to the authenticated user"
)
async def get_my_education_by_id(
    education_id: UUID = Path(..., description="Education record ID"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific education record for the current user"""
    return await get_education_by_id(education_id, user, db)


@router.get(
    "/{education_id}",
    response_model=EducationBase,
    summary="Get specific education record (public)",
    description="Get a specific education record by ID"
)
async def get_education_by_id_endpoint(
    education_id: UUID = Path(..., description="Education record ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific education record by ID"""
    return await get_education_by_id_public(education_id, db)


@router.put(
    "/{education_id}",
    response_model=EducationBase,
    summary="Update education record",
    description="Update an existing education record"
)
async def update_education_endpoint(
    education_data: EducationUpdate,
    education_id: UUID = Path(..., description="Education record ID to update"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing education record"""
    # Convert Pydantic model to dict, excluding None values
    update_dict = education_data.dict(exclude_unset=True, exclude_none=True)
    return await update_education(education_id, update_dict, user, db)


@router.patch(
    "/{education_id}",
    response_model=EducationBase,
    summary="Partially update education record",
    description="Partially update an existing education record"
)
async def patch_education_endpoint(
    education_data: EducationUpdate,
    education_id: UUID = Path(..., description="Education record ID to update"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Partially update an existing education record"""
    # Convert Pydantic model to dict, excluding None values for partial updates
    update_dict = education_data.dict(exclude_unset=True, exclude_none=True)
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update"
        )
    
    return await update_education(education_id, update_dict, user, db)


@router.delete(
    "/{education_id}",
    response_model=Dict[str, str],
    summary="Delete education record",
    description="Delete an existing education record"
)
async def delete_education_endpoint(
    education_id: UUID = Path(..., description="Education record ID to delete"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an existing education record"""
    return await delete_education(education_id, user, db)


# Additional utility endpoints

@router.get(
    "/search/institutions",
    response_model=List[str],
    summary="Search institutions",
    description="Get a list of unique institutions from all education records"
)
async def search_institutions(
    q: Optional[str] = Query(None, description="Search query for institution names"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Search for institutions"""
    from sqlalchemy import distinct
    from app.models.db_models import Education
    from sqlalchemy.future import select
    
    query = select(distinct(Education.institution)).where(Education.institution.isnot(None))
    
    if q:
        query = query.where(Education.institution.ilike(f"%{q}%"))
    
    query = query.limit(limit).order_by(Education.institution)
    
    result = await db.execute(query)
    institutions = result.scalars().all()
    
    return [inst for inst in institutions if inst]


@router.get(
    "/search/degrees",
    response_model=List[str],
    summary="Search degrees",
    description="Get a list of unique degrees from all education records"  
)
async def search_degrees(
    q: Optional[str] = Query(None, description="Search query for degree names"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Search for degrees"""
    from sqlalchemy import distinct
    from app.models.db_models import Education
    from sqlalchemy.future import select
    
    query = select(distinct(Education.degree)).where(Education.degree.isnot(None))
    
    if q:
        query = query.where(Education.degree.ilike(f"%{q}%"))
    
    query = query.limit(limit).order_by(Education.degree)
    
    result = await db.execute(query)
    degrees = result.scalars().all()
    
    return [degree for degree in degrees if degree]


@router.get(
    "/search/fields",
    response_model=List[str],
    summary="Search fields of study",
    description="Get a list of unique fields of study from all education records"
)
async def search_fields_of_study(
    q: Optional[str] = Query(None, description="Search query for field names"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Search for fields of study"""
    from sqlalchemy import distinct
    from app.models.db_models import Education
    from sqlalchemy.future import select
    
    query = select(distinct(Education.field_of_study)).where(Education.field_of_study.isnot(None))
    
    if q:
        query = query.where(Education.field_of_study.ilike(f"%{q}%"))
    
    query = query.limit(limit).order_by(Education.field_of_study)
    
    result = await db.execute(query)
    fields = result.scalars().all()
    
    return [field for field in fields if field]


@router.get(
    "/stats/summary",
    response_model=Dict[str, Union[int, List[Dict[str, Union[str, int]]]]],
    summary="Get education statistics",
    description="Get summary statistics about education records"
)
async def get_education_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get education statistics"""
    from sqlalchemy import func, desc
    from app.models.db_models import Education
    from sqlalchemy.future import select
    
    # Total count
    total_result = await db.execute(select(func.count(Education.id)))
    total_count = total_result.scalar()
    
    # Top institutions
    top_institutions_result = await db.execute(
        select(Education.institution, func.count(Education.id).label('count'))
        .where(Education.institution.isnot(None))
        .group_by(Education.institution)
        .order_by(desc('count'))
        .limit(10)
    )
    top_institutions = [
        {"name": row[0], "count": row[1]} 
        for row in top_institutions_result.fetchall()
    ]
    
    # Top degrees
    top_degrees_result = await db.execute(
        select(Education.degree, func.count(Education.id).label('count'))
        .where(Education.degree.isnot(None))
        .group_by(Education.degree)
        .order_by(desc('count'))
        .limit(10)
    )
    top_degrees = [
        {"name": row[0], "count": row[1]} 
        for row in top_degrees_result.fetchall()
    ]
    
    # Current students count
    current_students_result = await db.execute(
        select(func.count(Education.id))
        .where(Education.is_current == True)
    )
    current_students = current_students_result.scalar()
    
    return {
        "total_records": total_count,
        "current_students": current_students,
        "top_institutions": top_institutions,
        "top_degrees": top_degrees
    }