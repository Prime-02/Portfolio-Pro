from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from models.db_models import Suggestion, SuggestionComment, SuggestionVote, User
from models.schemas import SuggestionBase, SuggestionUpdate, SuggestionCommentBase


# ================== SUGGESTION CRUD ==================

async def create_suggestion(
    db: AsyncSession,
    suggestion_data: SuggestionBase,
    user: User
) -> Suggestion:
    """
    Create a new suggestion (max 3 per user).
    """
    # Check if user already has 3 suggestions
    result = await db.execute(
        select(func.count(Suggestion.id)).where(Suggestion.user_id == user.id)
    )
    suggestion_count = result.scalar()
    
    if suggestion_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 3 suggestions allowed per user. Please delete an existing suggestion first."
        )
    
    db_suggestion = Suggestion(
        title=suggestion_data.title,
        description=suggestion_data.description,
        status=suggestion_data.status or "pending",
        user_id=user.id
    )
    
    db.add(db_suggestion)
    await db.commit()
    await db.refresh(db_suggestion)
    
    # Load relationships for response
    result = await db.execute(
        select(Suggestion)
        .options(
            selectinload(Suggestion.user),
            selectinload(Suggestion.comments).selectinload(SuggestionComment.user),
            selectinload(Suggestion.comments).selectinload(SuggestionComment.replies),
            selectinload(Suggestion.votes).selectinload(SuggestionVote.user)
        )
        .where(Suggestion.id == db_suggestion.id)
    )
    
    return result.scalar_one()


async def get_suggestions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    user_id_filter: Optional[UUID] = None
) -> List[Suggestion]:
    """
    Get all suggestions with optional filtering.
    """
    query = select(Suggestion).options(
        selectinload(Suggestion.user),
        selectinload(Suggestion.comments).selectinload(SuggestionComment.user),
        selectinload(Suggestion.comments).selectinload(SuggestionComment.replies).selectinload(SuggestionComment.user),
        selectinload(Suggestion.votes).selectinload(SuggestionVote.user)
    )
    
    # Apply filters
    if status_filter:
        query = query.where(Suggestion.status == status_filter)
    
    if user_id_filter:
        query = query.where(Suggestion.user_id == user_id_filter)
    
    # Order by creation date (newest first)
    query = query.order_by(Suggestion.created_at.desc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_suggestion_by_id(db: AsyncSession, suggestion_id: UUID) -> Optional[Suggestion]:
    """
    Get a suggestion by ID with all relationships loaded.
    """
    result = await db.execute(
        select(Suggestion)
        .options(
            selectinload(Suggestion.user),
            selectinload(Suggestion.comments).selectinload(SuggestionComment.user),
            selectinload(Suggestion.comments).selectinload(SuggestionComment.replies).selectinload(SuggestionComment.user),
            selectinload(Suggestion.votes).selectinload(SuggestionVote.user)
        )
        .where(Suggestion.id == suggestion_id)
    )
    
    return result.scalar_one_or_none()


async def get_user_suggestions(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[Suggestion]:
    """
    Get suggestions created by a specific user.
    """
    return await get_suggestions(
        db=db,
        skip=skip,
        limit=limit,
        user_id_filter=user_id
    )


async def update_suggestion(
    db: AsyncSession,
    suggestion_id: UUID,
    suggestion_update: SuggestionUpdate,
    user: User
) -> Suggestion:
    """
    Update a suggestion (only by the creator or admin).
    """
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    # Only the creator can update their suggestion
    # (You might want to add admin role check here)
    if suggestion.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own suggestions"
        )
    
    # Update fields if provided
    update_data = suggestion_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(suggestion, field, value)
    
    await db.commit()
    await db.refresh(suggestion)
    
    return await get_suggestion_by_id(db, suggestion_id)


async def delete_suggestion(
    db: AsyncSession,
    suggestion_id: UUID,
    user: User
) -> bool:
    """
    Delete a suggestion (only by the creator or admin).
    """
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    # Only the creator can delete their suggestion
    # (You might want to add admin role check here)
    if suggestion.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own suggestions"
        )
    
    await db.delete(suggestion)
    await db.commit()
    
    return True


# ================== SUGGESTION COMMENT CRUD ==================

async def create_comment(
    db: AsyncSession,
    suggestion_id: UUID,
    comment_data: SuggestionCommentBase,
    user: User
) -> SuggestionComment:
    """
    Create a comment on a suggestion.
    Rules: All users can comment except the creator (who can only reply to existing comments).
    """
    # Get the suggestion
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    # Check if this is a top-level comment or a reply
    if comment_data.parent_comment_id is None:
        # Top-level comment - creator cannot create these
        if suggestion.user_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Suggestion creators cannot create top-level comments on their own suggestions"
            )
    else:
        # Reply to existing comment - check if parent exists
        parent_comment = await get_comment_by_id(db, comment_data.parent_comment_id)
        if not parent_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found"
            )
        
        # Verify parent comment belongs to this suggestion
        if parent_comment.suggestion_id != suggestion_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent comment does not belong to this suggestion"
            )
    
    db_comment = SuggestionComment(
        suggestion_id=suggestion_id,
        user_id=user.id,
        content=comment_data.content,
        parent_comment_id=comment_data.parent_comment_id
    )
    
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    
    # Load relationships for response
    return await get_comment_by_id(db, db_comment.id)


