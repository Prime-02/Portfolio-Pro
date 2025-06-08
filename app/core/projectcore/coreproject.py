from app.models.schemas import (
    PortfolioProjectBase,
    PortfolioProjectUpdate,
    CollaboratorResponse,
)
from app.models.db_models import PortfolioProject, User, UserProjectAssociation
from typing import Sequence
from typing import Dict, Union, List, Optional, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.security import get_current_user
from app.database import get_db
import uuid
from datetime import datetime, timedelta
from sqlalchemy.sql import Select
from sqlalchemy import exists, literal_column, and_, or_, case, func
from app.core.user import get_user_by_username, verify_edit_permission
from sqlalchemy.sql.functions import coalesce


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[Dict[str, str], User, AsyncSession]]:
    return {"data": data, "user": user, "db": db}


async def add_project(
    commons: dict = Depends(get_common_params),
) -> PortfolioProject:
    project_data = commons["data"]
    user = commons["user"]
    db = commons["db"]

    # Validate input
    if not project_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No project data provided"
        )
    if not all(k in project_data for k in ["project_name", "project_description", "project_category"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name and description are required",
        )

    # Create the project
    project = PortfolioProject(
        project_name=project_data["project_name"],
        project_description=project_data["project_description"],
        project_category=project_data["project_category"],
        project_url=project_data.get("project_url"),
        project_image_url=project_data.get("project_image_url"),
        is_public=project_data.get("is_public", True),
        created_at=datetime.now(),
        is_completed=project_data.get("is_completed", False),
        is_concept=project_data.get("is_concept", False),
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Link the user to the project via association table
    association = UserProjectAssociation(
        user_id=user.id,
        project_id=project.id,
        role="owner",
        can_edit=True,
        created_at=datetime.now(),
        contribution_description=project_data.get("contribution_description"),
        contribution=project_data.get("contribution"),
    )

    db.add(association)
    await db.commit()

    return project


async def get_project_by_id(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectBase:
    """Get a specific project by ID if the user has access to it."""
    # Check if user has access to this project
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == user.id,
            UserProjectAssociation.project_id == project_id,
        )
    )
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have access to it",
        )

    # Get the project itself
    result = await db.execute(
        select(PortfolioProject).filter(PortfolioProject.id == project_id)
    )
    project = result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return project


async def get_all_user_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_public: bool = False,
) -> Sequence[PortfolioProjectBase]:
    """Get all projects for the current user, optionally including public projects."""
    query = (
        select(PortfolioProject)
        .join(
            UserProjectAssociation,
            PortfolioProject.id == UserProjectAssociation.project_id,
        )
        .filter(UserProjectAssociation.user_id == user.id)
    )

    if include_public:
        # Include public projects that the user doesn't own
        public_query = select(PortfolioProject).filter(
            PortfolioProject.is_public == True,
            ~PortfolioProject.id.in_(
                select(UserProjectAssociation.project_id).filter(
                    UserProjectAssociation.user_id == user.id
                )
            ),
        )
        query = query.union(public_query)

    result = await db.execute(query)
    return result.scalars().all()


async def update_project(
    project_id: uuid.UUID,
    project_data: PortfolioProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectUpdate:
    """Update a project if the user has edit permissions."""
    # Check if user has edit rights to this project
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == user.id,
            UserProjectAssociation.project_id == project_id,
            UserProjectAssociation.can_edit == True,
        )
    )
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this project",
        )

    # Get the project to update
    result = await db.execute(
        select(PortfolioProject).filter(PortfolioProject.id == project_id)
    )
    project = result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Update the project fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    project.updated_at = datetime.now()
    await db.commit()
    await db.refresh(project)

    return project


