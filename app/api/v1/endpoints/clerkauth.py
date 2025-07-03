# app/api/endpoints/auth.py (or your main auth router file)
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.coreauth import create_user_from_clerk_webhook
from app.database import get_db
from app.config import settings
from app.core.coreclerkauth import get_user_by_clerk_id
import hmac
import hashlib
import json
from app.core.coreclerkauth import permanently_delete_user
from app.core.coreauth import update_user
from app.models.schemas import UserDeleteRequest
from app.models.schemas import WebhookUserUpdateData
from app.core.security import TokenData, create_access_token, get_expiration_timestamp
from datetime import timedelta

router = APIRouter(prefix="/clerk", tags=["Authentication"])
security = HTTPBearer()

# Clerk Webhook Secret from config
CLERK_WEBHOOK_SECRET = settings.CLERK_WEBHOOK_SECRET


def verify_clerk_webhook(request: Request, body: bytes) -> bool:
    """Verify Clerk webhook signature"""
    if not CLERK_WEBHOOK_SECRET:
        return False

    signature_header = request.headers.get("svix-signature", "")
    try:
        signatures = {
            k: v for k, v in (item.split("=") for item in signature_header.split(","))
        }
        timestamp = signatures.get("t")
        signature = signatures.get("v1")

        if not timestamp or not signature:
            return False

        signed_content = f"{timestamp}.{body.decode('utf-8')}"
        expected_signature = hmac.new(
            CLERK_WEBHOOK_SECRET.encode("utf-8"),
            signed_content.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


@router.post("/clerk-webhook", status_code=status.HTTP_201_CREATED)
async def handle_clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Clerk webhook events for user management.
    This endpoint should be configured in Clerk dashboard to receive user events.
    """
    try:
        body = await request.body()
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
            )

        if data.get("type") != "user.created":
            return {"status": "skipped", "reason": "not a user.created event"}

        user = await create_user_from_clerk_webhook(
            clerk_data=data["data"], request=request, db=db
        )

        return {
            "status": "success",
            "user_id": str(user.id),
            "clerk_id": data["data"]["id"],
            "email": user.email,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}",
        )


@router.post("/clerk-webhook", status_code=status.HTTP_200_OK)
async def webhook_delete_user(
    request_data: UserDeleteRequest,  # Validates incoming webhook data
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook endpoint for permanent user deletion.
    Expects: { "data": { "id": "user_123" } }
    """
    user_id = request_data.data.id  # Extract ID from webhook payload
    return await permanently_delete_user(user_id, request, db)


@router.post("/exchange")
async def clerk_token_exchange(
    user_data: dict = Depends(get_user_by_clerk_id),
):
    """
    Exchange Clerk token for your FastAPI access token.

    Expects: Clerk user ID in the request

    Returns:
        {
            "access_token": "your_jwt_token",
            "token_type": "bearer",
            "expires_in": 900,
            "user_id": "database_user_id",
            "clerk_id": "original_clerk_id"
        }
    """

    access_token_expires = timedelta(days=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    exp_timestamp = get_expiration_timestamp(access_token_expires)

    # Create TokenData with the user_id as subject
    token_data = TokenData(
        sub=str(user_data["user_id"]),  # JWT subject should be string
        exp=exp_timestamp,  # 15 minute expiration
    )

    # Create JWT token
    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 900,  # 15 minutes in seconds
        "user_id": user_data["user_id"],
        "clerk_id": user_data["clerk_id"],
    }


@router.post("/clerk-webhook", status_code=status.HTTP_200_OK)
async def webhook_update_user(
    request_data: WebhookUserUpdateData,  # Validates payload
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook endpoint for user updates.
    Expects: { "data": { "id": "user_123", "email": "new@example.com", ... } }
    """
    user_id = request_data.data.id
    update_fields = request_data.data.model_dump(exclude={"id"})  # Strip ID
    return await update_user(str(user_id), update_fields, db)
