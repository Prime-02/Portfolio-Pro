from typing import List, Optional, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import get_current_user, optional_current_user
from app.models.db_models import User
from app.models.schemas import MediaGalleryCreate, MediaGalleryUpdate, MediaGallery
from app.core.mediagallery import MediaGalleryCRUD

router = APIRouter(prefix="/media-gallery", tags=["Media Gallery"])


# Create media item
@router.post("/", response_model=MediaGallery, status_code=status.HTTP_201_CREATED)
async def create_media_item(
    media_data: MediaGalleryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a new media gallery item.
    Requires authentication.
    """
    return await MediaGalleryCRUD.create_media_item(db, media_data, current_user)


# Get single media item by ID
@router.get("/{media_id}", response_model=MediaGallery)
async def get_media_item(
    media_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(optional_current_user)] = None,
):
    """
    Get a specific media item by ID.
    Authentication optional - users can only see their own media when authenticated.
    """
    media_item = await MediaGalleryCRUD.get_media_item(db, media_id, current_user)
    if not media_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found"
        )
    return media_item


# Get current user's media items
@router.get("/", response_model=List[MediaGallery])
async def get_current_user_media_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    media_type: Annotated[Optional[str], Query()] = None,
    is_featured: Annotated[Optional[bool], Query()] = None,
):
    """
    Get media items for the current authenticated user.
    Supports filtering by media_type and featured status.
    """
    return await MediaGalleryCRUD.get_current_user_media_items(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        media_type=media_type,
        is_featured=is_featured,
    )


# Get media items by user ID
@router.get("/user/{user_id}", response_model=List[MediaGallery])
async def get_user_media_items(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(optional_current_user)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    media_type: Annotated[Optional[str], Query()] = None,
    is_featured: Annotated[Optional[bool], Query()] = None,
):
    """
    Get media items for a specific user.
    Users can only access their own media items.
    """
    return await MediaGalleryCRUD.get_user_media_items(
        db=db,
        user_id=user_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        media_type=media_type,
        is_featured=is_featured,
    )


# Get featured media items for a user
@router.get("/user/{user_id}/featured", response_model=List[MediaGallery])
async def get_user_featured_media(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(optional_current_user)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """
    Get featured media items for a specific user.
    """
    return await MediaGalleryCRUD.get_featured_media_items(
        db=db, user_id=user_id, current_user=current_user, skip=skip, limit=limit
    )


# Get current user's featured media
@router.get("/my/featured", response_model=List[MediaGallery])
async def get_my_featured_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """
    Get current user's featured media items.
    """
    return await MediaGalleryCRUD.get_featured_media_items(
        db=db,
        user_id=UUID(str(current_user.id)),
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


# Get media by type for a user
@router.get("/user/{user_id}/type/{media_type}", response_model=List[MediaGallery])
async def get_user_media_by_type(
    user_id: UUID,
    media_type: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(optional_current_user)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    Get media items of a specific type for a user.
    Common media types: 'image', 'video', 'document', 'audio'
    """
    return await MediaGalleryCRUD.get_media_by_type(
        db=db,
        user_id=user_id,
        media_type=media_type,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


# Get current user's media by type
@router.get("/my/type/{media_type}", response_model=List[MediaGallery])
async def get_my_media_by_type(
    media_type: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """
    Get current user's media items of a specific type.
    """
    return await MediaGalleryCRUD.get_media_by_type(
        db=db,
        user_id=UUID(str(current_user.id)),
        media_type=media_type,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


# Update media item
@router.put("/{media_id}", response_model=MediaGallery)
async def update_media_item(
    media_id: UUID,
    media_update: MediaGalleryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Update a media gallery item.
    Only the owner can update their media items.
    """
    return await MediaGalleryCRUD.update_media_item(
        db, media_id, media_update, current_user
    )


# Toggle featured status
@router.patch("/{media_id}/toggle-featured", response_model=MediaGallery)
async def toggle_media_featured_status(
    media_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Toggle the featured status of a media item.
    Only the owner can toggle featured status.
    """
    return await MediaGalleryCRUD.toggle_featured_status(db, media_id, current_user)


# Delete media item
@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_item(
    media_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Delete a media gallery item.
    Only the owner can delete their media items.
    """
    await MediaGalleryCRUD.delete_media_item(db, media_id, current_user)


# Get media count for current user
@router.get("/my/count", response_model=dict)
async def get_my_media_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    media_type: Annotated[Optional[str], Query()] = None,
):
    """
    Get total count of current user's media items.
    Optionally filter by media type.
    """
    count = await MediaGalleryCRUD.count_user_media_items(
        db=db,
        user_id=UUID(str(current_user.id)),
        current_user=current_user,
        media_type=media_type,
    )
    return {"count": count, "media_type": media_type, "user_id": str(current_user.id)}


# Get media count for a specific user
@router.get("/user/{user_id}/count", response_model=dict)
async def get_user_media_count(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(optional_current_user)] = None,
    media_type: Annotated[Optional[str], Query()] = None,
):
    """
    Get total count of media items for a specific user.
    Users can only access their own media count.
    """
    count = await MediaGalleryCRUD.count_user_media_items(
        db=db, user_id=user_id, current_user=current_user, media_type=media_type
    )
    return {"count": count, "media_type": media_type, "user_id": str(user_id)}


# Bulk operations
@router.patch("/bulk/featured", response_model=List[MediaGallery])
async def bulk_update_featured_status(
    request_data: dict,  # Expected: {"media_ids": [UUID, ...], "is_featured": bool}
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Bulk update featured status for multiple media items.
    Request body: {"media_ids": ["uuid1", "uuid2", ...], "is_featured": true/false}
    """
    media_ids = request_data.get("media_ids", [])
    is_featured = request_data.get("is_featured", False)

    if not media_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_ids list cannot be empty",
        )

    # Convert string UUIDs to UUID objects
    try:
        media_ids = [UUID(media_id) for media_id in media_ids]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format in media_ids",
        )

    return await MediaGalleryCRUD.bulk_update_featured_status(
        db=db, media_ids=media_ids, is_featured=is_featured, current_user=current_user
    )


# Get media statistics for current user
@router.get("/my/stats", response_model=dict)
async def get_my_media_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get comprehensive media statistics for the current user.
    """
    total_count = await MediaGalleryCRUD.count_user_media_items(
        db=db, user_id=UUID(str(current_user.id)), current_user=current_user
    )

    featured_count = await MediaGalleryCRUD.count_user_media_items(
        db=db, user_id=UUID(str(current_user.id)), current_user=current_user
    )

    # Get counts by media type
    media_types = ["image", "video", "document", "audio"]
    type_counts = {}

    for media_type in media_types:
        count = await MediaGalleryCRUD.count_user_media_items(
            db=db,
            user_id=UUID(str(current_user.id)),
            current_user=current_user,
            media_type=media_type,
        )
        type_counts[media_type] = count

    return {
        "user_id": str(current_user.id),
        "total_media": total_count,
        "featured_media": featured_count,
        "by_type": type_counts,
    }


# Health check endpoint
@router.get("/health", status_code=status.HTTP_200_OK)
async def media_gallery_health_check():
    """
    Health check endpoint for media gallery service.
    """
    return {"status": "healthy", "service": "media_gallery"}
