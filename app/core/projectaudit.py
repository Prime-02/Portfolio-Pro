from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from fastapi import HTTPException, status, Request
from app.models.db_models import ProjectAudit as ProjectAuditModel, User, PortfolioProject
from app.models.schemas import ProjectAuditCreate, ProjectAudit


async def create_project_audit_log(
    db: AsyncSession,
    audit_data: ProjectAuditCreate,
    current_user: User,
    request: Optional[Request] = None
) -> ProjectAudit:
    """
    Create a new project audit log entry.
    
    Args:
        db: Database session
        audit_data: Audit data to create
        current_user: Current authenticated user
        request: FastAPI request object (optional, for extracting IP and user agent)
    
    Returns:
        Created audit log entry
    
    Raises:
        HTTPException: If user doesn't have access to the project
    """
    # Verify the user has access to the project
    project_query = select(PortfolioProject).where(
        and_(
            PortfolioProject.id == audit_data.project_id,
            PortfolioProject.user_id == current_user.id
        )
    )
    result = await db.execute(project_query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    # Ensure the audit is created by the authenticated user
    if audit_data.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create audit log for another user"
        )
    
    # Extract IP address and user agent from request if provided
    audit_dict = audit_data.model_dump()
    if request:
        # Get IP address (handling proxy headers)
        ip_address = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.headers.get("X-Real-IP")
            or request.client.host if request.client else None
        )
        audit_dict["ip_address"] = ip_address
        
        # Get user agent
        audit_dict["user_agent"] = request.headers.get("User-Agent")
    
    # Create audit log entry
    db_audit = ProjectAuditModel(**audit_dict)
    db.add(db_audit)
    await db.commit()
    await db.refresh(db_audit)
    
    return ProjectAudit.model_validate(db_audit)


