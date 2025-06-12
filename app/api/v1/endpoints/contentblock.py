from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, Union, List, Optional
from uuid import UUID
from app.models.schemas import ContentBlockBase, ContentBlockCreate, ContentBlockUpdate
from app.models.db_models import User
from app.core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.corecontentblock import (
    add_content_block,
    get_all_content_blocks,
    get_all_content_blocks_public,
    get_content_block_by_id,
    get_content_block_by_id_public,
    update_content_block,
    delete_content_block,
    get_content_blocks_by_user_id,
    get_common_params,
    reorder_content_blocks,
    toggle_visibility
)

router = APIRouter(prefix="/content-blocks", tags=["content-blocks"])


@router.post(
    "/",
    response_model=ContentBlockCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new content block",
    description="Create a new content block for the authenticated user"
)
async def create_content_block(
    content_block_data: ContentBlockCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new content block"""
    data_dict = content_block_data.model_dump(exclude={"user_id"})  # Exclude user_id from input
    commons = await get_common_params(data_dict, user, db)
    return await add_content_block(commons)


@router.get(
    "/me",
    response_model=Dict[str, Union[List[ContentBlockBase], int]],
    summary="Get current user's content blocks",
    description="Get all content blocks for the authenticated user with pagination and filtering"
)
async def get_my_content_blocks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    block_type: Optional[str] = Query(None, description="Filter by block type"),
    is_visible: Optional[bool] = Query(None, description="Filter by visibility status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all content blocks for the current user"""
    return await get_all_content_blocks(user, db, skip, limit, block_type, is_visible)


@router.get(
    "/public",
    response_model=Dict[str, Union[List[ContentBlockBase], int]],
    summary="Get all content blocks (public)",
    description="Get all visible content blocks with optional filtering and pagination"
)
async def get_all_content_blocks_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    block_type: Optional[str] = Query(None, description="Filter by block type"),
    is_visible: Optional[bool] = Query(None, description="Filter by visibility status"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get all content blocks with filtering and pagination"""
    return await get_all_content_blocks_public(
        db, skip, limit, block_type, is_visible, user_id
    )


@router.get(
    "/user/{user_id}",
    response_model=Dict[str, Union[List[ContentBlockBase], int]],
    summary="Get content blocks by user ID",
    description="Get all visible content blocks for a specific user"
)
async def get_user_content_blocks(
    user_id: UUID = Path(..., description="User ID to get content blocks for"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    block_type: Optional[str] = Query(None, description="Filter by block type"),
    is_visible: Optional[bool] = Query(None, description="Filter by visibility status"),
    db: AsyncSession = Depends(get_db)
):
    """Get all content blocks for a specific user"""
    return await get_content_blocks_by_user_id(user_id, db, skip, limit, block_type, is_visible)


@router.get(
    "/me/{content_block_id}",
    response_model=ContentBlockBase,
    summary="Get specific content block (owner)",
    description="Get a specific content block that belongs to the authenticated user"
)
async def get_my_content_block_by_id(
    content_block_id: UUID = Path(..., description="Content block ID"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific content block for the current user"""
    return await get_content_block_by_id(content_block_id, user, db)


@router.get(
    "/{content_block_id}",
    response_model=ContentBlockBase,
    summary="Get specific content block (public)",
    description="Get a specific content block by ID"
)
async def get_content_block_by_id_endpoint(
    content_block_id: UUID = Path(..., description="Content block ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific content block by ID"""
    return await get_content_block_by_id_public(content_block_id, db)


@router.put(
    "/{content_block_id}",
    response_model=ContentBlockBase,
    summary="Update content block",
    description="Update an existing content block"
)
async def update_content_block_endpoint(
    content_block_data: ContentBlockUpdate,
    content_block_id: UUID = Path(..., description="Content block ID to update"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing content block"""
    # Convert Pydantic model to dict, excluding None values
    update_dict = content_block_data.model_dump(exclude_unset=True, exclude_none=True)
    return await update_content_block(content_block_id, update_dict, user, db)


@router.patch(
    "/{content_block_id}",
    response_model=ContentBlockBase,
    summary="Partially update content block",
    description="Partially update an existing content block"
)
async def patch_content_block_endpoint(
    content_block_data: ContentBlockUpdate,
    content_block_id: UUID = Path(..., description="Content block ID to update"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Partially update an existing content block"""
    # Convert Pydantic model to dict, excluding None values for partial updates
    update_dict = content_block_data.model_dump(exclude_unset=True, exclude_none=True)
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update"
        )
    
    return await update_content_block(content_block_id, update_dict, user, db)


@router.delete(
    "/{content_block_id}",
    response_model=Dict[str, str],
    summary="Delete content block",
    description="Delete an existing content block"
)
async def delete_content_block_endpoint(
    content_block_id: UUID = Path(..., description="Content block ID to delete"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an existing content block"""
    return await delete_content_block(content_block_id, user, db)


@router.patch(
    "/{content_block_id}/toggle-visibility",
    response_model=ContentBlockBase,
    summary="Toggle content block visibility",
    description="Toggle the visibility status of a content block"
)
async def toggle_content_block_visibility(
    content_block_id: UUID = Path(..., description="Content block ID"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle the visibility of a content block"""
    return await toggle_visibility(content_block_id, user, db)


# Content Block Type Management

@router.get(
    "/types",
    response_model=List[str],
    summary="Get available content block types",
    description="Get a list of available content block types"
)
async def get_content_block_types():
    """Get available content block types"""
    return ["about", "services", "process", "fun_facts"]


@router.get(
    "/me/by-type/{block_type}",
    response_model=Dict[str, Union[List[ContentBlockBase], int]],
    summary="Get content blocks by type (owner)",
    description="Get all content blocks of a specific type for the authenticated user"
)
async def get_my_content_blocks_by_type(
    block_type: str = Path(..., description="Content block type"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all content blocks of a specific type for the current user"""
    return await get_all_content_blocks(user, db, skip, limit, block_type=block_type)


@router.get(
    "/user/{user_id}/by-type/{block_type}",
    response_model=Dict[str, Union[List[ContentBlockBase], int]],
    summary="Get content blocks by type and user",
    description="Get all visible content blocks of a specific type for a specific user"
)
async def get_user_content_blocks_by_type(
    user_id: UUID = Path(..., description="User ID"),
    block_type: str = Path(..., description="Content block type"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get all visible content blocks of a specific type for a specific user"""
    return await get_content_blocks_by_user_id(user_id, db, skip, limit, block_type=block_type)


# Reordering Endpoints

from pydantic import BaseModel

class ReorderRequest(BaseModel):
    blocks: List[Dict[str, Union[UUID, int]]]

@router.put(
    "/reorder/{block_type}",
    response_model=Dict[str, str],
    summary="Reorder content blocks",
    description="Reorder content blocks within a specific block type"
)
async def reorder_content_blocks_endpoint(
    reorder_data: ReorderRequest,
    block_type: str = Path(..., description="Content block type to reorder"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reorder content blocks within a block type"""
    return await reorder_content_blocks(block_type, reorder_data.blocks, user, db)


# Statistics and Analytics

@router.get(
    "/stats/summary",
    response_model=Dict[str, Union[int, List[Dict[str, Union[str, int]]]]],
    summary="Get content block statistics",
    description="Get summary statistics about content blocks"
)
async def get_content_block_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get content block statistics"""
    from sqlalchemy import func, desc
    from app.models.db_models import ContentBlock
    from sqlalchemy.future import select
    
    # Total count
    total_result = await db.execute(select(func.count(ContentBlock.id)))
    total_count = total_result.scalar()
    
    # Visible count
    visible_result = await db.execute(
        select(func.count(ContentBlock.id)).where(ContentBlock.is_visible == True)
    )
    visible_count = visible_result.scalar()
    
    # Count by block type
    block_type_result = await db.execute(
        select(ContentBlock.block_type, func.count(ContentBlock.id).label('count'))
        .where(ContentBlock.block_type.isnot(None))
        .group_by(ContentBlock.block_type)
        .order_by(desc('count'))
    )
    block_type_stats = [
        {"type": row[0], "count": row[1]} 
        for row in block_type_result.fetchall()
    ]
    
    # Most active users
    user_stats_result = await db.execute(
        select(ContentBlock.user_id, func.count(ContentBlock.id).label('count'))
        .group_by(ContentBlock.user_id)
        .order_by(desc('count'))
        .limit(10)
    )
    user_stats = [
        {"user_id": str(row[0]), "count": row[1]} 
        for row in user_stats_result.fetchall()
    ]
    
    return {
        "total_blocks": total_count,
        "visible_blocks": visible_count,
        "hidden_blocks": total_count - visible_count,
        "blocks_by_type": block_type_stats,
        "top_users": user_stats
    }


# @router.get(
#     "/me/stats",
#     response_model=Dict[str, Union[int, List[Dict[str, Union[str, int]]]]],
#     summary="Get current user's content block statistics",
#     description="Get statistics for the authenticated user's content blocks"
# )
# async def get_my_content