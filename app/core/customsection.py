from typing import Dict, Union, List, Optional, cast
from fastapi import HTTPException, status, Depends
from app.core.security import get_current_user, optional_current_user
from app.database import get_db
from app.models.db_models import User, CustomSection, CustomSectionItem
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import (
    CustomSectionBase,
    CustomSectionCreate,
    CustomSectionUpdate,
    CustomSectionItemBase,
    CustomSectionItemCreate,
    CustomSectionItemUpdate,
)
from sqlalchemy.future import select
from sqlalchemy import and_, desc, asc, func
from uuid import UUID


async def create_custom_section(
    section_data: CustomSectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomSection:
    """Create a new custom section for the authenticated user"""

    # Verify user owns the section or is creating for themselves
    if section_data.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create sections for yourself",
        )

    # Check if position is already taken
    existing_section = await db.execute(
        select(CustomSection).where(
            and_(
                CustomSection.user_id == user.id,
                CustomSection.position == section_data.position,
            )
        )
    )
    if existing_section.scalar_one_or_none():
        # Auto-increment positions of existing sections
        await db.execute(
            CustomSection.__table__.update()
            .where(
                and_(
                    CustomSection.user_id == user.id,
                    CustomSection.position >= section_data.position,
                )
            )
            .values(position=CustomSection.position + 1)
        )

    new_section = CustomSection(
        user_id=section_data.user_id,
        section_type=section_data.section_type,
        title=section_data.title,
        description=section_data.description,
        position=section_data.position,
        is_visible=section_data.is_visible,
    )

    db.add(new_section)
    await db.commit()
    await db.refresh(new_section)

    return new_section


