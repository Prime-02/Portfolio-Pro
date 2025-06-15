from typing import List, Optional, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

# Import your dependencies and schemas
from app.database import get_db
from app.core.security import get_current_user, oauth2_scheme
from app.models.db_models import User, Suggestion, SuggestionComment, SuggestionVote
from app.models.schemas import (
    SuggestionBase, 
    SuggestionResponse, 
    SuggestionUpdate,
    SuggestionCommentBase,
    SuggestionCommentResponse,
    SuggestionVoteResponse
)
from app.core.sugestions import (
    create_suggestion,
    get_suggestions,
    get_suggestion_by_id,
    get_user_suggestions,
    update_suggestion,
    delete_suggestion,
    create_comment,
    get_suggestion_comments,
    delete_comment,
    toggle_vote,
    get_suggestion_vote_count,
    check_user_voted,
    get_user_votes,
    get_suggestion_stats,
    get_user_suggestion_summary
)

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

# ================== SUGGESTION ENDPOINTS ==================

@router.post("/", response_model=SuggestionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_suggestion(
    suggestion_data: SuggestionBase,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Create a new suggestion.
    
    - **Maximum 3 suggestions per user**
    - **title**: Suggestion title (max 200 chars)
    - **description**: Detailed description
    - **status**: Optional status (defaults to 'pending')
    """
    return await create_suggestion(db, suggestion_data, current_user)


@router.get("/", response_model=List[SuggestionResponse])
async def get_all_suggestions(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0, description="Number of suggestions to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of suggestions to return"),
    status: Optional[str] = Query(None, description="Filter by status (pending/approved/rejected/implemented)"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID")
):
    """
    Get all suggestions with optional filtering.
    
    - **All users can view suggestions**
    - **Supports pagination and filtering**
    """
    return await get_suggestions(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=status,
        user_id_filter=user_id
    )


@router.get("/me", response_model=List[SuggestionResponse])
async def get_my_suggestions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Get current user's suggestions.
    """
    return await get_user_suggestions(db, UUID(str(current_user.id)), skip, limit)


@router.get("/me/summary")
async def get_my_suggestion_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get current user's suggestion activity summary.
    
    Returns:
    - Number of suggestions created
    - Remaining suggestion slots (out of 3)
    - Number of votes cast
    - Number of comments made
    """
    return await get_user_suggestion_summary(db, UUID(str(current_user.id)))


@router.get("/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get a specific suggestion by ID.
    
    - **Includes all comments, votes, and user information**
    """
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    return suggestion


@router.put("/{suggestion_id}", response_model=SuggestionResponse)
async def update_existing_suggestion(
    suggestion_id: UUID,
    suggestion_update: SuggestionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Update a suggestion.
    
    - **Only the creator can update their suggestion**
    """
    return await update_suggestion(db, suggestion_id, suggestion_update, current_user)


@router.delete("/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_suggestion(
    suggestion_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Delete a suggestion.
    
    - **Only the creator can delete their suggestion**
    - **Frees up a suggestion slot for the user**
    """
    await delete_suggestion(db, suggestion_id, current_user)


@router.get("/{suggestion_id}/stats")
async def get_suggestion_statistics(
    suggestion_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get comprehensive statistics for a suggestion.
    
    Returns:
    - Vote count
    - Comment count
    - Creation and update timestamps
    """
    return await get_suggestion_stats(db, suggestion_id)


# ================== COMMENT ENDPOINTS ==================

@router.post("/{suggestion_id}/comments", response_model=SuggestionCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_suggestion_comment(
    suggestion_id: UUID,
    comment_data: SuggestionCommentBase,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Create a comment on a suggestion.
    
    **Business Rules:**
    - All users can create top-level comments EXCEPT the suggestion creator
    - Suggestion creators can ONLY reply to existing comments
    - Use `parent_comment_id` to reply to a specific comment
    """
    return await create_comment(db, suggestion_id, comment_data, current_user)


@router.get("/{suggestion_id}/comments", response_model=List[SuggestionCommentResponse])
async def get_suggestion_comments_list(
    suggestion_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Get comments for a suggestion.
    
    - **Returns only top-level comments**
    - **Replies are included in the `replies` field of each comment**
    """
    return await get_suggestion_comments(db, suggestion_id, skip, limit)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suggestion_comment(
    comment_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Delete a comment.
    
    - **Only the comment creator can delete their comment**
    """
    await delete_comment(db, comment_id, current_user)


# ================== VOTE ENDPOINTS ==================

@router.post("/{suggestion_id}/vote")
async def toggle_suggestion_vote(
    suggestion_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Toggle vote on a suggestion (add if not voted, remove if already voted).
    
    **Business Rules:**
    - All users can vote EXCEPT the suggestion creator
    - Returns the action taken and updated vote count
    
    Returns:
    - **action**: "added" or "removed"
    - **vote_count**: Total votes for the suggestion
    - **user_voted**: Whether the current user has voted
    """
    return await toggle_vote(db, suggestion_id, current_user)


@router.get("/{suggestion_id}/votes/count")
async def get_vote_count(
    suggestion_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get the total vote count for a suggestion.
    """
    vote_count = await get_suggestion_vote_count(db, suggestion_id)
    return {"suggestion_id": suggestion_id, "vote_count": vote_count}


@router.get("/{suggestion_id}/votes/check")
async def check_my_vote(
    suggestion_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Check if the current user has voted on a suggestion.
    """
    has_voted = await check_user_voted(db, suggestion_id, UUID(str(current_user.id)))
    return {"suggestion_id": suggestion_id, "user_voted": has_voted}


@router.get("/votes/me", response_model=List[SuggestionVoteResponse])
async def get_my_votes(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Get all votes cast by the current user.
    
    - **Includes the suggestion details for each vote**
    """
    return await get_user_votes(db, UUID(str(current_user.id)), skip, limit)


# ================== ADMIN/MANAGEMENT ENDPOINTS ==================

@router.get("/users/{user_id}/summary")
async def get_user_activity_summary(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    # Add admin role check here if needed
    # admin_user: Annotated[User, Depends(get_admin_user)]
):
    """
    Get activity summary for any user (admin endpoint).
    
    **Note**: Add admin authentication if needed
    """
    return await get_user_suggestion_summary(db, user_id)


@router.get("/users/{user_id}", response_model=List[SuggestionResponse])
async def get_user_suggestions_by_id(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Get suggestions by a specific user (public endpoint).
    """
    return await get_user_suggestions(db, user_id, skip, limit)


# ================== BULK OPERATIONS ==================

@router.get("/stats/overview")
async def get_suggestions_overview(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get overall statistics for the suggestion system.
    """
    from sqlalchemy import func, select
    from models.db_models import Suggestion, SuggestionComment, SuggestionVote
    
    # Get total suggestions by status
    result = await db.execute(
        select(Suggestion.status, func.count(Suggestion.id))
        .group_by(Suggestion.status)
    )
    status_counts = {status: count for status, count in result.fetchall()}
    
    # Get total comments
    result = await db.execute(select(func.count(SuggestionComment.id)))
    total_comments = result.scalar() or 0
    
    # Get total votes
    result = await db.execute(select(func.count(SuggestionVote.id)))
    total_votes = result.scalar() or 0
    
    # Get total suggestions
    total_suggestions = sum(status_counts.values())
    
    return {
        "total_suggestions": total_suggestions,
        "suggestions_by_status": status_counts,
        "total_comments": total_comments,
        "total_votes": total_votes
    }


@router.patch("/{suggestion_id}/status")
async def update_suggestion_status(
    current_user: Annotated[User, Depends(get_current_user)],
    suggestion_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    new_status: str = Query(..., regex="^(pending|approved|rejected|implemented)$")
    # Add admin role check here: admin_user: Annotated[User, Depends(get_admin_user)]
):
    """
    Update suggestion status (admin endpoint).
    
    **Valid statuses**: pending, approved, rejected, implemented
    **Note**: Add admin authentication if needed
    """
    suggestion_update = SuggestionUpdate(status=new_status)
    return await update_suggestion(db, suggestion_id, suggestion_update, current_user)


# ================== SEARCH ENDPOINTS ==================

@router.get("/search/")
async def search_suggestions(
    q: str = Query(..., min_length=3, description="Search query (minimum 3 characters)"),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(pending|approved|rejected|implemented)$")
):
    """
    Search suggestions by title and description.
    
    - **q**: Search query (searches in title and description)
    - **status**: Optional status filter
    """
    from sqlalchemy import or_, and_, select
    from sqlalchemy.orm import selectinload
    
    
    query = select(Suggestion).options(
        selectinload(Suggestion.user),
        selectinload(Suggestion.comments).selectinload(SuggestionComment.user),
        selectinload(Suggestion.votes).selectinload(SuggestionVote.user)
    )
    
    # Add search filter
    search_filter = or_(
        Suggestion.title.ilike(f"%{q}%"),
        Suggestion.description.ilike(f"%{q}%")
    )
    
    if status:
        search_filter = and_(search_filter, Suggestion.status == status)
    
    query = query.where(search_filter).order_by(
        Suggestion.created_at.desc()
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    suggestions = result.scalars().all()
    
    return {
        "query": q,
        "status_filter": status,
        "results": suggestions,
        "count": len(suggestions)
    }