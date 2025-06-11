from fastapi import APIRouter, Depends, HTTPException, Request, Query
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.projectcore.coreprojectaudit import (
    create_audit_log,
    get_audit_log_by_id,
    get_project_audit_logs,
    get_user_audit_logs,
    search_audit_logs,
    delete_audit_log,
)
from app.models.schemas import ProjectAudit, ProjectAuditCreate
from app.models.db_models import  User
from app.database import get_db
from app.core.security import get_current_active_user, require_admin_role
from uuid import UUID


router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.post("/", response_model=ProjectAudit)
async def audit_log_create(
    audit_data: ProjectAuditCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new audit log entry.
    Note: In practice, you might want to automatically create these from other endpoints.
    """
    try:
        return await create_audit_log(
            db=db,
            project_id=audit_data.project_id,
            user_id=UUID(str(current_user.id)),  # Always use the authenticated user
            action=audit_data.action,
            details=audit_data.details,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{audit_id}", response_model=ProjectAudit)
async def get_audit_log(
    audit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific audit log by ID.
    """
    audit_log = await get_audit_log_by_id(db, audit_id)
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    # Add permission check if needed (e.g., admin or user owns the log)
    if not current_user.is_superuser and audit_log.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this audit log"
        )

    return audit_log


@router.get("/project/{project_id}", response_model=List[ProjectAudit])
async def get_logs_for_project(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get audit logs for a specific project.
    """
    # Add project access check here if needed
    return await get_project_audit_logs(
        db=db, project_id=project_id, skip=skip, limit=limit
    )


@router.get("/user/{user_id}", response_model=List[ProjectAudit])
async def get_logs_for_user(
    user_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get audit logs for a specific user.
    """
    # Users can only see their own logs unless admin
    if not current_user.is_superuser and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only view your own audit logs")

    return await get_user_audit_logs(db=db, user_id=user_id, skip=skip, limit=limit)


@router.get("", response_model=List[ProjectAudit])
async def search_logs(
    project_id: Optional[UUID] = Query(None),
    user_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),  # Only admins can search globally
):
    """
    Search audit logs with filters (Admin only).
    """
    return await search_audit_logs(
        db=db,
        project_id=project_id,
        user_id=user_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.delete("/{audit_id}")
async def audit_logdelete(
    audit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),  # Only admins can delete
):
    """
    Delete an audit log (Admin only).
    """
    success = await delete_audit_log(db, audit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return {"message": "Audit log deleted successfully"}
