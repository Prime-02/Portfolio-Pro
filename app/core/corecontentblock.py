from app.models.schemas import ContentBlockBase, ContentBlockCreate, ContentBlockUpdate
from app.models.db_models import User, ContentBlock
from typing import Dict, Union, List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.database import get_db
from sqlalchemy.future import select
from sqlalchemy import func, or_
from uuid import UUID


async def get_common_params(
    data: Dict[str, Union[str, bool, int]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"data": data, "user": user, "db": db}


async def add_content_block(commons: dict = Depends(get_common_params)) -> ContentBlockCreate:
    """Create a new content block"""
    content_block_data = commons["data"]
    user = commons["user"]
    db: AsyncSession = commons["db"]

    if not content_block_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No content block data provided",
        )

    if "block_type" not in content_block_data or "content" not in content_block_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block type and content are required",
        )

    # Check if position is provided, if not, get the next available position
    position = content_block_data.get("position")
    if position is None:
        max_position_result = await db.execute(
            select(func.max(ContentBlock.position))
            .where(ContentBlock.user_id == user.id)
            .where(ContentBlock.block_type == str(content_block_data["block_type"]))
        )
        max_position = max_position_result.scalar() or 0
        position = max_position + 1

    # Check for duplicate position within the same block_type for the user
    existing_block = await db.execute(
        select(ContentBlock)
        .where(ContentBlock.user_id == user.id)
        .where(ContentBlock.block_type == str(content_block_data["block_type"]))
        .where(ContentBlock.position == position)
    )
    if existing_block.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content block with position {position} already exists for this block type",
        )

    new_content_block = ContentBlock(
        user_id=user.id,
        block_type=content_block_data["block_type"],
        title=content_block_data.get("title"),
        content=content_block_data["content"],
        position=position,
        is_visible=content_block_data.get("is_visible", False),
    )

    db.add(new_content_block)
    await db.commit()
    await db.refresh(new_content_block)

    return ContentBlockCreate(
        user_id=user.id,
        block_type=content_block_data["block_type"],
        title=content_block_data.get("title"),
        content=content_block_data["content"],
        position=position,
        is_visible=content_block_data.get("is_visible", False),
    )


async def get_all_content_blocks(
    user: User, 
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    block_type: Optional[str] = None,
    is_visible: Optional[bool] = None
) -> Dict[str, Union[List[ContentBlockBase], int]]:
    """Get all content blocks for the current user with pagination"""
    
    # Build query with optional filters
    query = select(ContentBlock).where(ContentBlock.user_id == user.id)
    count_query = select(func.count(ContentBlock.id)).where(ContentBlock.user_id == user.id)
    
    if block_type:
        query = query.where(ContentBlock.block_type == block_type)
        count_query = count_query.where(ContentBlock.block_type == block_type)
    
    if is_visible is not None:
        query = query.where(ContentBlock.is_visible == is_visible)
        count_query = count_query.where(ContentBlock.is_visible == is_visible)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query
        .offset(skip)
        .limit(limit)
        .order_by(ContentBlock.block_type, ContentBlock.position)
    )
    content_blocks = result.scalars().all()

    return {
        "content_blocks": [
            ContentBlockBase(
                block_type=cb.block_type,
                title=cb.title,
                content=cb.content,
                position=cb.position,
                is_visible=cb.is_visible
            ) for cb in content_blocks
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


async def get_all_content_blocks_public(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    block_type: Optional[str] = None,
    is_visible: Optional[bool] = None,
    user_id: Optional[UUID] = None
) -> Dict[str, Union[List[ContentBlockBase], int]]:
    """Get all content blocks (public access) with filtering and pagination"""
    
    # Build query with optional filters
    query = select(ContentBlock)
    count_query = select(func.count(ContentBlock.id))
    
    if user_id:
        query = query.where(ContentBlock.user_id == user_id)
        count_query = count_query.where(ContentBlock.user_id == user_id)
    
    if block_type:
        query = query.where(ContentBlock.block_type == block_type)
        count_query = count_query.where(ContentBlock.block_type == block_type)
    
    if is_visible is not None:
        query = query.where(ContentBlock.is_visible == is_visible)
        count_query = count_query.where(ContentBlock.is_visible == is_visible)
    else:
        # By default, only show visible content blocks for public access
        query = query.where(ContentBlock.is_visible == True)
        count_query = count_query.where(ContentBlock.is_visible == True)
    
    # Get total count with filters
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query
        .offset(skip)
        .limit(limit)
        .order_by(ContentBlock.block_type, ContentBlock.position)
    )
    content_blocks = result.scalars().all()

    return {
        "content_blocks": [
            ContentBlockBase(
                block_type=cb.block_type,
                title=cb.title,
                content=cb.content,
                position=cb.position,
                is_visible=cb.is_visible
            ) for cb in content_blocks
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


async def get_content_block_by_id(
    content_block_id: UUID,
    user: User,
    db: AsyncSession
) -> ContentBlockBase:
    """Get a specific content block by ID (must belong to current user)"""
    
    result = await db.execute(
        select(ContentBlock)
        .where(ContentBlock.id == content_block_id)
        .where(ContentBlock.user_id == user.id)
    )
    content_block = result.scalar_one_or_none()
    
    if not content_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content block not found"
        )
    
    return ContentBlockBase(
        block_type=content_block.block_type,
        title=content_block.title,
        content=content_block.content,
        position=content_block.position,
        is_visible=content_block.is_visible
    )


async def get_content_block_by_id_public(
    content_block_id: UUID,
    db: AsyncSession
) -> ContentBlockBase:
    """Get a specific content block by ID (public access)"""
    
    result = await db.execute(
        select(ContentBlock).where(ContentBlock.id == content_block_id)
    )
    content_block = result.scalar_one_or_none()
    
    if not content_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content block not found"
        )
    
    return ContentBlockBase(
        block_type=content_block.block_type,
        title=content_block.title,
        content=content_block.content,
        position=content_block.position,
        is_visible=content_block.is_visible
    )


async def update_content_block(
    content_block_id: UUID,
    content_block_data: Dict[str, Union[str, bool, int]],
    user: User,
    db: AsyncSession
) -> ContentBlockBase:
    """Update a content block record"""
    
    # Get existing content block
    result = await db.execute(
        select(ContentBlock)
        .where(ContentBlock.id == content_block_id)
        .where(ContentBlock.user_id == user.id)
    )
    content_block = result.scalar_one_or_none()
    
    if not content_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content block not found"
        )
    
    # Check for duplicate position if position is being updated
    if "position" in content_block_data:
        new_position = content_block_data["position"]
        new_block_type = content_block_data.get("block_type", content_block.block_type)
        
        # Only check for duplicates if position or block_type is actually changing
        if new_position != content_block.position or new_block_type != content_block.block_type:
            existing_check = await db.execute(
                select(ContentBlock)
                .where(ContentBlock.user_id == user.id)
                .where(ContentBlock.block_type == str(new_block_type))
                .where(ContentBlock.position == new_position)
                .where(ContentBlock.id != content_block_id)
            )
            if existing_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Content block with position {new_position} already exists for this block type"
                )
    
    # Update fields
    for field, value in content_block_data.items():
        if hasattr(content_block, field):
            setattr(content_block, field, value)
    
    await db.commit()
    await db.refresh(content_block)
    
    return ContentBlockBase(
        block_type=content_block.block_type,
        title=content_block.title,
        content=content_block.content,
        position=content_block.position,
        is_visible=content_block.is_visible
    )


