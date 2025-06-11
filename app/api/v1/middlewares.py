from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Awaitable
import json

class NotificationAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable]
    ):
        response = await call_next(request)
        
        # Skip if the request failed or isn't relevant
        if response.status_code >= 400 or request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response
        
        # Extract user & project info (modify based on your auth system)
        user = request.state.user if hasattr(request.state, "user") else None
        project_id = request.path_params.get("project_id")  # Adjust based on your routes
        
        # --- 1. Create Audit Log (if applicable) ---
        if project_id and user:
            try:
                await create_audit_log(
                    db=request.state.db,
                    project_id=project_id,
                    user_id=user.id,
                    action=f"{request.method}:{request.url.path}",
                    details={
                        "status_code": response.status_code,
                        "params": dict(request.query_params),
                        "payload": await _safe_extract_body(request),
                    },
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent")
                )
            except Exception as e:
                logging.error(f"Audit logging failed: {e}")

        # --- 2. Create Notifications (if applicable) ---
        if user and _should_notify(request.url.path):
            try:
                await create_notification(
                    db=request.state.db,
                    user_id=user.id,
                    message=f"Action completed: {request.method} {request.url.path}",
                    context={
                        "action": request.method,
                        "path": request.url.path,
                        "status": response.status_code,
                    }
                )
            except Exception as e:
                logging.error(f"Notification failed: {e}")

        return response

async def _safe_extract_body(request: Request) -> Optional[dict]:
    """Safely extract request body without consuming it."""
    try:
        body = await request.json()
        return {k: v for k, v in body.items() if k not in ("password", "token")}  # Filter sensitive data
    except (json.JSONDecodeError, TypeError):
        return None

def _should_notify(path: str) -> bool:
    """Define which routes should trigger notifications."""
    notify_paths = {
        "/projects/",
        "/settings/",
        "/billing/",
    }
    return any(p in path for p in notify_paths)