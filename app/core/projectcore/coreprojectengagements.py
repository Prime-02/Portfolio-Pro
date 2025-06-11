from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc
from fastapi import HTTPException, status

from app.models.db_models import ProjectLike, ProjectComment
from app.models.schemas import (
    ProjectLikeCreate,
    ProjectCommentCreate,
    ProjectCommentUpdate,
)


# ===== PROJECT LIKE CRUD OPERATIONS =====


async def create_project_like(db: Session, like_data: ProjectLikeCreate) -> ProjectLike:
    """Create a new project like"""
    # Check if user already liked this project
    existing_like = (
        db.query(ProjectLike)
        .filter(
            ProjectLike.project_id == like_data.project_id,
            ProjectLike.user_id == like_data.user_id,
        )
        .first()
    )

    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already liked this project",
        )

    db_like = ProjectLike(**like_data.model_dump())
    db.add(db_like)
    db.commit()
    db.refresh(db_like)
    return db_like


async def get_project_like(db: Session, like_id: UUID) -> Optional[ProjectLike]:
    """Get a specific project like by ID"""
    return (
        db.query(ProjectLike)
        .options(joinedload(ProjectLike.user))
        .filter(ProjectLike.id == like_id)
        .first()
    )


async def get_project_likes(
    db: Session, 
    project_id: UUID, 
    skip: int = 0, 
    limit: int = 100
) -> List[ProjectLike]:
    """Get all likes for a specific project"""
    return (
        db.query(ProjectLike)
        .options(joinedload(ProjectLike.user))
        .filter(ProjectLike.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


async def get_user_likes(
    db: Session, 
    user_id: UUID, 
    skip: int = 0, 
    limit: int = 100
) -> List[ProjectLike]:
    """Get all likes by a specific user"""
    return (
        db.query(ProjectLike)
        .options(joinedload(ProjectLike.user))
        .filter(ProjectLike.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )



async def check_user_liked_project(
    db: Session, project_id: UUID, user_id: UUID
) -> bool:
    """Check if a user has liked a specific project"""
    like = (
        db.query(ProjectLike)
        .filter(ProjectLike.project_id == project_id, ProjectLike.user_id == user_id)
        .first()
    )
    return like is not None


async def get_project_likes_count(db: Session, project_id: UUID) -> int:
    """Get the total count of likes for a project"""
    return db.query(ProjectLike).filter(ProjectLike.project_id == project_id).count()


async def delete_project_like(db: Session, project_id: UUID, user_id: UUID) -> bool:
    """Delete a project like (unlike)"""
    like = (
        db.query(ProjectLike)
        .filter(ProjectLike.project_id == project_id, ProjectLike.user_id == user_id)
        .first()
    )

    if not like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Like not found"
        )

    db.delete(like)
    db.commit()
    return True


async def toggle_project_like(db: Session, project_id: UUID, user_id: UUID) -> dict:
    """Toggle like status - like if not liked, unlike if already liked"""
    existing_like = (
        db.query(ProjectLike)
        .filter(ProjectLike.project_id == project_id, ProjectLike.user_id == user_id)
        .first()
    )

    if existing_like:
        # Unlike
        db.delete(existing_like)
        db.commit()
        return {"liked": False, "message": "Project unliked successfully"}
    else:
        # Like
        like_data = ProjectLikeCreate(project_id=project_id, user_id=user_id)
        db_like = ProjectLike(**like_data.model_dump())
        db.add(db_like)
        db.commit()
        db.refresh(db_like)
        return {"liked": True, "message": "Project liked successfully", "like": db_like}


# ===== PROJECT COMMENT CRUD OPERATIONS =====


async def create_project_comment(
    db: Session, comment_data: ProjectCommentCreate
) -> ProjectComment:
    """Create a new project comment"""
    # If it's a reply, verify parent comment exists and belongs to same project
    if comment_data.parent_comment_id:
        parent_comment = (
            db.query(ProjectComment)
            .filter(ProjectComment.id == comment_data.parent_comment_id)
            .first()
        )

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
    db.commit()
    db.refresh(db_comment)
    return db_comment


async def get_project_comment(
    db: Session, comment_id: UUID
) -> Optional[ProjectComment]:
    """Get a specific project comment by ID with replies"""
    return (
        db.query(ProjectComment)
        .options(joinedload(ProjectComment.replies))
        .filter(ProjectComment.id == comment_id)
        .first()
    )


async def get_project_comments(
    db: Session,
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    include_replies: bool = True,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> List[ProjectComment]:
    """Get all comments for a specific project (top-level comments only by default)"""
    query = db.query(ProjectComment).filter(
        ProjectComment.project_id == project_id,
        ProjectComment.parent_comment_id.is_(None),  # Only top-level comments
    )

    if include_replies:
        query = query.options(joinedload(ProjectComment.replies))

    # Add sorting
    if sort_order.lower() == "desc":
        query = query.order_by(
            desc(getattr(ProjectComment, sort_by, ProjectComment.created_at))
        )
    else:
        query = query.order_by(
            asc(getattr(ProjectComment, sort_by, ProjectComment.created_at))
        )

    return query.offset(skip).limit(limit).all()


async def get_comment_replies(
    db: Session, parent_comment_id: UUID, skip: int = 0, limit: int = 50
) -> List[ProjectComment]:
    """Get all replies to a specific comment"""
    return (
        db.query(ProjectComment)
        .filter(ProjectComment.parent_comment_id == parent_comment_id)
        .order_by(asc(ProjectComment.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


async def get_user_comments(
    db: Session, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[ProjectComment]:
    """Get all comments by a specific user"""
    return (
        db.query(ProjectComment)
        .filter(ProjectComment.user_id == user_id)
        .order_by(desc(ProjectComment.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


async def update_project_comment(
    db: Session, comment_id: UUID, comment_update: ProjectCommentUpdate, user_id: UUID
) -> Optional[ProjectComment]:
    """Update a project comment (only by the comment author)"""
    db_comment = (
        db.query(ProjectComment).filter(ProjectComment.id == comment_id).first()
    )

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

    db.commit()
    db.refresh(db_comment)
    return db_comment


async def delete_project_comment(db: Session, comment_id: UUID, user_id: UUID) -> bool:
    """Delete a project comment (only by the comment author)"""
    db_comment = (
        db.query(ProjectComment).filter(ProjectComment.id == comment_id).first()
    )

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
    replies = (
        db.query(ProjectComment)
        .filter(ProjectComment.parent_comment_id == comment_id)
        .all()
    )

    for reply in replies:
        db.delete(reply)

    # Delete the main comment
    db.delete(db_comment)
    db.commit()
    return True


async def get_project_comments_count(db: Session, project_id: UUID) -> int:
    """Get the total count of comments for a project"""
    return (
        db.query(ProjectComment).filter(ProjectComment.project_id == project_id).count()
    )


async def get_comment_thread(db: Session, comment_id: UUID) -> Optional[ProjectComment]:
    """Get a comment with all its nested replies"""

    def load_replies_recursively(comment):
        replies = (
            db.query(ProjectComment)
            .filter(ProjectComment.parent_comment_id == comment.id)
            .order_by(asc(ProjectComment.created_at))
            .all()
        )

        for reply in replies:
            reply.replies = load_replies_recursively(reply)

        return replies

    main_comment = (
        db.query(ProjectComment).filter(ProjectComment.id == comment_id).first()
    )

    if main_comment:
        main_comment.replies = load_replies_recursively(main_comment)

    return main_comment


# ===== UTILITY FUNCTIONS =====


async def get_project_engagement_stats(db: Session, project_id: UUID) -> dict:
    """Get engagement statistics for a project (likes and comments count)"""
    likes_count = await get_project_likes_count(db, project_id)
    comments_count = await get_project_comments_count(db, project_id)

    return {
        "project_id": project_id,
        "likes_count": likes_count,
        "comments_count": comments_count,
        "total_engagement": likes_count + comments_count,
    }


async def get_user_engagement_stats(db: Session, user_id: UUID) -> dict:
    """Get user engagement statistics (total likes given and comments made)"""
    likes_given = db.query(ProjectLike).filter(ProjectLike.user_id == user_id).count()
    comments_made = (
        db.query(ProjectComment).filter(ProjectComment.user_id == user_id).count()
    )

    return {
        "user_id": user_id,
        "likes_given": likes_given,
        "comments_made": comments_made,
        "total_interactions": likes_given + comments_made,
    }
