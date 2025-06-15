from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.db_models import MediaGallery as MediaGalleryModel, User
from app.models.schemas import MediaGalleryCreate, MediaGalleryUpdate, MediaGallery


class MediaGalleryCRUD:
    """CRUD operations for Media Gallery"""

    @staticmethod
    async def create_media_item(
        db: AsyncSession,
        media_data: MediaGalleryCreate,
        current_user: User
    ) -> MediaGallery:
        """
        Create a new media gallery item.
        Only authenticated users can create media items.
        """
        # Ensure the user_id matches the authenticated user
        if media_data.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create media item for another user"
            )
        
        db_media = MediaGalleryModel(**media_data.model_dump())
        db.add(db_media)
        await db.commit()
        await db.refresh(db_media)
        return MediaGallery.model_validate(db_media)

    @staticmethod
    async def get_media_item(
        db: AsyncSession,
        media_id: UUID,
        current_user: Optional[User] = None
    ) -> Optional[MediaGallery]:
        """
        Get a specific media item by ID.
        Returns None if not found or user doesn't have access.
        """
        query = select(MediaGalleryModel).where(MediaGalleryModel.id == media_id)
        
        # If user is authenticated, they can only see their own media
        if current_user:
            query = query.where(MediaGalleryModel.user_id == current_user.id)
        
        result = await db.execute(query)
        media_item = result.scalar_one_or_none()
        
        if media_item:
            return MediaGallery.model_validate(media_item)
        return None

    @staticmethod
    async def get_user_media_items(
        db: AsyncSession,
        user_id: UUID,
        current_user: Optional[User] = None,
        skip: int = 0,
        limit: int = 100,
        media_type: Optional[str] = None,
        is_featured: Optional[bool] = None
    ) -> List[MediaGallery]:
        """
        Get media items for a specific user with optional filtering.
        Users can only see their own media items unless specified otherwise.
        """
        query = select(MediaGalleryModel).where(MediaGalleryModel.user_id == user_id)
        
        # If current user is provided and not the owner, restrict access
        if current_user and current_user.id != user_id:
            # You might want to add public/private logic here
            # For now, users can only see their own media
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's media items"
            )
        
        # Apply filters
        if media_type:
            query = query.where(MediaGalleryModel.media_type == media_type)
        
        if is_featured is not None:
            query = query.where(MediaGalleryModel.is_featured == is_featured)
        
        # Order by creation date (newest first) and apply pagination
        query = query.order_by(MediaGalleryModel.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        media_items = result.scalars().all()
        
        return [MediaGallery.model_validate(item) for item in media_items]

    @staticmethod
    async def get_current_user_media_items(
        db: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        media_type: Optional[str] = None,
        is_featured: Optional[bool] = None
    ) -> List[MediaGallery]:
        """
        Get media items for the current authenticated user.
        """
        return await MediaGalleryCRUD.get_user_media_items(
            db=db,
            user_id=UUID(str(current_user.id)),
            current_user=current_user,
            skip=skip,
            limit=limit,
            media_type=media_type,
            is_featured=is_featured
        )

    @staticmethod
    async def get_featured_media_items(
        db: AsyncSession,
        user_id: UUID,
        current_user: Optional[User] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[MediaGallery]:
        """
        Get featured media items for a user.
        """
        return await MediaGalleryCRUD.get_user_media_items(
            db=db,
            user_id=user_id,
            current_user=current_user,
            skip=skip,
            limit=limit,
            is_featured=True
        )

    @staticmethod
    async def update_media_item(
        db: AsyncSession,
        media_id: UUID,
        media_update: MediaGalleryUpdate,
        current_user: User
    ) -> Optional[MediaGallery]:
        """
        Update a media gallery item.
        Only the owner can update their media items.
        """
        # First, check if the media item exists and belongs to the user
        result = await db.execute(
            select(MediaGalleryModel).where(
                and_(
                    MediaGalleryModel.id == media_id,
                    MediaGalleryModel.user_id == current_user.id
                )
            )
        )
        media_item = result.scalar_one_or_none()
        
        if not media_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media item not found or access denied"
            )
        
        # Update only provided fields
        update_data = media_update.model_dump(exclude_unset=True)
        if not update_data:
            return MediaGallery.model_validate(media_item)
        
        await db.execute(
            update(MediaGalleryModel)
            .where(MediaGalleryModel.id == media_id)
            .values(**update_data)
        )
        await db.commit()
        
        # Refresh and return updated item
        await db.refresh(media_item)
        return MediaGallery.model_validate(media_item)

    @staticmethod
    async def delete_media_item(
        db: AsyncSession,
        media_id: UUID,
        current_user: User
    ) -> bool:
        """
        Delete a media gallery item.
        Only the owner can delete their media items.
        """
        # Check if the media item exists and belongs to the user
        result = await db.execute(
            select(MediaGalleryModel).where(
                and_(
                    MediaGalleryModel.id == media_id,
                    MediaGalleryModel.user_id == current_user.id
                )
            )
        )
        media_item = result.scalar_one_or_none()
        
        if not media_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media item not found or access denied"
            )
        
        await db.execute(
            delete(MediaGalleryModel).where(MediaGalleryModel.id == media_id)
        )
        await db.commit()
        return True

    @staticmethod
    async def toggle_featured_status(
        db: AsyncSession,
        media_id: UUID,
        current_user: User
    ) -> Optional[MediaGallery]:
        """
        Toggle the featured status of a media item.
        Only the owner can toggle featured status.
        """
        # Get current media item
        result = await db.execute(
            select(MediaGalleryModel).where(
                and_(
                    MediaGalleryModel.id == media_id,
                    MediaGalleryModel.user_id == current_user.id
                )
            )
        )
        media_item = result.scalar_one_or_none()
        
        if not media_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media item not found or access denied"
            )
        
        # Toggle featured status
        new_featured_status = not media_item.is_featured
        await db.execute(
            update(MediaGalleryModel)
            .where(MediaGalleryModel.id == media_id)
            .values(is_featured=new_featured_status)
        )
        await db.commit()
        
        # Refresh and return updated item
        await db.refresh(media_item)
        return MediaGallery.model_validate(media_item)

    @staticmethod
    async def get_media_by_type(
        db: AsyncSession,
        user_id: UUID,
        media_type: str,
        current_user: Optional[User] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[MediaGallery]:
        """
        Get media items filtered by type for a specific user.
        """
        return await MediaGalleryCRUD.get_user_media_items(
            db=db,
            user_id=user_id,
            current_user=current_user,
            skip=skip,
            limit=limit,
            media_type=media_type
        )

    @staticmethod
    async def count_user_media_items(
        db: AsyncSession,
        user_id: UUID,
        current_user: Optional[User] = None,
        media_type: Optional[str] = None
    ) -> Union[int, None]:
        """
        Count total media items for a user with optional type filter.
        """
        # Check access permissions
        if current_user and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's media count"
            )
        
        query = select(func.count(MediaGalleryModel.id)).where(
            MediaGalleryModel.user_id == user_id
        )
        
        if media_type:
            query = query.where(MediaGalleryModel.media_type == media_type)
        
        result = await db.execute(query)
        return result.scalar()

    @staticmethod
    async def bulk_update_featured_status(
        db: AsyncSession,
        media_ids: List[UUID],
        is_featured: bool,
        current_user: User
    ) -> List[MediaGallery]:
        """
        Bulk update featured status for multiple media items.
        Only the owner can update their media items.
        """
        # Verify all media items belong to the current user
        result = await db.execute(
            select(MediaGalleryModel).where(
                and_(
                    MediaGalleryModel.id.in_(media_ids),
                    MediaGalleryModel.user_id == current_user.id
                )
            )
        )
        media_items = result.scalars().all()
        
        if len(media_items) != len(media_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Some media items not found or access denied"
            )
        
        # Bulk update
        await db.execute(
            update(MediaGalleryModel)
            .where(
                and_(
                    MediaGalleryModel.id.in_(media_ids),
                    MediaGalleryModel.user_id == current_user.id
                )
            )
            .values(is_featured=is_featured)
        )
        await db.commit()
        
        # Return updated items
        result = await db.execute(
            select(MediaGalleryModel).where(MediaGalleryModel.id.in_(media_ids))
        )
        updated_items = result.scalars().all()
        
        return [MediaGallery.model_validate(item) for item in updated_items]


# Convenience functions for easier imports
media_gallery_crud = MediaGalleryCRUD()