async def get_custom_section(
    section_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> CustomSection:
    """Get a custom section by ID"""

    result = await db.execute(
        select(CustomSection).where(CustomSection.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom section not found",
        )

    # If section is not visible, only owner can view it
    if not section.is_visible and (
        not current_user or section.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom section not found",
        )

    return section


async def get_user_custom_sections(
    user_id: UUID,
    include_hidden: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> List[CustomSection]:
    """Get all custom sections for a user"""

    query = select(CustomSection).where(CustomSection.user_id == user_id)

    # Only show hidden sections to the owner
    if not include_hidden or (current_user and current_user.id != user_id):
        query = query.where(CustomSection.is_visible == True)

    query = query.order_by(asc(CustomSection.position))

    result = await db.execute(query)
    return result.scalars().all()


async def update_custom_section(
    section_id: UUID,
    section_update: CustomSectionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomSection:
    """Update a custom section (owner only)"""

    # Get the section
    result = await db.execute(
        select(CustomSection).where(CustomSection.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom section not found",
        )

    # Check ownership
    if section.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own sections",
        )

    # Handle position changes
    update_data = section_update.model_dump(exclude_unset=True)

    if "position" in update_data and update_data["position"] != section.position:
        new_position = update_data["position"]
        old_position = section.position

        # Adjust other sections' positions
        if new_position > old_position:
            # Moving down: decrease positions of sections in between
            await db.execute(
                CustomSection.__table__.update()
                .where(
                    and_(
                        CustomSection.user_id == user.id,
                        CustomSection.position > old_position,
                        CustomSection.position <= new_position,
                        CustomSection.id != section_id,
                    )
                )
                .values(position=CustomSection.position - 1)
            )
        else:
            # Moving up: increase positions of sections in between
            await db.execute(
                CustomSection.__table__.update()
                .where(
                    and_(
                        CustomSection.user_id == user.id,
                        CustomSection.position >= new_position,
                        CustomSection.position < old_position,
                        CustomSection.id != section_id,
                    )
                )
                .values(position=CustomSection.position + 1)
            )

    # Update the section
    for field, value in update_data.items():
        setattr(section, field, value)

    await db.commit()
    await db.refresh(section)

    return section


async def delete_custom_section(
    section_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a custom section and all its items (owner only)"""

    # Get the section
    result = await db.execute(
        select(CustomSection).where(CustomSection.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom section not found",
        )

    # Check ownership
    if section.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own sections",
        )

    # Delete all items in the section first
    await db.execute(
        CustomSectionItem.__table__.delete().where(
            CustomSectionItem.section_id == section_id
        )
    )

    # Adjust positions of remaining sections
    await db.execute(
        CustomSection.__table__.update()
        .where(
            and_(
                CustomSection.user_id == user.id,
                CustomSection.position > section.position,
            )
        )
        .values(position=CustomSection.position - 1)
    )

    await db.delete(section)
    await db.commit()

    return {"message": "Custom section and all its items deleted successfully"}


async def reorder_sections(
    user_id: UUID,
    section_orders: List[
        Dict[str, Union[UUID, int]]
    ],  # [{"section_id": UUID, "position": int}]
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CustomSection]:
    """Reorder multiple sections at once"""

    if user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reorder your own sections",
        )

    # Validate all sections exist and belong to user
    section_ids = [order["section_id"] for order in section_orders]
    result = await db.execute(
        select(CustomSection).where(
            and_(CustomSection.id.in_(section_ids), CustomSection.user_id == user_id)
        )
    )
    sections = {section.id: section for section in result.scalars().all()}

    if len(sections) != len(section_orders):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some sections not found or don't belong to you",
        )

    # Update positions
    for order in section_orders:
        section = sections[order["section_id"]]
        section.position = order["position"]

    await db.commit()

    # Return updated sections in order
    for section in sections.values():
        await db.refresh(section)

    return sorted(sections.values(), key=lambda x: x.position)


# =============================================================================
# CUSTOM SECTION ITEM CRUD OPERATIONS
# =============================================================================


async def create_section_item(
    item_data: CustomSectionItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomSectionItem:
    """Create a new item in a custom section"""

    # Verify section exists and user owns it
    result = await db.execute(
        select(CustomSection).where(CustomSection.id == item_data.section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom section not found",
        )

    if section.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add items to your own sections",
        )

    new_item = CustomSectionItem(
        section_id=item_data.section_id,
        title=item_data.title,
        subtitle=item_data.subtitle,
        description=item_data.description,
        start_date=item_data.start_date,
        end_date=item_data.end_date,
        is_current=item_data.is_current,
        media_url=item_data.media_url,
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    return new_item


async def get_section_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> CustomSectionItem:
    """Get a section item by ID"""

    result = await db.execute(
        select(CustomSectionItem)
        .join(CustomSection)
        .where(CustomSectionItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section item not found",
        )

    # Check if section is visible (unless owner is viewing)
    if not item.section.is_visible and (
        not current_user or item.section.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section item not found",
        )

    return item


async def get_section_items(
    section_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> List[CustomSectionItem]:
    """Get all items for a section"""

    # Verify section exists and is accessible
    section_result = await db.execute(
        select(CustomSection).where(CustomSection.id == section_id)
    )
    section = section_result.scalar_one_or_none()

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom section not found",
        )

    # Check visibility
    if not section.is_visible and (
        not current_user or section.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom section not found",
        )

    result = await db.execute(
        select(CustomSectionItem)
        .where(CustomSectionItem.section_id == section_id)
        .order_by(desc(CustomSectionItem.start_date), CustomSectionItem.title)
    )

    return result.scalars().all()


async def update_section_item(
    item_id: UUID,
    item_update: CustomSectionItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomSectionItem:
    """Update a section item (section owner only)"""

    # Get the item with section info
    result = await db.execute(
        select(CustomSectionItem)
        .join(CustomSection)
        .where(CustomSectionItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section item not found",
        )

    # Check ownership through section
    if item.section.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update items in your own sections",
        )

    # Update the item
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)

    return item


async def delete_section_item(
    item_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a section item (section owner only)"""

    # Get the item with section info
    result = await db.execute(
        select(CustomSectionItem)
        .join(CustomSection)
        .where(CustomSectionItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section item not found",
        )

    # Check ownership through section
    if item.section.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete items in your own sections",
        )

    await db.delete(item)
    await db.commit()

    return {"message": "Section item deleted successfully"}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


async def get_section_with_items(
    section_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> Dict[str, Union[CustomSection, List[CustomSectionItem]]]:
    """Get a section with all its items"""

    section = await get_custom_section(section_id, db, current_user)
    items = await get_section_items(section_id, db, current_user)

    return {"section": section, "items": items, "item_count": len(items)}


async def get_user_sections_with_items(
    user_id: UUID,
    include_hidden: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> List[Dict[str, Union[CustomSection, List[CustomSectionItem]]]]:
    """Get all sections for a user with their items"""

    sections = await get_user_custom_sections(
        user_id=user_id, include_hidden=include_hidden, db=db, current_user=current_user
    )

    sections_with_items = []
    for section in sections:
        items = await get_section_items(UUID(str(section.id)), db, current_user)
        sections_with_items.append(
            {"section": section, "items": items, "item_count": len(items)}
        )

    return sections_with_items


async def search_section_items(
    user_id: UUID,
    query: str,
    section_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(optional_current_user),
) -> List[CustomSectionItem]:
    """Search items within a user's sections"""

    from sqlalchemy import or_

    search_query = select(CustomSectionItem).join(CustomSection)

    # Filter by user and visible sections
    search_query = search_query.where(CustomSection.user_id == user_id)

    if not current_user or current_user.id != user_id:
        search_query = search_query.where(CustomSection.is_visible == True)

    # Filter by section type if provided
    if section_type:
        search_query = search_query.where(CustomSection.section_type == section_type)

    # Add text search
    search_filter = or_(
        func.lower(CustomSectionItem.title).contains(query.lower()),
        func.lower(CustomSectionItem.subtitle).contains(query.lower()),
        func.lower(CustomSectionItem.description).contains(query.lower()),
    )
    search_query = search_query.where(search_filter)

    # Order by relevance (title matches first, then subtitle, then description)
    search_query = search_query.order_by(
        func.lower(CustomSectionItem.title).contains(query.lower()).desc(),
        func.lower(CustomSectionItem.subtitle).contains(query.lower()).desc(),
        CustomSectionItem.start_date.desc(),
    )

    result = await db.execute(search_query)
    return result.scalars().all()


async def get_section_stats(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[int, UUID, Dict[str, int]]]:
    """Get statistics about a user's sections"""

    # Get section counts by type
    result = await db.execute(
        select(
            CustomSection.section_type,
            func.count(CustomSection.id).label("count"),
            func.count(CustomSectionItem.id).label("item_count"),
        )
        .outerjoin(CustomSectionItem)
        .where(CustomSection.user_id == user_id)
        .group_by(CustomSection.section_type)
    )

    stats = result.all()

    section_types = {}
    total_sections = 0
    total_items = 0

    for stat in stats:
        section_types[stat.section_type] = {
            "sections": stat.count,
            "items": stat.item_count,
        }
        total_sections += stat.count
        total_items += stat.item_count

    return {
        "total_sections": total_sections,
        "total_items": total_items,
        "by_type": section_types,
        "user_id": user_id,
    }
