from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable, Awaitable, Optional
import json
import logging
from datetime import datetime
from app.core.projectcore.coreprojectaudit import create_audit_log
from app.core.corenotification import create_notification, get_common_params
from app.models.schemas import (
    NotificationCreate,
    NotificationType,
)
from uuid import UUID

# Configure logging
logger = logging.getLogger(__name__)


class NotificationAuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        # Paths to exclude from processing
        self.excluded_paths = excluded_paths or [
            "/socials",
            "/skills",
        ]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip excluded paths
        if any(excluded in request.url.path for excluded in self.excluded_paths):
            return await call_next(request)

        # Store original body for later use (if needed)
        request_body = None
        if request.method in ("POST", "PUT", "PATCH"):
            request_body = await self._get_request_body(request)

        response = await call_next(request)

        # Skip if the request failed or isn't relevant
        if response.status_code >= 400 or request.method not in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            return response

        try:
            # Extract user & project info with proper error handling
            user = getattr(request.state, "user", None)
            db = getattr(request.state, "db", None)

            if not db:
                logger.warning("Database session not found in request state")
                return response

            project_id = request.path_params.get("project_id")

            # --- 1. Create Audit Log (if applicable) ---
            if project_id and user:
                await self._create_audit_log(
                    request, response, user, project_id, request_body
                )

            # --- 2. Create Notifications (if applicable) ---
            if user and self._should_notify(request.url.path):
                await self._create_notification(request, response, user, db)

        except Exception as e:
            logger.error(f"Middleware processing failed: {e}", exc_info=True)
            # Don't let middleware errors break the response

        return response

    async def _get_request_body(self, request: Request) -> Optional[bytes]:
        """Get request body without consuming it."""
        try:
            # Store the original receive callable
            receive = request._receive

            # Read the body
            body = b""
            more_body = True

            while more_body:
                message = await receive()
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

            # Create a new receive callable that returns the cached body
            async def new_receive():
                return {"type": "http.request", "body": body, "more_body": False}

            # Replace the receive callable
            request._receive = new_receive

            return body
        except Exception as e:
            logger.warning(f"Failed to extract request body: {e}")
            return None

    async def _create_audit_log(
        self,
        request: Request,
        response: Response,
        user,
        project_id: str,
        request_body: Optional[bytes],
    ):
        """Create audit log entry."""
        try:
            ip_address = self._get_client_ip(request)

            # Parse request body safely
            parsed_body = None
            if request_body:
                parsed_body = self._parse_request_body(request_body)

            await create_audit_log(
                db=request.state.db,
                project_id=UUID(str(project_id)),
                user_id=user.id,
                action=f"{request.method}:{request.url.path}",
                details={
                    "status_code": response.status_code,
                    "params": dict(request.query_params),
                    "payload": parsed_body,
                    "timestamp": datetime.now().isoformat(),
                },
                ip_address=ip_address,
                user_agent=request.headers.get("user-agent"),
            )
            logger.info(f"Audit log created for user {user.id} on project {project_id}")

        except Exception as e:
            logger.error(f"Audit logging failed: {e}", exc_info=True)

    async def _create_notification(
        self, request: Request, response: Response, user, db
    ):
        """Create notification for specific actions using the updated service."""
        try:
            message = self._get_notification_message(request, response)

            if not message:
                return

            ip_address = self._get_client_ip(request)

            # Create notification data dict (not using user_id since it will be set automatically)
            notification_data = {
                "notification_type": NotificationType.SYSTEM,
                "message": message,
                "meta_data": {
                    "action": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ip": ip_address,
                    "user_agent": request.headers.get("user-agent"),
                    "timestamp": datetime.now().isoformat(),
                },
                "action_url": request.url.path,
                "is_read": False,  # New notifications are unread by default
            }

            # Use the updated get_common_params and create_notification
            commons = await get_common_params(data=notification_data, user=user, db=db)

            await create_notification(commons)
            logger.info(f"Notification created for user {user.id}")

        except Exception as e:
            logger.error(f"Notification creation failed: {e}", exc_info=True)

    def _get_notification_message(
        self, request: Request, response: Response
    ) -> Optional[str]:
        """Generate appropriate notification message based on the request."""
        path = request.url.path
        status_code = response.status_code

        # Base messages for successful operations
        if status_code >= 400:
            return None  # Don't notify on failures

        route_messages = {
            "/api/v1/auth/login": "👋 Welcome back! You've successfully logged in.",
            "/api/v1/auth/signup": "🎉 Welcome aboard! Complete your profile to unlock all features.",
            "/api/v1/auth/forgotten-password": "🔑 Password reset requested. Check your email for instructions.",
            "/api/v1/auth/register-device": "📱 New device registered successfully.",
            "/api/v1/auth/reset-password": "🔐 Your password has been successfully reset.",
            "/api/v1/auth/logout": "👋 You've successfully logged out. See you next time!",
        }

        # Check for exact matches first
        if path in route_messages:
            return route_messages[path]

        # Check for partial matches
        for route_path, message in route_messages.items():
            if route_path in path:
                # Customize message for device registration
                if "register-device" in path:
                    device_info = self._get_device_info(request)
                    return f"📱 New login from {device_info}. Review your devices in settings if this wasn't you."
                elif "reset-password" in path:
                    return "🔐 Your password has been successfully reset."
                return message

        # Handle dynamic project-related notifications
        if "/projects/" in path and response.status_code in [200, 201]:
            if request.method == "POST":
                return "🚀 New project created successfully!"
            elif request.method == "PUT" or request.method == "PATCH":
                return "✏️ Project updated successfully!"
            elif request.method == "DELETE":
                return "🗑️ Project deleted successfully!"

        return None

    def _get_device_info(self, request: Request) -> str:
        """Extract device information from request."""
        user_agent = request.headers.get("user-agent", "Unknown Device")

        # Simple device detection (you might want to use a library like user-agents)
        if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
            device_type = "Mobile Device"
        elif "Tablet" in user_agent or "iPad" in user_agent:
            device_type = "Tablet"
        else:
            device_type = "Desktop"

        return device_type

    def _parse_request_body(self, body: bytes) -> Optional[dict]:
        """Parse request body and filter sensitive data."""
        try:
            if not body:
                return None

            body_str = body.decode("utf-8")
            parsed_body = json.loads(body_str)

            # Filter out sensitive fields
            sensitive_fields = {
                "password",
                "token",
                "secret",
                "api_key",
                "access_token",
                "refresh_token",
                "current_password",
                "new_password",
                "confirm_password",
            }

            if isinstance(parsed_body, dict):
                return {
                    k: ("***FILTERED***" if k.lower() in sensitive_fields else v)
                    for k, v in parsed_body.items()
                }

            return parsed_body

        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse request body: {e}")
            return None

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address with proper header checking."""
        # Check for forwarded headers first (common in production with load balancers)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        if request.client and hasattr(request.client, "host"):
            return request.client.host

        return None

    def _should_notify(self, path: str) -> bool:

        # Exact paths that should trigger notifications
        exact_notify_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/signup",
            "/api/v1/auth/register",
            "/api/v1/auth/forgotten-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/register-device",
            "/api/v1/auth/logout",
        }

        # Path prefixes that should trigger notifications
        prefix_notify_paths = {
            "/api/v1/projects/",  # Project-related actions
            "/api/v1/profile/",  # Profile updates
        }

        # Check for exact matches first (most efficient)
        if path in exact_notify_paths:
            return True

        # Check for prefix matches (for parameterized routes)
        return any(path.startswith(prefix) for prefix in prefix_notify_paths)
