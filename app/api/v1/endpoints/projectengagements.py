from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import (
    ProjectLike,
    ProjectLikeCreate,
    ProjectComment,
    ProjectCommentCreate,
    ProjectCommentUpdate
)
from app.core.projectcore import coreprojectengagements as crud
from app.core.user import get_current_user  # Assuming you have auth dependency
from uuid import UUID

router = APIRouter(prefix="/engagements", tags=["Projects"])

# ===== PROJECT LIKE ENDPOINTS =====

@router.post("/projects/{project_id}/likes", response_model=ProjectLike, status_code=status.HTTP_201_CREATED)
async def create_project_like(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Like a project"""
    like_data = ProjectLikeCreate(project_id=project_id, user_id=current_user.id)
    return await crud.create_project_like(db=db, like_data=like_data)


@router.delete("/projects/{project_id}/likes", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_like(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Unlike a project"""
    await crud.delete_project_like(db=db, project_id=project_id, user_id=current_user.id)
    return {"message": "Like removed successfully"}


@router.post("/projects/{project_id}/likes/toggle")
async def toggle_project_like(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Toggle like status for a project"""
    return await crud.toggle_project_like(db=db, project_id=project_id, user_id=current_user.id)


@router.get("/projects/{project_id}/likes", response_model=List[ProjectLike])
async def get_project_likes(
    project_id: UUID,
    skip: int = Query(0, ge=0, description="Number of likes to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of likes to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get all likes for a specific project"""
    return await crud.get_project_likes(db=db, project_id=project_id, skip=skip, limit=limit)


@router.get("/projects/{project_id}/likes/count")
async def get_project_likes_count(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the total count of likes for a project"""
    count = await crud.get_project_likes_count(db=db, project_id=project_id)
    return {"project_id": project_id, "likes_count": count}


@router.get("/projects/{project_id}/likes/check")
async def check_user_liked_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Check if current user has liked a project"""
    liked = await crud.check_user_liked_project(db=db, project_id=project_id, user_id=current_user.id)
    return {"project_id": project_id, "user_id": current_user.id, "liked": liked}


@router.get("/users/me/likes", response_model=List[ProjectLike])
async def get_my_likes(
    skip: int = Query(0, ge=0, description="Number of likes to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of likes to return"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all likes by the current user"""
    return await crud.get_user_likes(db=db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/users/{user_id}/likes", response_model=List[ProjectLike])
async def get_user_likes(
    user_id: UUID,
    skip: int = Query(0, ge=0, description="Number of likes to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of likes to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get all likes by a specific user"""
    return await crud.get_user_likes(db=db, user_id=user_id, skip=skip, limit=limit)


@router.get("/likes/{like_id}", response_model=ProjectLike)
async def get_project_like(
    like_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project like by ID"""
    like = await crud.get_project_like(db=db, like_id=like_id)
    if not like:
        raise HTTPException(status_code=404, detail="Like not found")
    return like


# ===== PROJECT COMMENT ENDPOINTS =====

@router.post("/projects/{project_id}/comments", response_model=ProjectComment, status_code=status.HTTP_201_CREATED)
async def create_project_comment(
    project_id: UUID,
    comment_data: ProjectCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new comment on a project"""
    # Override the user_id and project_id from the authenticated user and URL
    comment_data.user_id = current_user.id
    comment_data.project_id = project_id
    return await crud.create_project_comment(db=db, comment_data=comment_data)


@router.get("/projects/{project_id}/comments", response_model=List[ProjectComment])
async def get_project_comments(
    project_id: UUID,
    skip: int = Query(0, ge=0, description="Number of comments to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of comments to return"),
    include_replies: bool = Query(True, description="Include replies in the response"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db)
):
    """Get all comments for a specific project"""
    return await crud.get_project_comments(
        db=db, 
        project_id=project_id, 
        skip=skip, 
        limit=limit,
        include_replies=include_replies,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/projects/{project_id}/comments/count")
async def get_project_comments_count(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the total count of comments for a project"""
    count = await crud.get_project_comments_count(db=db, project_id=project_id)
    return {"project_id": project_id, "comments_count": count}


@router.get("/comments/{comment_id}", response_model=ProjectComment)
async def get_project_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific comment by ID"""
    comment = await crud.get_project_comment(db=db, comment_id=comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.get("/comments/{comment_id}/thread", response_model=ProjectComment)
async def get_comment_thread(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a comment with all its nested replies"""
    thread = await crud.get_comment_thread(db=db, comment_id=comment_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Comment not found")
    return thread


@router.get("/comments/{parent_comment_id}/replies", response_model=List[ProjectComment])
async def get_comment_replies(
    parent_comment_id: UUID,
    skip: int = Query(0, ge=0, description="Number of replies to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of replies to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get all replies to a specific comment"""
    return await crud.get_comment_replies(
        db=db, 
        parent_comment_id=parent_comment_id, 
        skip=skip, 
        limit=limit
    )


@router.put("/comments/{comment_id}", response_model=ProjectComment)
async def update_project_comment(
    comment_id: UUID,
    comment_update: ProjectCommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a project comment (only by the author)"""
    return await crud.update_project_comment(
        db=db, 
        comment_id=comment_id, 
        comment_update=comment_update,
        user_id=current_user.id
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a project comment (only by the author)"""
    await crud.delete_project_comment(db=db, comment_id=comment_id, user_id=current_user.id)
    return {"message": "Comment deleted successfully"}


@router.get("/users/me/comments", response_model=List[ProjectComment])
async def get_my_comments(
    skip: int = Query(0, ge=0, description="Number of comments to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of comments to return"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all comments by the current user"""
    return await crud.get_user_comments(db=db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/users/{user_id}/comments", response_model=List[ProjectComment])
async def get_user_comments(
    user_id: UUID,
    skip: int = Query(0, ge=0, description="Number of comments to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of comments to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get all comments by a specific user"""
    return await crud.get_user_comments(db=db, user_id=user_id, skip=skip, limit=limit)


# ===== ENGAGEMENT STATISTICS ENDPOINTS =====

@router.get("/projects/{project_id}/engagement")
async def get_project_engagement_stats(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get engagement statistics for a project"""
    return await crud.get_project_engagement_stats(db=db, project_id=project_id)


@router.get("/users/{user_id}/engagement")
async def get_user_engagement_stats(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get engagement statistics for a user"""
    return await crud.get_user_engagement_stats(db=db, user_id=user_id)


@router.get("/users/me/engagement")
async def get_my_engagement_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get engagement statistics for the current user"""
    return await crud.get_user_engagement_stats(db=db, user_id=current_user.id)


# ===== BATCH OPERATIONS ENDPOINTS =====

@router.get("/projects/batch/engagement")
async def get_multiple_projects_engagement(
    project_ids: List[UUID] = Query(..., description="List of project IDs"),
    db: AsyncSession = Depends(get_db)
):
    """Get engagement statistics for multiple projects"""
    results = []
    for project_id in project_ids[:10]:  # Limit to 10 projects per request
        stats = await crud.get_project_engagement_stats(db=db, project_id=project_id)
        results.append(stats)
    return results


@router.post("/comments/reply/{parent_comment_id}", response_model=ProjectComment, status_code=status.HTTP_201_CREATED)
async def reply_to_comment(
    parent_comment_id: UUID,
    reply_content: dict,  # Expecting {"content": "reply text"}
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a reply to an existing comment"""
    # Get the parent comment to extract project_id
    parent_comment = await crud.get_project_comment(db=db, comment_id=parent_comment_id)
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Parent comment not found")
    
    comment_data = ProjectCommentCreate(
        project_id=UUID(str(parent_comment.project_id)),
        user_id=current_user.id,
        content=reply_content["content"],
        parent_comment_id=parent_comment_id
    )
    
    return await crud.create_project_comment(db=db, comment_data=comment_data)


# ===== ADMIN ENDPOINTS (Optional - for moderation) =====

@router.get("/admin/comments", response_model=List[ProjectComment])
async def get_all_comments_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)  # Add admin check here
):
    """Admin endpoint to get all comments with optional filters"""
    # Add admin role check here
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    if project_id:
        return await crud.get_project_comments(db=db, project_id=project_id, skip=skip, limit=limit)
    elif user_id:
        return await crud.get_user_comments(db=db, user_id=user_id, skip=skip, limit=limit)
    else:
        # Return all comments (implement this in crud if needed)
        return []


@router.delete("/admin/comments/{comment_id}")
async def delete_comment_admin(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)  # Add admin check here
):
    """Admin endpoint to delete any comment"""
    # Add admin role check here
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    comment = await crud.get_project_comment(db=db, comment_id=comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Force delete without user check for admin
    await crud.delete_project_comment(db=db, comment_id=comment_id, user_id=UUID(str(comment.user_id)))
    return {"message": "Comment deleted by admin"}


@router.get("/admin/likes", response_model=List[ProjectLike])
async def get_all_likes_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)  # Add admin check here
):
    """Admin endpoint to get all likes with optional filters"""
    # Add admin role check here
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    if project_id:
        return await crud.get_project_likes(db=db, project_id=project_id, skip=skip, limit=limit)
    elif user_id:
        return await crud.get_user_likes(db=db, user_id=user_id, skip=skip, limit=limit)
    else:
        # Return all likes (implement this in crud if needed)
        return []