async def delete_project(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Delete a project if the user is the owner."""
    # Check if user is the owner of this project
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == user.id,
            UserProjectAssociation.project_id == project_id,
            UserProjectAssociation.role == "owner",
        )
    )
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can delete this project",
        )

    # First delete all associations
    await db.execute(
        delete(UserProjectAssociation).where(
            UserProjectAssociation.project_id == project_id
        )
    )
    await db.commit()

    # Then delete the project
    result = await db.execute(
        delete(PortfolioProject).where(PortfolioProject.id == project_id)
    )
    await db.commit()

    return {"message": "Project deleted successfully"}


async def get_project_collaborators(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[CollaboratorResponse]:
    """Get all collaborators for a project (public access)"""
    # Check if project exists
    if not await db.scalar(select(exists().where(PortfolioProject.id == project_id))):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    # Build query
    stmt = (
        select(
            literal_column("users.username").label("username"),
            literal_column("user_project_association.role").label("role"),
            literal_column("user_project_association.can_edit").label("can_edit"),
            literal_column("user_project_association.created_at").label("created_at"),
            literal_column("user_project_association.contribution_description").label(
                "contribution_description"
            ),
            literal_column("user_project_association.contribution").label(
                "contribution"
            ),
        )
        .select_from(UserProjectAssociation)
        .join(User, UserProjectAssociation.user_id == User.id)
        .where(UserProjectAssociation.project_id == project_id)
    )

    # Execute query and format response
    result = await db.execute(stmt)
    collaborators = result.all()

    return [
        CollaboratorResponse(
            username=row.username,
            role=row.role,
            can_edit=row.can_edit,
            created_at=row.created_at,
            contribution_description=row.contribution_description,
            contribution=row.contribution,
        )
        for row in collaborators
    ]


async def add_collaborator(
    project_id: uuid.UUID,
    username: str,
    role: str,
    can_edit: bool,
    contribution_description: Optional[str] = None,
    contribution: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[str, bool, datetime]]:
    """
    Add a collaborator to a project if the requesting user has edit permissions.

    Args:
        project_id: The ID of the project to add the collaborator to
        username: The username of the user to add as a collaborator
        role: The role of the collaborator (e.g., "contributor", "reviewer")
        can_edit: Whether the collaborator can edit the project
        contribution_description: Description of the collaborator's contribution
        contribution_description: The collaborator's contribution
        user: The current authenticated user (injected by dependency)
        db: The database session (injected by dependency)

    Returns:
        A message indicating success

    Raises:
        HTTPException: If the project doesn't exist, user doesn't have permission,
                      or the collaborator user doesn't exist
    """
    # Check if requesting user has edit rights to this project
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == user.id,
            UserProjectAssociation.project_id == project_id,
            UserProjectAssociation.can_edit == True,
        )
    )
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add collaborators to this project",
        )

    # Check if project exists
    project_exists = await db.scalar(
        select(exists().where(PortfolioProject.id == project_id))
    )
    if not project_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Get the user to add as collaborator
    result = await db.execute(select(User).filter(User.username == username))
    collaborator_user = result.scalars().first()

    if not collaborator_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is already a collaborator
    existing_association = await db.scalar(
        select(
            exists().where(
                and_(
                    UserProjectAssociation.user_id == collaborator_user.id,
                    UserProjectAssociation.project_id == project_id,
                )
            )
        )
    )
    if existing_association:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a collaborator on this project",
        )

    # Create the association
    new_association = UserProjectAssociation(
        user_id=collaborator_user.id,
        project_id=project_id,
        role=role,
        can_edit=can_edit,
        created_at=datetime.now(),
        contribution_description=contribution_description,
        contribution=contribution,
    )

    db.add(new_association)
    await db.commit()

    return {"message": "Collaborator added successfully"}


async def remove_collaborator(
    project_id: uuid.UUID,
    username: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Remove a collaborator from a project if the requesting user is the owner.

    Args:
        project_id: The ID of the project to remove the collaborator from
        username: The username of the user to remove as a collaborator
        user: The current authenticated user (injected by dependency)
        db: The database session (injected by dependency)

    Returns:
        A message indicating success

    Raises:
        HTTPException: If the project doesn't exist, user isn't the owner,
                      or the collaborator user doesn't exist
    """
    # Check if requesting user is the owner of this project
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == user.id,
            UserProjectAssociation.project_id == project_id,
            UserProjectAssociation.role == "owner",
        )
    )
    owner_association = result.scalars().first()

    if not owner_association:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can remove collaborators",
        )

    # Check if project exists
    project_exists = await db.scalar(
        select(exists().where(PortfolioProject.id == project_id))
    )
    if not project_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Get the user to remove as collaborator
    result = await db.execute(select(User).filter(User.username == username))
    collaborator_user = result.scalars().first()

    if not collaborator_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is actually a collaborator
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == collaborator_user.id,
            UserProjectAssociation.project_id == project_id,
        )
    )
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a collaborator on this project",
        )

    # Prevent owner from removing themselves
    if association.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the project owner",
        )

    # Delete the association
    await db.execute(
        delete(UserProjectAssociation).where(
            UserProjectAssociation.user_id == collaborator_user.id,
            UserProjectAssociation.project_id == project_id,
        )
    )
    await db.commit()

    return {"message": "Collaborator removed successfully"}


