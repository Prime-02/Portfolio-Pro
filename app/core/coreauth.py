# services/user_service.py
from sqlalchemy import select, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Request
from app.models.db_models import User, UserSettings
from app.models.schemas import UserCreate, DBUser, UserUpdateRequest
from app.core.security import get_password_hash, validate_username
from app.services.gmail_utils import send_email
from app.core.corenotification import create_user_notification
from typing import Any


async def create_new_user(
    user: UserCreate, request: Request, db: AsyncSession, is_clerk_user: bool = False
) -> DBUser:
    """
    Core user creation logic with welcome notifications.
    Handles both native signups and Clerk webhook integrations.

    Args:
        user: UserCreate data
        request: FastAPI request object
        db: Async database session
        is_clerk_user: Flag indicating if this is a Clerk-created user
    """
    # 1. Check existing user - modified to check auth_id for Clerk users
    query = select(User).where(
        or_(
            User.email == user.email,
            User.username == user.username,
        )
    )

    if is_clerk_user and user.id:
        query = query.where(
            or_(
                User.email == user.email,
                User.username == user.username,
                User.auth_id == user.id,
            )
        )

    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )

    # 2. Validate username (skip for Clerk users if username is None)
    if not is_clerk_user and not validate_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 30 characters...",  # truncated for brevity
        )

    # 3. Handle password generation
    if is_clerk_user:
        # For Clerk users, generate a random password since we won't have one
        # This account will only be accessible via Clerk authentication
        import secrets

        user_password = secrets.token_urlsafe(16)
    else:
        user_password = user.password if user.password else ""

    # 4. Create new user
    db_user = User(
        email=user.email,
        username=user.username or user.email.split("@")[0],  # Fallback for Clerk users
        hashed_password=get_password_hash(user_password),
        is_active=True,
        role="user",
        is_superuser=False,
        firstname=str(user.first_name) if user.first_name else "",
        lastname=str(user.last_name) if user.last_name else "",
        auth_id=str(user.id) if is_clerk_user else "",
    )
    db.add(db_user)
    await db.flush()

    # 5. Create default settings
    db_settings = UserSettings(
        language="en",
        theme="light",
        primary_theme="#000000",
        owner_id=db_user.id,
        secondary_theme="#ffffff",
        layout_style="default",
    )
    db.add(db_settings)

    try:
        await db.commit()
        await db.refresh(db_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # 6. Send welcome email if not from Clerk (Clerk handles its own notifications)
    if not is_clerk_user and user.email:
        send_email(
            to=str(user.email),
            subject=f"Welcome to Portfolio Pro, {user.username or 'User'}!",
            body="Welcome to Portfolio Pro! Your account has been created successfully...",
        )

    # 7. Create notifications
    await create_user_notification(
        user=db_user,
        db=db,
        message="Welcome to Portfolio Pro! Your account has been created successfully.",
        notification_type="info",
        action_url="/dashboard",
        meta_data={
            "event": "account_created",
            "signup_method": "clerk" if is_clerk_user else "email",
        },
        request=request,
    )

    if not is_clerk_user:
        await create_user_notification(
            user=db_user,
            db=db,
            message="Complete your profile setup to get the most out of Portfolio Pro",
            notification_type="info",
            action_url="/profile/setup",
            meta_data={"event": "profile_setup_reminder", "action_required": True},
            request=request,
        )

    return DBUser.model_validate(db_user)


async def create_user_from_clerk_webhook(
    clerk_data: dict, request: Request, db: AsyncSession
) -> DBUser:
    """
    Specialized function to handle Clerk webhook user creation.
    """
    # Extract emails from Clerk data
    emails = [e["email_address"] for e in clerk_data.get("email_addresses", [])]
    primary_email = next(
        (
            e["email_address"]
            for e in clerk_data.get("email_addresses", [])
            if e.get("id") == clerk_data.get("primary_email_address_id")
        ),
        emails[0] if emails else "",
    )
    print(clerk_data)

    user_data = UserCreate(
        email=primary_email,
        username=clerk_data.get("username") or primary_email.split("@")[0],
        password="",  # Not used for Clerk users
        first_name=clerk_data.get("first_name", ""),
        last_name=clerk_data.get("last_name", ""),
        id=clerk_data.get("id"),
    )

    return await create_new_user(user_data, request, db, is_clerk_user=True)


async def update_user(
    user_id: str, user_data: dict[str, Any], db: AsyncSession
) -> dict:
    """
    Updates user fields (excluding id).
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Filter out None values to avoid overwriting with null
    update_data = user_data.dict(exclude_unset=True)

    # Prevent updating ID
    if "id" in update_data:
        del update_data["id"]

    # Execute update
    await db.execute(update(User).where(User.id == user_id).values(**update_data))
    await db.commit()

    return {"status": "success", "message": "User updated successfully"}
