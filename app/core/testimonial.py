from typing import Dict, Union, List, Optional, cast
from fastapi import HTTPException, status, Depends
from app.core.security import get_current_user, optional_current_user
from app.database import get_db
from app.models.db_models import User, Testimonial
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import TestimonialBase, TestimonialCreate, TestimonialUpdate
from sqlalchemy.future import select
from sqlalchemy import and_
from uuid import UUID


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[Dict[str, Union[str, bool]], User, AsyncSession]]:
    return {"data": data, "user": user, "db": db}


async def add_testimonial(
    commons: Dict[
        str, Union[Dict[str, Union[str, bool]], User, AsyncSession]
    ] = Depends(get_common_params),
) -> Testimonial:
    testimonial_data = cast(Dict[str, Union[str, bool]], commons["data"])
    user = cast(User, commons["user"])
    db = cast(AsyncSession, commons["db"])

    if not testimonial_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Testimonial data was provided",
        )
    
    if "content" not in testimonial_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Content Provided",
        )

    if "author_name" not in testimonial_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An Author's name is required",
        )

    if "user_id" not in testimonial_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user ID is required",
        )

    # Check if user is trying to write testimonial for themselves
    if str(testimonial_data["user_id"]) == str(user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot write a testimonial for yourself",
        )

    # Check if author already wrote a testimonial for this user
    existing_testimonial = await db.execute(
        select(Testimonial)
        .where(
            and_(
                Testimonial.user_id == testimonial_data["user_id"],
                Testimonial.author_user_id == user.id
            )
        )
    )
    if existing_testimonial.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have already written a testimonial for this user",
        )

    # Verify target user exists
    target_user = await db.execute(
        select(User).where(User.id == testimonial_data["user_id"])
    )
    if not target_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    # Create testimonial
    new_testimonial = Testimonial(
        user_id=testimonial_data["user_id"],
        author_user_id=user.id,
        author_name=testimonial_data["author_name"],
        author_title=testimonial_data.get("author_title"),
        author_company=testimonial_data.get("author_company"),
        author_relationship=testimonial_data.get("author_relationship"),
        content=testimonial_data["content"],
        rating=testimonial_data.get("rating"),
    )

    db.add(new_testimonial)
    await db.commit()
    await db.refresh(new_testimonial)

    return new_testimonial


async def update_testimonial(
    testimonial_id: UUID,
    testimonial_update: TestimonialUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Testimonial:
    # Get the testimonial
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == testimonial_id)
    )
    testimonial = result.scalar_one_or_none()

    if not testimonial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        )

    # Check if user is the author of the testimonial
    if testimonial.author_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update testimonials you authored",
        )

    # Update only provided fields
    update_data = testimonial_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(testimonial, field, value)

    await db.commit()
    await db.refresh(testimonial)

    return testimonial


async def delete_testimonial(
    testimonial_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    # Get the testimonial
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == testimonial_id)
    )
    testimonial = result.scalar_one_or_none()

    if not testimonial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        )

    # Check if user is the author of the testimonial
    if testimonial.author_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete testimonials you authored",
        )

    await db.delete(testimonial)
    await db.commit()

    return {"message": "Testimonial deleted successfully"}


async def get_testimonial(
    testimonial_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(optional_current_user),
) -> Testimonial:
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == testimonial_id)
    )
    testimonial = result.scalar_one_or_none()

    if not testimonial:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        )

    return testimonial


async def get_user_testimonials(
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> List[Testimonial]:
    """Get all testimonials for a specific user"""
    result = await db.execute(
        select(Testimonial)
        .where(Testimonial.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .order_by(Testimonial.created_at.desc())
    )
    
    return result.scalars().all()


async def get_authored_testimonials(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Testimonial]:
    """Get all testimonials authored by the current user"""
    result = await db.execute(
        select(Testimonial)
        .where(Testimonial.author_user_id == user.id)
        .offset(skip)
        .limit(limit)
        .order_by(Testimonial.created_at.desc())
    )
    
    return result.scalars().all()


async def get_all_testimonials(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> List[Testimonial]:
    """Get all testimonials (public access)"""
    result = await db.execute(
        select(Testimonial)
        .offset(skip)
        .limit(limit)
        .order_by(Testimonial.created_at.desc())
    )
    
    return result.scalars().all()


# Additional utility functions

async def get_testimonial_stats(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[int, float]]:
    """Get testimonial statistics for a user"""
    from sqlalchemy import func, cast as sql_cast
    from sqlalchemy.types import Float
    
    result = await db.execute(
        select(
            func.count(Testimonial.id).label('total_count'),
            func.avg(sql_cast(Testimonial.rating, Float)).label('average_rating'),
            func.count(Testimonial.rating).label('rated_count')
        )
        .where(Testimonial.user_id == user_id)
    )
    
    stats = result.first()
    
    return {
        "total_testimonials": stats.total_count if stats else 0,
        "average_rating": round(float(stats.average_rating), 2) if stats and stats.average_rating else 0.0,
        "testimonials_with_rating": stats.rated_count if stats else 0,
    }


async def search_testimonials(
    query: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> List[Testimonial]:
    """Search testimonials by content, author name, or company"""
    from sqlalchemy import or_, func
    
    search_filter = or_(
        func.lower(Testimonial.content).contains(query.lower()),
        func.lower(Testimonial.author_name).contains(query.lower()),
        func.lower(Testimonial.author_company).contains(query.lower()),
    )
    
    result = await db.execute(
        select(Testimonial)
        .where(search_filter)
        .offset(skip)
        .limit(limit)
        .order_by(Testimonial.created_at.desc())
    )
    
    return result.scalars().all()