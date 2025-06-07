from app.models.schemas import SocialLinksCreate, SocialLinksUpdate, SocialLinksBase
from app.models.db_models import SocialLinks, User
from typing import Dict, Union, List, Optional, cast
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.database import get_db
from sqlalchemy.future import select
import uuid
from datetime import datetime


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[Dict[str, Union[str, bool]], User, AsyncSession]]:
    return {"data": data, "user": user, "db": db}


async def add_social(
    commons: Dict[
        str, Union[Dict[str, Union[str, bool]], User, AsyncSession]
    ] = Depends(get_common_params),
) -> SocialLinksCreate:
    socials_data = cast(Dict[str, Union[str, bool]], commons["data"])
    user = cast(User, commons["user"])
    db = cast(AsyncSession, commons["db"])

    if not socials_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No social media data provided",
        )

    if "platform_name" not in socials_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Platform name is required"
        )

    if "profile_url" not in socials_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile URL is required"
        )

    # Check if platform already exists for this user
    existing_social = await db.execute(
        select(SocialLinks)
        .where(SocialLinks.user_id == user.id)
        .where(SocialLinks.platform_name == cast(str, socials_data["platform_name"]))
    )
    if existing_social.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{socials_data['platform_name']} already exists for this user",
        )

    social_id = uuid.uuid4()
    created_at = datetime.utcnow()

    new_social = SocialLinks(
        id=social_id,
        user_id=user.id,
        platform_name=cast(str, socials_data["platform_name"]),
        profile_url=cast(str, socials_data["profile_url"]),
        created_at=created_at,
    )

    db.add(new_social)
    await db.commit()
    await db.refresh(new_social)

    return SocialLinksCreate(
        id=social_id,
        user_id=uuid.UUID(str(user.id)),
        platform_name=cast(str, new_social.platform_name),
        profile_url=cast(str, new_social.profile_url),
    )


async def get_all_socials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SocialLinksBase]:
    result = await db.execute(select(SocialLinks).where(SocialLinks.user_id == user.id))
    socials = result.scalars().all()

    return [
        SocialLinksBase(
            platform_name=cast(str, social.platform_name),
            profile_url=cast(str, social.profile_url),
            id=cast(uuid.UUID, social.id),
        )
        for social in socials
    ]


async def get_social_by_id(
    social_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SocialLinksBase:
    result = await db.execute(
        select(SocialLinks)
        .where(SocialLinks.id == social_id)
        .where(SocialLinks.user_id == user.id)
    )
    social = cast(Optional[SocialLinks], result.scalar_one_or_none())

    if not social:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Social link not found"
        )

    return SocialLinksBase(
        platform_name=cast(str, social.platform_name),
        profile_url=cast(str, social.profile_url),
        id=cast(uuid.UUID, social.id),
    )


async def update_social(
    social_id: uuid.UUID,
    social_data: SocialLinksUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SocialLinksBase:
    result = await db.execute(
        select(SocialLinks)
        .where(SocialLinks.id == social_id)
        .where(SocialLinks.user_id == user.id)
    )
    social = cast(Optional[SocialLinks], result.scalar_one_or_none())

    if not social:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Social link not found"
        )

    # Check if the new platform name already exists (if it's being updated)
    if social_data.platform_name and social_data.platform_name != social.platform_name:
        existing_social = await db.execute(
            select(SocialLinks)
            .where(SocialLinks.user_id == user.id)
            .where(SocialLinks.platform_name == social_data.platform_name)
        )
        if existing_social.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform with this name already exists for this user",
            )

    # Update fields if they are provided in the update data
    if social_data.platform_name is not None:
        social.platform_name = cast(str, social_data.platform_name)
    if social_data.profile_url is not None:
        social.profile_url = cast(str, social_data.profile_url)

    await db.commit()
    await db.refresh(social)

    return SocialLinksBase(
        platform_name=cast(str, social.platform_name),
        profile_url=cast(str, social.profile_url),
        id=cast(uuid.UUID, social.id),
    )


async def delete_social(
    social_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[bool, str]]:
    result = await db.execute(
        select(SocialLinks)
        .where(SocialLinks.id == social_id)
        .where(SocialLinks.user_id == user.id)
    )
    social = cast(Optional[SocialLinks], result.scalar_one_or_none())

    if not social:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Social link not found"
        )

    await db.delete(social)
    await db.commit()

    return {"success": True, "message": "Social link deleted successfully"}