async def get_all_projects_by_user(
    username: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[PortfolioProjectBase]:
    """
    Get all projects created by a specific user (including private ones if requested by owner).

    Args:
        username: Username of the user whose projects to retrieve
        db: Database session
        current_user: The currently authenticated user

    Returns:
        List of projects created by the user

    Raises:
        HTTPException: If user not found or unauthorized to view private projects
    """
    # Get the target user
    result = await db.execute(select(User).filter(User.username == username))
    target_user = result.scalars().first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if current user is requesting their own projects
    is_self = current_user.id == target_user.id

    # Base query for projects owned by the target user
    query = (
        select(PortfolioProject)
        .join(
            UserProjectAssociation,
            PortfolioProject.id == UserProjectAssociation.project_id,
        )
        .filter(
            UserProjectAssociation.user_id == target_user.id,
            # UserProjectAssociation.role == "owner",
        )
    )

    # If not requesting their own projects, filter for public projects only
    if not is_self:
        query = query.filter(PortfolioProject.is_public == True)

    result = await db.execute(query)
    return result.scalars().all()


async def search_projects(
    search_term: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_public: bool = True,
) -> Sequence[PortfolioProjectBase]:
    """
    Search projects by name or description.
    Returns matching projects the user has access to plus public ones if requested.
    """
    # Base query for projects user has access to
    user_projects = (
        select(PortfolioProject)
        .join(UserProjectAssociation)
        .filter(UserProjectAssociation.user_id == current_user.id)
    )

    if include_public:
        public_projects = select(PortfolioProject).filter(
            PortfolioProject.is_public == True,
            ~PortfolioProject.id.in_(
                select(UserProjectAssociation.project_id).filter(
                    UserProjectAssociation.user_id == current_user.id
                )
            ),
        )
        query = user_projects.union(public_projects)
    else:
        query = user_projects

    # Add search filters
    query = query.select(
        or_(
            PortfolioProject.project_name.ilike(f"%{search_term}%"),
            PortfolioProject.project_description.ilike(f"%{search_term}%"),
            PortfolioProject.project_category.ilike(f"%{search_term}%"),
        )
    )

    result = await db.execute(query)
    return result.scalars().all()


async def get_projects_by_status(
    is_completed: Optional[bool] = None,
    is_concept: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[PortfolioProjectBase]:
    """
    Filter projects by completion status and/or concept status.
    """
    query = (
        select(PortfolioProject)
        .join(UserProjectAssociation)
        .filter(UserProjectAssociation.user_id == current_user.id)
    )

    if is_completed is not None:
        query = query.filter(PortfolioProject.is_completed == is_completed)

    if is_concept is not None:
        query = query.filter(PortfolioProject.is_concept == is_concept)

    result = await db.execute(query)
    return result.scalars().all()


async def update_collaborator_permissions(
    project_id: uuid.UUID,
    username: str,
    role: Optional[str] = None,
    can_edit: Optional[bool] = None,
    contribution_description: Optional[str] = None,
    contribution: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Update a collaborator's permissions on a project.
    """
    # Verify requesting user has edit rights
    await verify_edit_permission(project_id, current_user, db)

    # Get the collaborator user
    collaborator = await get_user_by_username(username, db)

    # Get the existing association
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == collaborator.id,
            UserProjectAssociation.project_id == project_id,
        )
    )
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user is not a collaborator on the project",
        )

    # Update fields if provided
    if role is not None:
        association.role = role
    if can_edit is not None:
        association.can_edit = can_edit
    if contribution_description is not None:
        association.contribution_description = contribution_description
    if contribution is not None:
        association.contribution = contribution

    association.updated_at = datetime.now()
    await db.commit()

    return {"message": "Collaborator permissions updated successfully"}


async def get_recent_projects(
    days: int = 30,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[PortfolioProjectBase]:
    """
    Get recently created or updated projects.
    """
    cutoff_date = datetime.now() - timedelta(days=days)

    query = (
        select(PortfolioProject)
        .join(UserProjectAssociation)
        .filter(
            UserProjectAssociation.user_id == current_user.id,
            or_(
                PortfolioProject.created_at >= cutoff_date,
                PortfolioProject.updated_at >= cutoff_date,
            ),
        )
        .order_by(
            coalesce(PortfolioProject.updated_at, PortfolioProject.created_at).desc()
        )
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()


async def get_project_stats(
    user_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get statistics about projects (counts by status, visibility, etc.)
    """
    # Use current user if no user_id provided
    target_user_id = user_id if user_id else current_user.id

    # Verify requesting user has access (either self or public stats)
    if user_id and user_id != current_user.id:
        if not await db.scalar(
            select(User.is_public_profile).filter(User.id == user_id)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User profile is private"
            )

    # Build the stats query with coalesce to handle NULL values
    stats_query = (
        select(
            func.count().label("total_projects"),
            func.coalesce(
                func.sum(case((PortfolioProject.is_public == True, 1), else_=0)), 0
            ).label("public_projects"),
            func.coalesce(
                func.sum(case((PortfolioProject.is_completed == True, 1), else_=0)), 0
            ).label("completed_projects"),
            func.coalesce(
                func.sum(case((PortfolioProject.is_concept == True, 1), else_=0)), 0
            ).label("concept_projects"),
        )
        .select_from(PortfolioProject)
        .join(UserProjectAssociation)
        .filter(
            UserProjectAssociation.user_id == target_user_id,
            UserProjectAssociation.role == "owner",
        )
    )

    result = await db.execute(stats_query)
    stats = result.mappings().first() or {}  # Fallback to empty dict if None

    return {
        "total_projects": stats.get("total_projects", 0),
        "public_projects": stats.get("public_projects", 0),
        "private_projects": stats.get("total_projects", 0)
        - stats.get("public_projects", 0),
        "completed_projects": stats.get("completed_projects", 0),
        "active_projects": stats.get("total_projects", 0)
        - stats.get("completed_projects", 0),
        "concept_projects": stats.get("concept_projects", 0),
    }