async def get_project_audit_logs(
    db: AsyncSession,
    project_id: UUID,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    action_filter: Optional[str] = None
) -> List[ProjectAudit]:
    """
    Get audit logs for a specific project.
    
    Args:
        db: Database session
        project_id: Project ID to get audit logs for
        current_user: Current authenticated user
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        action_filter: Optional filter by action type
    
    Returns:
        List of audit log entries
    
    Raises:
        HTTPException: If user doesn't have access to the project
    """
    # Verify the user has access to the project
    project_query = select(PortfolioProject).where(
        and_(
            PortfolioProject.id == project_id,
            PortfolioProject.user_id == current_user.id
        )
    )
    result = await db.execute(project_query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    # Build query for audit logs
    query = select(ProjectAuditModel).where(ProjectAuditModel.project_id == project_id)
    
    # Apply action filter if provided
    if action_filter:
        query = query.where(ProjectAuditModel.action == action_filter)
    
    # Order by creation date (newest first) and apply pagination
    query = query.order_by(desc(ProjectAuditModel.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    audit_logs = result.scalars().all()
    
    return [ProjectAudit.model_validate(log) for log in audit_logs]


async def get_user_audit_logs(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    project_id_filter: Optional[UUID] = None,
    action_filter: Optional[str] = None
) -> List[ProjectAudit]:
    """
    Get all audit logs for projects owned by the current user.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        project_id_filter: Optional filter by specific project ID
        action_filter: Optional filter by action type
    
    Returns:
        List of audit log entries for user's projects
    """
    # Build query for audit logs of projects owned by the user
    query = (
        select(ProjectAuditModel)
        .join(PortfolioProject, ProjectAuditModel.project_id == PortfolioProject.id)
        .where(PortfolioProject.user_id == current_user.id)
    )
    
    # Apply project filter if provided
    if project_id_filter:
        query = query.where(ProjectAuditModel.project_id == project_id_filter)
    
    # Apply action filter if provided
    if action_filter:
        query = query.where(ProjectAuditModel.action == action_filter)
    
    # Order by creation date (newest first) and apply pagination
    query = query.order_by(desc(ProjectAuditModel.created_at)).offset(skip).limit(limit)
    
    result = await db.execute(query)
    audit_logs = result.scalars().all()
    
    return [ProjectAudit.model_validate(log) for log in audit_logs]


async def get_recent_project_activity(
    db: AsyncSession,
    project_id: UUID,
    current_user: User,
    limit: int = 10
) -> List[ProjectAudit]:
    """
    Get recent activity for a specific project (last N audit logs).
    
    Args:
        db: Database session
        project_id: Project ID to get recent activity for
        current_user: Current authenticated user
        limit: Maximum number of recent activities to return
    
    Returns:
        List of recent audit log entries
    """
    return await get_project_audit_logs(
        db=db,
        project_id=project_id,
        current_user=current_user,
        skip=0,
        limit=limit
    )


async def get_audit_log_by_id(
    db: AsyncSession,
    audit_id: UUID,
    current_user: User
) -> Optional[ProjectAudit]:
    """
    Get a specific audit log entry by ID.
    
    Args:
        db: Database session
        audit_id: Audit log ID
        current_user: Current authenticated user
    
    Returns:
        Audit log entry if found and user has access, None otherwise
    """
    # Query audit log with project join to verify user access
    query = (
        select(ProjectAuditModel)
        .join(PortfolioProject, ProjectAuditModel.project_id == PortfolioProject.id)
        .where(
            and_(
                ProjectAuditModel.id == audit_id,
                PortfolioProject.user_id == current_user.id
            )
        )
    )
    
    result = await db.execute(query)
    audit_log = result.scalar_one_or_none()
    
    if audit_log:
        return ProjectAudit.model_validate(audit_log)
    return None


async def count_project_audit_logs(
    db: AsyncSession,
    project_id: UUID,
    current_user: User,
    action_filter: Optional[str] = None
) -> Union[int, None]:
    """
    Count total audit logs for a project.
    
    Args:
        db: Database session
        project_id: Project ID to count audit logs for
        current_user: Current authenticated user
        action_filter: Optional filter by action type
    
    Returns:
        Total count of audit logs
    
    Raises:
        HTTPException: If user doesn't have access to the project
    """
    # Verify the user has access to the project
    project_query = select(PortfolioProject).where(
        and_(
            PortfolioProject.id == project_id,
            PortfolioProject.user_id == current_user.id
        )
    )
    result = await db.execute(project_query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    # Build count query
    from sqlalchemy import func
    query = select(func.count(ProjectAuditModel.id)).where(
        ProjectAuditModel.project_id == project_id
    )
    
    # Apply action filter if provided
    if action_filter:
        query = query.where(ProjectAuditModel.action == action_filter)
    
    result = await db.execute(query)
    return result.scalar()


async def get_audit_actions_summary(
    db: AsyncSession,
    project_id: UUID,
    current_user: User
) -> dict:
    """
    Get a summary of audit actions for a project (count by action type).
    
    Args:
        db: Database session
        project_id: Project ID to get summary for
        current_user: Current authenticated user
    
    Returns:
        Dictionary with action types as keys and counts as values
    
    Raises:
        HTTPException: If user doesn't have access to the project
    """
    # Verify the user has access to the project
    project_query = select(PortfolioProject).where(
        and_(
            PortfolioProject.id == project_id,
            PortfolioProject.user_id == current_user.id
        )
    )
    result = await db.execute(project_query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )

    # Get action counts
    from sqlalchemy import func
    query = (
        select(
            ProjectAuditModel.action,
            func.count(ProjectAuditModel.id).label('count')
        )
        .where(ProjectAuditModel.project_id == project_id)
        .group_by(ProjectAuditModel.action)
        .order_by(func.count(ProjectAuditModel.id).desc())
    )
    
    result = await db.execute(query)
    action_counts = result.all()
    
    return {row.action: row.count for row in action_counts}


# Helper function to create common audit log entries
async def log_project_action(
    db: AsyncSession,
    project_id: UUID,
    user: User,
    action: str,
    details: Optional[dict] = None,
    request: Optional[Request] = None
) -> ProjectAudit:
    """
    Helper function to quickly log a project action.
    
    Args:
        db: Database session
        project_id: Project ID
        user: User performing the action
        action: Action being performed
        details: Optional additional details
        request: FastAPI request object (optional)
    
    Returns:
        Created audit log entry
    """
    audit_data = ProjectAuditCreate(
        project_id=project_id,
        user_id=UUID(str(user.id)),
        action=action,
        details=details
    )
    
    return await create_project_audit_log(
        db=db,
        audit_data=audit_data,
        current_user=user,
        request=request
    )
