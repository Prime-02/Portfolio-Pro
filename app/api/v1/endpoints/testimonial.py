from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user, optional_current_user
from app.models.db_models import User, Testimonial
from app.models.schemas import TestimonialBase, TestimonialCreate, TestimonialUpdate
from app.core.testimonial import (
    add_testimonial,
    update_testimonial,
    delete_testimonial,
    get_testimonial,
    get_user_testimonials,
    get_authored_testimonials,
    get_all_testimonials,
    get_testimonial_stats,
    search_testimonials,
    get_common_params
)

router = APIRouter(prefix="/testimonials", tags=["testimonials"])


@router.post("/", response_model=TestimonialBase, status_code=201)
async def create_testimonial(
    testimonial_data: TestimonialCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new testimonial.
    
    - **user_id**: ID of the user receiving the testimonial
    - **author_user_id**: ID of the user writing the testimonial (automatically set to current user)
    - **author_name**: Name of the testimonial author
    - **content**: Testimonial content
    - **rating**: Optional rating (1-5)
    """
    # Convert Pydantic model to dict for the service function
    testimonial_dict = testimonial_data.model_dump()
    # Override author_user_id with current user
    testimonial_dict["author_user_id"] = user.id
    
    commons = await get_common_params(
        data=testimonial_dict,
        user=user,
        db=db
    )
    
    return await add_testimonial(commons)


@router.get("/", response_model=List[TestimonialBase])
async def list_all_testimonials(
    skip: int = Query(0, ge=0, description="Number of testimonials to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of testimonials to return"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """
    Get all testimonials (public access).
    
    - **skip**: Number of testimonials to skip (for pagination)
    - **limit**: Maximum number of testimonials to return
    """
    return await get_all_testimonials(
        skip=skip,
        limit=limit,
        db=db,
        current_user=current_user
    )


@router.get("/search", response_model=List[TestimonialBase])
async def search_testimonials_endpoint(
    q: str = Query(..., description="Search query"),
    skip: int = Query(0, ge=0, description="Number of testimonials to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of testimonials to return"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """
    Search testimonials by content, author name, or company.
    
    - **q**: Search query string
    - **skip**: Number of testimonials to skip (for pagination)
    - **limit**: Maximum number of testimonials to return
    """
    return await search_testimonials(
        query=q,
        skip=skip,
        limit=limit,
        db=db,
        current_user=current_user
    )


@router.get("/my-authored", response_model=List[TestimonialBase])
async def list_my_authored_testimonials(
    skip: int = Query(0, ge=0, description="Number of testimonials to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of testimonials to return"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all testimonials authored by the current user.
    
    - **skip**: Number of testimonials to skip (for pagination)
    - **limit**: Maximum number of testimonials to return
    """
    return await get_authored_testimonials(
        skip=skip,
        limit=limit,
        user=user,
        db=db
    )


@router.get("/user/{user_id}", response_model=List[TestimonialBase])
async def list_user_testimonials(
    user_id: UUID,
    skip: int = Query(0, ge=0, description="Number of testimonials to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of testimonials to return"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """
    Get all testimonials for a specific user (public access).
    
    - **user_id**: ID of the user whose testimonials to retrieve
    - **skip**: Number of testimonials to skip (for pagination)
    - **limit**: Maximum number of testimonials to return
    """
    return await get_user_testimonials(
        user_id=user_id,
        skip=skip,
        limit=limit,
        db=db,
        current_user=current_user
    )


@router.get("/user/{user_id}/stats", response_model=Dict[str, Union[int, float]])
async def get_user_testimonial_stats(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get testimonial statistics for a specific user.
    
    - **user_id**: ID of the user whose testimonial stats to retrieve
    
    Returns:
    - **total_testimonials**: Total number of testimonials
    - **average_rating**: Average rating (if ratings exist)
    - **testimonials_with_rating**: Number of testimonials with ratings
    """
    return await get_testimonial_stats(
        user_id=user_id,
        db=db
    )


@router.get("/{testimonial_id}", response_model=TestimonialBase)
async def get_testimonial_by_id(
    testimonial_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(optional_current_user),
):
    """
    Get a specific testimonial by ID (public access).
    
    - **testimonial_id**: ID of the testimonial to retrieve
    """
    return await get_testimonial(
        testimonial_id=testimonial_id,
        db=db,
        user=user
    )


@router.put("/{testimonial_id}", response_model=TestimonialBase)
async def update_testimonial_by_id(
    testimonial_id: UUID,
    testimonial_update: TestimonialUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a testimonial (only by the author).
    
    - **testimonial_id**: ID of the testimonial to update
    - Only the author of the testimonial can update it
    - All fields are optional in the update
    """
    return await update_testimonial(
        testimonial_id=testimonial_id,
        testimonial_update=testimonial_update,
        user=user,
        db=db
    )


@router.delete("/{testimonial_id}", response_model=Dict[str, str])
async def delete_testimonial_by_id(
    testimonial_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a testimonial (only by the author).
    
    - **testimonial_id**: ID of the testimonial to delete
    - Only the author of the testimonial can delete it
    """
    return await delete_testimonial(
        testimonial_id=testimonial_id,
        user=user,
        db=db
    )


# Additional utility routes

@router.get("/user/{user_id}/summary")
async def get_user_testimonial_summary(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a comprehensive summary of a user's testimonials including stats and recent testimonials.
    
    - **user_id**: ID of the user whose testimonial summary to retrieve
    """
    # Get stats
    stats = await get_testimonial_stats(user_id=user_id, db=db)
    
    # Get recent testimonials (last 5)
    recent_testimonials = await get_user_testimonials(
        user_id=user_id,
        skip=0,
        limit=5,
        db=db,
        current_user=None
    )
    
    return {
        "stats": stats,
        "recent_testimonials": recent_testimonials,
        "user_id": user_id
    }


@router.post("/user/{user_id}/quick", response_model=TestimonialBase, status_code=201)
async def create_quick_testimonial(
    user_id: UUID,
    content: str,
    author_name: str,
    rating: Optional[int] = None,
    author_title: Optional[str] = None,
    author_company: Optional[str] = None,
    author_relationship: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick testimonial creation endpoint with simplified parameters.
    
    - **user_id**: ID of the user receiving the testimonial
    - **content**: Testimonial content
    - **author_name**: Name of the testimonial author
    - **rating**: Optional rating (1-5)
    - Other fields are optional
    """
    testimonial_data = {
        "user_id": user_id,
        "author_user_id": user.id,
        "author_name": author_name,
        "content": content,
        "rating": rating,
        "author_title": author_title,
        "author_company": author_company,
        "author_relationship": author_relationship,
    }
    
    commons = await get_common_params(
        data=testimonial_data,
        user=user,
        db=db
    )
    
    return await add_testimonial(commons)