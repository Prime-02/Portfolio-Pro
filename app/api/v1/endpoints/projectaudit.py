from typing import List, Optional, Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import get_current_user
from app.models.db_models import User
from app.models.schemas import ProjectAuditCreate, ProjectAudit
from app.core.projectaudit import (
    create_project_audit_log,
    get_project_audit_logs,
    get_user_audit_logs,
    get_recent_project_activity,
    get_audit_log_by_id,
    count_project_audit_logs,
    get_audit_actions_summary,
    log_project_action
)

router = APIRouter(prefix="/project-audit", tags=["Project Audit"])


# Create audit log entry
@router.post("/", response_model=ProjectAudit, status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    audit_data: ProjectAuditCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Create a new project audit log entry.
    Automatically captures IP address and user agent from request.
    """
    return await create_project_audit_log(
        db=db,
        audit_data=audit_data,
        current_user=current_user,
        request=request
    )


# Quick audit logging endpoint
@router.post("/log", response_model=ProjectAudit, status_code=status.HTTP_201_CREATED)
async def log_audit_action(
    request_data: dict,  # Expected: {"project_id": UUID, "action": str, "details": dict}
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Quick audit logging endpoint.
    Request body: {
        "project_id": "uuid",
        "action": "action_name",
        "details": {"key": "value"}  // optional
    }
    """
    try:
        project_id = UUID(request_data["project_id"])
        action = request_data["action"]
        details = request_data.get("details", None)
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request data: {str(e)}"
        )
    
    return await log_project_action(
        db=db,
        project_id=project_id,
        user=current_user,
        action=action,
        details=details,
        request=request
    )


# Get audit logs for a specific project
@router.get("/project/{project_id}", response_model=List[ProjectAudit])
async def get_project_audits(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    action: Annotated[Optional[str], Query()] = None
):
    """
    Get audit logs for a specific project.
    Supports filtering by action type and pagination.
    """
    return await get_project_audit_logs(
        db=db,
        project_id=project_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        action_filter=action
    )


# Get all audit logs for current user's projects
@router.get("/my-projects", response_model=List[ProjectAudit])
async def get_my_project_audits(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    project_id: Annotated[Optional[UUID], Query()] = None,
    action: Annotated[Optional[str], Query()] = None
):
    """
    Get audit logs for all projects owned by the current user.
    Supports filtering by specific project ID and action type.
    """
    return await get_user_audit_logs(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        project_id_filter=project_id,
        action_filter=action
    )


# Get recent activity for a project
@router.get("/project/{project_id}/recent", response_model=List[ProjectAudit])
async def get_project_recent_activity(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10
):
    """
    Get recent activity for a specific project.
    Returns the most recent audit log entries.
    """
    return await get_recent_project_activity(
        db=db,
        project_id=project_id,
        current_user=current_user,
        limit=limit
    )


# Get specific audit log by ID
@router.get("/{audit_id}", response_model=ProjectAudit)
async def get_audit_log(
    audit_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get a specific audit log entry by ID.
    User must own the project associated with the audit log.
    """
    audit_log = await get_audit_log_by_id(
        db=db,
        audit_id=audit_id,
        current_user=current_user
    )
    
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found or access denied"
        )
    
    return audit_log


# Get audit log count for a project
@router.get("/project/{project_id}/count", response_model=dict)
async def get_project_audit_count(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    action: Annotated[Optional[str], Query()] = None
):
    """
    Get total count of audit logs for a project.
    Optionally filter by action type.
    """
    count = await count_project_audit_logs(
        db=db,
        project_id=project_id,
        current_user=current_user,
        action_filter=action
    )
    
    return {
        "project_id": str(project_id),
        "total_audit_logs": count,
        "action_filter": action
    }


# Get action summary for a project
@router.get("/project/{project_id}/summary", response_model=dict)
async def get_project_audit_summary(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get summary of audit actions for a project.
    Returns count of each action type.
    """
    summary = await get_audit_actions_summary(
        db=db,
        project_id=project_id,
        current_user=current_user
    )
    
    return {
        "project_id": str(project_id),
        "action_summary": summary,
        "total_actions": sum(summary.values())
    }


# Get audit statistics for current user
@router.get("/my-projects/stats", response_model=dict)
async def get_my_audit_statistics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Get comprehensive audit statistics for current user's projects.
    """
    # Get all audit logs for user's projects
    all_audits = await get_user_audit_logs(
        db=db,
        current_user=current_user,
        skip=0,
        limit=1000  # Get a large number for statistics
    )
    
    # Calculate statistics
    total_audits = len(all_audits)
    
    # Count by action
    action_counts = {}
    project_counts = {}
    
    for audit in all_audits:
        # Count actions
        action_counts[audit.action] = action_counts.get(audit.action, 0) + 1
        
        # Count by project
        project_id_str = str(audit.project_id)
        project_counts[project_id_str] = project_counts.get(project_id_str, 0) + 1
    
    # Get most active project
    most_active_project = max(project_counts.items(), key=lambda x: x[1]) if project_counts else None
    
    # Get most common action
    most_common_action = max(action_counts.items(), key=lambda x: x[1]) if action_counts else None
    
    return {
        "user_id": str(current_user.id),
        "total_audit_logs": total_audits,
        "unique_projects_with_activity": len(project_counts),
        "action_breakdown": action_counts,
        "most_active_project": {
            "project_id": most_active_project[0],
            "audit_count": most_active_project[1]
        } if most_active_project else None,
        "most_common_action": {
            "action": most_common_action[0],
            "count": most_common_action[1]
        } if most_common_action else None
    }


# Get audit logs by action type across all user projects
@router.get("/my-projects/action/{action_type}", response_model=List[ProjectAudit])
async def get_my_audits_by_action(
    action_type: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    project_id: Annotated[Optional[UUID], Query()] = None
):
    """
    Get audit logs of a specific action type across all user's projects.
    Optionally filter by specific project.
    """
    return await get_user_audit_logs(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        project_id_filter=project_id,
        action_filter=action_type
    )


# Bulk audit logging endpoint
@router.post("/bulk", response_model=List[ProjectAudit], status_code=status.HTTP_201_CREATED)
async def bulk_create_audit_logs(
    audit_entries: List[dict],  # List of audit data
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Create multiple audit log entries in bulk.
    Request body: [
        {"project_id": "uuid", "action": "action_name", "details": {...}},
        {"project_id": "uuid", "action": "action_name", "details": {...}}
    ]
    """
    if not audit_entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audit entries list cannot be empty"
        )
    
    if len(audit_entries) > 50:  # Limit bulk operations
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 audit entries allowed per bulk operation"
        )
    
    created_audits = []
    
    for entry in audit_entries:
        try:
            project_id = UUID(entry["project_id"])
            action = entry["action"]
            details = entry.get("details", None)
            
            audit = await log_project_action(
                db=db,
                project_id=project_id,
                user=current_user,
                action=action,
                details=details,
                request=request
            )
            created_audits.append(audit)
            
        except (KeyError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid entry format: {str(e)}"
            )
        except HTTPException:
            # Re-raise HTTP exceptions (like access denied)
            raise
    
    return created_audits


# Health check endpoint
@router.get("/health", status_code=status.HTTP_200_OK)
async def audit_service_health_check():
    """
    Health check endpoint for project audit service.
    """
    return {"status": "healthy", "service": "project_audit"}



