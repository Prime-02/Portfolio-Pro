from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List, Dict, Optional, Union
from app.models.schemas import (
    CustomSectionCreate,
    CustomSectionUpdate,
    CustomSectionItemCreate,
    CustomSectionItemUpdate,
    CustomSection,
    CustomSectionItem,
)
from app.core.security import get_db, get_current_user, optional_current_user
from app.models.db_models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import customsection as crud

# Single router with unified prefix
router = APIRouter(
    prefix="/custom-sections",
    tags=["Custom Sections"],
    responses={404: {"description": "Not found"}},
)

# CUSTOM SECTION ENDPOINTS
@router.post("/", response_model=CustomSection, status_code=status.HTTP_201_CREATED)
async def create_section(
    section_data: CustomSectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new custom section"""
    return await crud.create_custom_section(section_data, user, db)

@router.get("/{section_id}", response_model=CustomSection)
async def read_section(
    section_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """Get a specific custom section by ID"""
    return await crud.get_custom_section(section_id, db, current_user)

@router.put("/{section_id}", response_model=CustomSection)
async def update_section(
    section_id: UUID,
    section_update: CustomSectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom section"""
    return await crud.update_custom_section(section_id, section_update, user, db)

@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom section"""
    await crud.delete_custom_section(section_id, user, db)
    return None

@router.get("/{section_id}/with_items", response_model=Dict[str, Union[CustomSection, List[CustomSectionItem], int]])
async def read_section_with_items(
    section_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """Get a section with all its items"""
    return await crud.get_section_with_items(section_id, db, current_user)

# CUSTOM SECTION ITEM ENDPOINTS
@router.post("/{section_id}/items", response_model=CustomSectionItem, status_code=status.HTTP_201_CREATED)
async def create_item(
    section_id: UUID,
    item_data: CustomSectionItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new item in a custom section"""
    # Verify section exists and belongs to user
    section = await crud.get_custom_section(section_id, db, user)
    if section.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add items to your own sections",
        )
    return await crud.create_section_item(item_data, user, db)

@router.get("/{section_id}/items", response_model=List[CustomSectionItem])
async def read_items(
    section_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """Get all items for a section"""
    return await crud.get_section_items(section_id, db, current_user)

# ITEM-SPECIFIC ENDPOINTS
@router.get("/items/{item_id}", response_model=CustomSectionItem)
async def read_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """Get a specific section item by ID"""
    return await crud.get_section_item(item_id, db, current_user)

@router.put("/items/{item_id}", response_model=CustomSectionItem)
async def update_item(
    item_id: UUID,
    item_update: CustomSectionItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a section item"""
    return await crud.update_section_item(item_id, item_update, user, db)

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a section item"""
    await crud.delete_section_item(item_id, user, db)
    return None

# USER-SPECIFIC ENDPOINTS
@router.get("/users/{user_id}/sections", response_model=List[CustomSection])
async def read_user_sections(
    user_id: UUID,
    include_hidden: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """Get all custom sections for a user"""
    return await crud.get_user_custom_sections(user_id, include_hidden, db, current_user)

@router.post("/users/{user_id}/reorder_sections", response_model=List[CustomSection])
async def reorder_user_sections(
    user_id: UUID,
    section_orders: List[Dict[str, Union[UUID, int]]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder multiple sections at once"""
    return await crud.reorder_sections(user_id, section_orders, user, db)

@router.get("/users/{user_id}/sections_with_items", response_model=List[Dict[str, Union[CustomSection, List[CustomSectionItem], int]]])
async def read_user_sections_with_items(
    user_id: UUID,
    include_hidden: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """Get all sections for a user with their items"""
    return await crud.get_user_sections_with_items(user_id, include_hidden, db, current_user)

@router.get("/users/{user_id}/search_items", response_model=List[CustomSectionItem])
async def search_items(
    user_id: UUID,
    query: str,
    section_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
):
    """Search items within a user's sections"""
    return await crud.search_section_items(user_id, query, section_type, db, current_user)


@router.get("/users/{user_id}/section_stats", response_model=Dict[str, Union[int, Dict[str, int]]])
async def get_user_section_stats(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get statistics about a user's sections"""
    return await crud.get_section_stats(user_id, db)