async def delete_content_block(
    content_block_id: UUID,
    user: User,
    db: AsyncSession
) -> Dict[str, str]:
    """Delete a content block record"""
    
    result = await db.execute(
        select(ContentBlock)
        .where(ContentBlock.id == content_block_id)
        .where(ContentBlock.user_id == user.id)
    )
    content_block = result.scalar_one_or_none()
    
    if not content_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content block not found"
        )
    
    await db.delete(content_block)
    await db.commit()
    
    return {"message": "Content block deleted successfully"}


async def get_content_blocks_by_user_id(
    user_id: UUID,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    block_type: Optional[str] = None,
    is_visible: Optional[bool] = None
) -> Dict[str, Union[List[ContentBlockBase], int]]:
    """Get all content blocks for a specific user (public access)"""
    
    # Build query with optional filters
    query = select(ContentBlock).where(ContentBlock.user_id == user_id)
    count_query = select(func.count(ContentBlock.id)).where(ContentBlock.user_id == user_id)
    
    if block_type:
        query = query.where(ContentBlock.block_type == block_type)
        count_query = count_query.where(ContentBlock.block_type == block_type)
    
    if is_visible is not None:
        query = query.where(ContentBlock.is_visible == is_visible)
        count_query = count_query.where(ContentBlock.is_visible == is_visible)
    else:
        # By default, only show visible content blocks for public access
        query = query.where(ContentBlock.is_visible == True)
        count_query = count_query.where(ContentBlock.is_visible == True)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get paginated results
    result = await db.execute(
        query
        .offset(skip)
        .limit(limit)
        .order_by(ContentBlock.block_type, ContentBlock.position)
    )
    content_blocks = result.scalars().all()

    return {
        "content_blocks": [
            ContentBlockBase(
                block_type=cb.block_type,
                title=cb.title,
                content=cb.content,
                position=cb.position,
                is_visible=cb.is_visible
            ) for cb in content_blocks
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


async def reorder_content_blocks(
    block_type: str,
    block_positions: List[Dict[str, Union[UUID, int]]],
    user: User,
    db: AsyncSession
) -> Dict[str, str]:
    """Reorder content blocks within a block type"""
    
    # Validate that all blocks belong to the user and are of the correct type
    block_ids = [item["id"] for item in block_positions]
    
    result = await db.execute(
        select(ContentBlock)
        .where(ContentBlock.id.in_(block_ids))
        .where(ContentBlock.user_id == user.id)
        .where(ContentBlock.block_type == block_type)
    )
    existing_blocks = result.scalars().all()
    
    if len(existing_blocks) != len(block_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more content blocks not found or don't belong to you"
        )
    
    # Update positions
    for item in block_positions:
        block_id = item["id"]
        new_position = item["position"]
        
        for block in existing_blocks:
            if block.id == block_id:
                block.position = new_position
                break
    
    await db.commit()
    
    return {"message": f"Content blocks reordered successfully for {block_type}"}


async def toggle_visibility(
    content_block_id: UUID,
    user: User,
    db: AsyncSession
) -> ContentBlockBase:
    """Toggle the visibility of a content block"""
    
    result = await db.execute(
        select(ContentBlock)
        .where(ContentBlock.id == content_block_id)
        .where(ContentBlock.user_id == user.id)
    )
    content_block = result.scalar_one_or_none()
    
    if not content_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content block not found"
        )
    
    content_block.is_visible = not content_block.is_visible
    await db.commit()
    await db.refresh(content_block)
    
    return ContentBlockBase(
        block_type=content_block.block_type,
        title=content_block.title,
        content=content_block.content,
        position=content_block.position,
        is_visible=content_block.is_visible
    )