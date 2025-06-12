from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import desc, asc, select, func
from fastapi import HTTPException, status

from app.models.db_models import ProjectLike, ProjectComment
from app.models.schemas import (
    ProjectLikeCreate,
    ProjectCommentCreate,
    ProjectCommentUpdate,
)


# ===== PROJECT LIKE CRUD OPERATIONS =====


async def create_project_like(db: AsyncSession, like_data: ProjectLikeCreate) -> ProjectLike:
    """Create a new project like"""
    # Check if user already liked this project
    result = await db.execute(
        select(ProjectLike).filter(
            ProjectLike.project_id == like_data.project_id,
            ProjectLike.user_id == like_data.user_id,
        )
    )
    existing_like = result.scalar_one_or_none()

    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already liked this project",
        )

    db_like = ProjectLike(**like_data.model_dump())
    db.add(db_like)
    await db.commit()
    await db.refresh(db_like)
    return db_like


async def get_project_like(db: AsyncSession, like_id: UUID) -> Optional[ProjectLike]:
    """Get a specific project like by ID"""
    result = await db.execute(
        select(ProjectLike)
        .options(selectinload(ProjectLike.user))
        .filter(ProjectLike.id == like_id)
    )
    return result.scalar_one_or_none()


async def get_project_likes(
    db: AsyncSession, 
    project_id: UUID, 
    skip: int = 0, 
    limit: int = 100
) -> List[ProjectLike]:
    """Get all likes for a specific project"""
    result = await db.execute(
        select(ProjectLike)
        .options(selectinload(ProjectLike.user))
        .filter(ProjectLike.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_user_likes(
    db: AsyncSession, 
    user_id: UUID, 
    skip: int = 0, 
    limit: int = 100
) -> List[ProjectLike]:
    """Get all likes by a specific user"""
    result = await db.execute(
        select(ProjectLike)
        .options(selectinload(ProjectLike.user))
        .filter(ProjectLike.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def check_user_liked_project(
    db: AsyncSession, project_id: UUID, user_id: UUID
) -> bool:
    """Check if a user has liked a specific project"""
    result = await db.execute(
        select(ProjectLike).filter(
            ProjectLike.project_id == project_id, 
            ProjectLike.user_id == user_id
        )
    )
    like = result.scalar_one_or_none()
    return like is not None


async def get_project_likes_count(db: AsyncSession, project_id: UUID) -> int:
    """Get the total count of likes for a project"""
    result = await db.execute(
        select(func.count(ProjectLike.id)).filter(ProjectLike.project_id == project_id)
    )
    return result.scalar()


async def delete_project_like(db: AsyncSession, project_id: UUID, user_id: UUID) -> bool:
    """Delete a project like (unlike)"""
    result = await db.execute(
        select(ProjectLike).filter(
            ProjectLike.project_id == project_id, 
            ProjectLike.user_id == user_id
        )
    )
    like = result.scalar_one_or_none()

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Like not found"
        )

    await db.delete(like)
    await db.commit()
    return True


async def toggle_project_like(db: AsyncSession, project_id: UUID, user_id: UUID) -> dict:
    """Toggle like status - like if not liked, unlike if already liked"""
    result = await db.execute(
        select(ProjectLike).filter(
            ProjectLike.project_id == project_id, 
            ProjectLike.user_id == user_id
        )
    )
    existing_like = result.scalar_one_or_none()

    if existing_like:
        # Unlike
        await db.delete(existing_like)
        await db.commit()
        return {"liked": False, "message": "Project unliked successfully"}
    else:
        # Like
        like_data = ProjectLikeCreate(project_id=project_id, user_id=user_id)
        db_like = ProjectLike(**like_data.model_dump())
        db.add(db_like)
        await db.commit()
        await db.refresh(db_like)
        return {"liked": True, "message": "Project liked successfully", "like": db_like}


# ===== PROJECT COMMENT CRUD OPERATIONS =====


async def create_project_comment(
    db: AsyncSession, comment_data: ProjectCommentCreate
) -> ProjectComment:
    """Create a new project comment"""
    # If it's a reply, verify parent comment exists and belongs to same project
    if comment_data.parent_comment_id:
        result = await db.execute(
            select(ProjectComment).filter(ProjectComment.id == comment_data.parent_comment_id)
        )
        parent_comment = result.scalar_one_or_none()

        if not parent_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found"
            )

        if parent_comment.project_id != comment_data.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent comment does not belong to the same project",
            )

    db_comment = ProjectComment(**comment_data.model_dump())
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment


async def get_project_comment(
    db: AsyncSession, comment_id: UUID
) -> Optional[ProjectComment]:
    """Get a specific project comment by ID with replies"""
    result = await db.execute(
        select(ProjectComment)
        .options(selectinload(ProjectComment.replies))
        .filter(ProjectComment.id == comment_id)
    )
    return result.scalar_one_or_none()


async def get_project_comments(
    db: AsyncSession,
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    include_replies: bool = True,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> List[ProjectComment]:
    """Get all comments for a specific project (top-level comments only by default)"""
    query = select(ProjectComment).filter(
        ProjectComment.project_id == project_id,
        ProjectComment.parent_comment_id.is_(None),  # Only top-level comments
    )

    if include_replies:
        query = query.options(selectinload(ProjectComment.replies))

    # Add sorting
    sort_column = getattr(ProjectComment, sort_by, ProjectComment.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


async def get_comment_replies(
    db: AsyncSession, parent_comment_id: UUID, skip: int = 0, limit: int = 50
) -> List[ProjectComment]:
    """Get all replies to a specific comment"""
    result = await db.execute(
        select(ProjectComment)
        .filter(ProjectComment.parent_comment_id == parent_comment_id)
        .order_by(asc(ProjectComment.created_at))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_user_comments(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[ProjectComment]:
    """Get all comments by a specific user"""
    result = await db.execute(
        select(ProjectComment)
        .filter(ProjectComment.user_id == user_id)
        .order_by(desc(ProjectComment.created_at))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_project_comment(
    db: AsyncSession, comment_id: UUID, comment_update: ProjectCommentUpdate, user_id: UUID
) -> Optional[ProjectComment]:
    """Update a project comment (only by the comment author)"""
    result = await db.execute(
        select(ProjectComment).filter(ProjectComment.id == comment_id)
    )
    db_comment = result.scalar_one_or_none()

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    # Check if user is the author of the comment
    if db_comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments",
        )

    # Update only provided fields
    update_data = comment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_comment, field, value)

    await db.commit()
    await db.refresh(db_comment)
    return db_comment


async def delete_project_comment(db: AsyncSession, comment_id: UUID, user_id: UUID) -> bool:
    """Delete a project comment (only by the comment author)"""
    result = await db.execute(
        select(ProjectComment).filter(ProjectComment.id == comment_id)
    )
    db_comment = result.scalar_one_or_none()

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    # Check if user is the author of the comment
    if db_comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )

    # Delete all replies first (cascade delete)
    replies_result = await db.execute(
        select(ProjectComment).filter(ProjectComment.parent_comment_id == comment_id)
    )
    replies = replies_result.scalars().all()

    for reply in replies:
        await db.delete(reply)

    # Delete the main comment
    await db.delete(db_comment)
    await db.commit()
    return True


async def get_project_comments_count(db: AsyncSession, project_id: UUID) -> int:
    """Get the total count of comments for a project"""
    result = await db.execute(
        select(func.count(ProjectComment.id)).filter(ProjectComment.project_id == project_id)
    )
    return result.scalar()


async def get_comment_thread(db: AsyncSession, comment_id: UUID) -> Optional[ProjectComment]:
    """Get a comment with all its nested replies"""

    async def load_replies_recursively(comment):
        result = await db.execute(
            select(ProjectComment)
            .filter(ProjectComment.parent_comment_id == comment.id)
            .order_by(asc(ProjectComment.created_at))
        )
        replies = result.scalars().all()

        for reply in replies:
            reply.replies = await load_replies_recursively(reply)

        return replies

    result = await db.execute(
        select(ProjectComment).filter(ProjectComment.id == comment_id)
    )
    main_comment = result.scalar_one_or_none()

    if main_comment:
        main_comment.replies = await load_replies_recursively(main_comment)

    return main_comment


# ===== UTILITY FUNCTIONS =====


async def get_project_engagement_stats(db: AsyncSession, project_id: UUID) -> dict:
    """Get engagement statistics for a project (likes and comments count)"""
    likes_count = await get_project_likes_count(db, project_id)
    comments_count = await get_project_comments_count(db, project_id)

    return {
        "project_id": project_id,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "total_engagement": likes_count + comments_count,
    }


async def get_user_engagement_stats(db: AsyncSession, user_id: UUID) -> dict:
    """Get user engagement statistics (total likes given and comments made)"""
    likes_result = await db.execute(
        select(func.count(ProjectLike.id)).filter(ProjectLike.user_id == user_id)
    )
    likes_given = likes_result.scalar()

    comments_result = await db.execute(
        select(func.count(ProjectComment.id)).filter(ProjectComment.user_id == user_id)
    )
    comments_made = comments_result.scalar()

    return {
        "user_id": user_id,
        "likes_given": likes_given,
        "comments_made": comments_made,
        "total_interactions": likes_given + comments_made,
    }