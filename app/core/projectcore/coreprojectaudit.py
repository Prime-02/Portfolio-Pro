from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import ProjectAudit as ProjectAuditSchema
from app.models.db_models import ProjectAudit
from typing import Optional, List
from sqlalchemy import select, delete
from datetime import datetime
import uuid


async def create_audit_log(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    action: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ProjectAuditSchema:
    """
    Create a new audit log entry.

    Args:
        db: Database session
        project_id: ID of the project being audited
        user_id: ID of the user performing the action
        action: Type of action performed (e.g., "create", "update", "delete")
        details: Additional context about the action
        ip_address: IP address of the user
        user_agent: User agent string from the request

    Returns:
        The created audit log entry
    """
    created_at = datetime.now()
    audit_log = ProjectAudit(
        project_id=project_id,
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=created_at,
        id=uuid.uuid4(),
    )

    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)
    return audit_log


async def get_audit_log_by_id(
    db: AsyncSession, audit_id: UUID
) -> Optional[ProjectAudit]:
    """
    Retrieve a single audit log entry by its ID.

    Args:
        db: Database session
        audit_id: ID of the audit log to retrieve

    Returns:
        The audit log if found, None otherwise
    """
    result = await db.execute(select(ProjectAudit).where(ProjectAudit.id == audit_id))
    return result.scalar_one_or_none()


async def get_project_audit_logs(
    db: AsyncSession, project_id: UUID, skip: int = 0, limit: int = 100
) -> List[ProjectAudit]:
    """
    Get paginated audit logs for a specific project, newest first.

    Args:
        db: Database session
        project_id: ID of the project to get logs for
        skip: Pagination offset
        limit: Maximum number of logs to return

    Returns:
        List of audit logs for the project
    """
    result = await db.execute(
        select(ProjectAudit)
        .where(ProjectAudit.project_id == project_id)
        .order_by(ProjectAudit.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_user_audit_logs(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[ProjectAudit]:
    """
    Get paginated audit logs for a specific user, newest first.

    Args:
        db: Database session
        user_id: ID of the user to get logs for
        skip: Pagination offset
        limit: Maximum number of logs to return

    Returns:
        List of audit logs for the user
    """
    result = await db.execute(
        select(ProjectAudit)
        .where(ProjectAudit.user_id == user_id)
        .order_by(ProjectAudit.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def search_audit_logs(
    db: AsyncSession,
    project_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[ProjectAudit]:
    """
    Search audit logs with multiple filter criteria.

    Args:
        db: Database session
        project_id: Filter by project ID
        user_id: Filter by user ID
        action: Filter by action type
        start_date: Earliest date to include
        end_date: Latest date to include
        skip: Pagination offset
        limit: Maximum number of logs to return

    Returns:
        List of matching audit logs
    """
    query = select(ProjectAudit)

    if project_id:
        query = query.where(ProjectAudit.project_id == project_id)
    if user_id:
        query = query.where(ProjectAudit.user_id == user_id)
    if action:
        query = query.where(ProjectAudit.action == action)
    if start_date:
        query = query.where(ProjectAudit.created_at >= start_date)
    if end_date:
        query = query.where(ProjectAudit.created_at <= end_date)

    query = query.order_by(ProjectAudit.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def delete_audit_log(db: AsyncSession, audit_id: UUID) -> dict:
    """
    Delete an audit log (should be restricted to admin users).

    Args:
        db: Database session
        audit_id: ID of the audit log to delete

    Returns:
        True if deleted, False if not found
    """
    result = await db.execute(delete(ProjectAudit).where(ProjectAudit.id == audit_id))
    await db.commit()
    return {"message": "Log deleted"}