async def get_comment_by_id(db: AsyncSession, comment_id: UUID) -> Optional[SuggestionComment]:
    """
    Get a comment by ID with relationships loaded.
    """
    result = await db.execute(
        select(SuggestionComment)
        .options(
            selectinload(SuggestionComment.user),
            selectinload(SuggestionComment.replies).selectinload(SuggestionComment.user)
        )
        .where(SuggestionComment.id == comment_id)
    )
    
    return result.scalar_one_or_none()


async def get_suggestion_comments(
    db: AsyncSession,
    suggestion_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[SuggestionComment]:
    """
    Get comments for a suggestion (only top-level comments, replies are loaded via relationships).
    """
    result = await db.execute(
        select(SuggestionComment)
        .options(
            selectinload(SuggestionComment.user),
            selectinload(SuggestionComment.replies).selectinload(SuggestionComment.user)
        )
        .where(
            and_(
                SuggestionComment.suggestion_id == suggestion_id,
                SuggestionComment.parent_comment_id.is_(None)
            )
        )
        .order_by(SuggestionComment.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    
    return result.scalars().all()


async def delete_comment(
    db: AsyncSession,
    comment_id: UUID,
    user: User
) -> bool:
    """
    Delete a comment (only by the creator or admin).
    """
    comment = await get_comment_by_id(db, comment_id)
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only the creator can delete their comment
    # (You might want to add admin role check here)
    if comment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )
    
    await db.delete(comment)
    await db.commit()
    
    return True


# ================== SUGGESTION VOTE CRUD ==================

async def toggle_vote(
    db: AsyncSession,
    suggestion_id: UUID,
    user: User
) -> dict:
    """
    Toggle vote on a suggestion (add if not exists, remove if exists).
    Rules: All users can vote except the creator.
    """
    # Get the suggestion
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    # Creator cannot vote on their own suggestion
    if suggestion.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot vote on your own suggestion"
        )
    
    # Check if user has already voted
    result = await db.execute(
        select(SuggestionVote).where(
            and_(
                SuggestionVote.user_id == user.id,
                SuggestionVote.suggestion_id == suggestion_id
            )
        )
    )
    existing_vote = result.scalar_one_or_none()
    
    if existing_vote:
        # Remove vote
        await db.delete(existing_vote)
        await db.commit()
        action = "removed"
    else:
        # Add vote
        db_vote = SuggestionVote(
            user_id=user.id,
            suggestion_id=suggestion_id
        )
        db.add(db_vote)
        await db.commit()
        action = "added"
    
    # Get updated vote count
    vote_count = await get_suggestion_vote_count(db, suggestion_id)
    
    return {
        "action": action,
        "vote_count": vote_count,
        "user_voted": action == "added"
    }


async def get_suggestion_vote_count(db: AsyncSession, suggestion_id: UUID) -> int:
    """
    Get the total vote count for a suggestion.
    """
    result = await db.execute(
        select(func.count(SuggestionVote.id)).where(
            SuggestionVote.suggestion_id == suggestion_id
        )
    )
    
    return result.scalar() or 0


async def check_user_voted(
    db: AsyncSession,
    suggestion_id: UUID,
    user_id: UUID
) -> bool:
    """
    Check if a user has voted on a suggestion.
    """
    result = await db.execute(
        select(SuggestionVote).where(
            and_(
                SuggestionVote.user_id == user_id,
                SuggestionVote.suggestion_id == suggestion_id
            )
        )
    )
    
    return result.scalar_one_or_none() is not None


async def get_user_votes(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[SuggestionVote]:
    """
    Get all votes by a user.
    """
    result = await db.execute(
        select(SuggestionVote)
        .options(
            selectinload(SuggestionVote.suggestion).selectinload(Suggestion.user),
            selectinload(SuggestionVote.user)
        )
        .where(SuggestionVote.user_id == user_id)
        .order_by(SuggestionVote.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    return result.scalars().all()


# ================== UTILITY FUNCTIONS ==================

async def get_suggestion_stats(db: AsyncSession, suggestion_id: UUID) -> dict:
    """
    Get comprehensive stats for a suggestion.
    """
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    # Get vote count
    vote_count = await get_suggestion_vote_count(db, suggestion_id)
    
    # Get comment count (including replies)
    result = await db.execute(
        select(func.count(SuggestionComment.id)).where(
            SuggestionComment.suggestion_id == suggestion_id
        )
    )
    comment_count = result.scalar() or 0
    
    return {
        "id": suggestion_id,
        "title": suggestion.title,
        "status": suggestion.status,
        "vote_count": vote_count,
        "comment_count": comment_count,
        "created_at": suggestion.created_at,
        "updated_at": suggestion.updated_at
    }


async def get_user_suggestion_summary(db: AsyncSession, user_id: UUID) -> dict:
    """
    Get summary of user's suggestion activity.
    """
    # Count user's suggestions
    result = await db.execute(
        select(func.count(Suggestion.id)).where(Suggestion.user_id == user_id)
    )
    suggestion_count = result.scalar() or 0
    
    # Count user's votes
    result = await db.execute(
        select(func.count(SuggestionVote.id)).where(SuggestionVote.user_id == user_id)
    )
    vote_count = result.scalar() or 0
    
    # Count user's comments
    result = await db.execute(
        select(func.count(SuggestionComment.id)).where(SuggestionComment.user_id == user_id)
    )
    comment_count = result.scalar() or 0
    
    return {
        "user_id": user_id,
        "suggestions_created": suggestion_count,
        "remaining_suggestions": max(0, 3 - suggestion_count),
        "votes_cast": vote_count,
        "comments_made": comment_count
    }