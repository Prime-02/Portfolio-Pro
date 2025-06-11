from app.models.schemas import (
    PortfolioProjectBase,
    PortfolioProjectUpdate,
    CollaboratorResponse,
    CollaboratorResponseUpdate,
)
from app.models.db_models import PortfolioProject, User, UserProjectAssociation
from typing import Dict, Union, List, Optional, Any, Sequence, Tuple
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.security import get_current_user
from app.database import get_db
import uuid
from datetime import datetime, timedelta
from sqlalchemy.sql import Select, union
from sqlalchemy import exists, literal_column, and_, or_, case, func
from app.core.user import get_user_by_username, verify_edit_permission
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.orm import aliased


async def get_common_params(
    data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[Dict[str, str], User, AsyncSession]]:
    return {"data": data, "user": user, "db": db}


# Helper function to get user ID from username (for backward compatibility)
async def get_username_by_userid(user_id: uuid.UUID, db: AsyncSession) -> Optional[str]:
    """
    Helper function to get user username from ID.
    Use this when you need to convert username to user_id for the optimized functions.
    """
    result = await db.execute(select(User.username).filter(User.id == user_id))
    user_name = result.scalar_one_or_none()
    return user_name


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
    if not all(
        k in project_data
        for k in ["project_name", "project_description", "project_category"]
    ):
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
    skip: int = 0,
    limit: int = 100,
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """Get paginated projects for the current user with total count.

    Returns:
        Tuple of (projects, total_count)
    """
    # Base count query for user's projects
    count_query = (
        select(func.count(PortfolioProject.id))
        .join(
            UserProjectAssociation,
            PortfolioProject.id == UserProjectAssociation.project_id,
        )
        .filter(UserProjectAssociation.user_id == user.id)
    )

    if include_public:
        # Count public projects that the user doesn't own
        public_count_query = select(func.count(PortfolioProject.id)).filter(
            PortfolioProject.is_public == True,
            ~PortfolioProject.id.in_(
                select(UserProjectAssociation.project_id).filter(
                    UserProjectAssociation.user_id == user.id,
                    UserProjectAssociation.role == "owner",
                )
            ),
        )
        # Execute both count queries and sum the results
        user_count = (await db.execute(count_query)).scalar_one()
        public_count = (await db.execute(public_count_query)).scalar_one()
        total_count = user_count + public_count
    else:
        total_count = (await db.execute(count_query)).scalar_one()

    # Get paginated results (same as before)
    query = (
        select(PortfolioProject)
        .join(
            UserProjectAssociation,
            PortfolioProject.id == UserProjectAssociation.project_id,
        )
        .filter(UserProjectAssociation.user_id == user.id)
        .offset(skip)
        .limit(limit)
    )

    if include_public:
        public_query = (
            select(PortfolioProject)
            .filter(
                PortfolioProject.is_public == True,
                ~PortfolioProject.id.in_(
                    select(UserProjectAssociation.project_id).filter(
                        UserProjectAssociation.user_id == user.id,
                        UserProjectAssociation.role == "owner",
                    )
                ),
            )
            .offset(skip)
            .limit(limit)
        )
        query = query.union(public_query)

    result = await db.execute(query)
    projects = result.scalars().all()

    return projects, total_count


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

    project.created_at = datetime.now()
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


# UPDATED: Added pagination to get_project_collaborators
async def get_project_collaborators(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[CollaboratorResponse], int]:
    """Get paginated collaborators for a project with total count"""
    # Check if project exists
    if not await db.scalar(select(exists().where(PortfolioProject.id == project_id))):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    # Count total collaborators
    count_query = (
        select(func.count(UserProjectAssociation.user_id))
        .where(UserProjectAssociation.project_id == project_id)
    )
    total_count = (await db.execute(count_query)).scalar_one()

    # Get paginated collaborators
    stmt = (
        select(
            User.id,
            User.username,
            UserProjectAssociation.role,
            UserProjectAssociation.can_edit,
            UserProjectAssociation.created_at,
            UserProjectAssociation.contribution_description,
            UserProjectAssociation.contribution,
        )
        .select_from(UserProjectAssociation)
        .join(User, UserProjectAssociation.user_id == User.id)
        .where(UserProjectAssociation.project_id == project_id)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    collaborators = result.all()

    collaborator_list = [
        CollaboratorResponse(
            username=row.username,
            user_id=row.id,
            role=row.role,
            can_edit=row.can_edit,
            created_at=row.created_at,
            contribution_description=row.contribution_description,
            contribution=row.contribution,
        )
        for row in collaborators
    ]

    return collaborator_list, total_count


async def add_collaborator(
    project_id: uuid.UUID,
    user_id: uuid.UUID,  # Changed from username to user_id
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
        user_id: The ID of the user to add as a collaborator (changed from username)
        role: The role of the collaborator (e.g., "contributor", "reviewer")
        can_edit: Whether the collaborator can edit the project
        contribution_description: Description of the collaborator's contribution
        contribution: The collaborator's contribution
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

    # Check if the collaborator user exists using user_id
    collaborator_exists = await db.scalar(select(exists().where(User.id == user_id)))
    if not collaborator_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is already a collaborator
    existing_association = await db.scalar(
        select(
            exists().where(
                and_(
                    UserProjectAssociation.user_id == user_id,
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
        user_id=user_id,
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
    user_id: uuid.UUID,  # Changed from username to user_id
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Remove a collaborator from a project if the requesting user is the owner.

    Args:
        project_id: The ID of the project to remove the collaborator from
        user_id: The ID of the user to remove as a collaborator (changed from username)
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

    # Check if the collaborator user exists using user_id
    collaborator_exists = await db.scalar(select(exists().where(User.id == user_id)))
    if not collaborator_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is actually a collaborator
    result = await db.execute(
        select(UserProjectAssociation).filter(
            UserProjectAssociation.user_id == user_id,
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
            UserProjectAssociation.user_id == user_id,
            UserProjectAssociation.project_id == project_id,
        )
    )
    await db.commit()

    return {"message": "Collaborator removed successfully"}


# UPDATED: Added pagination to get_all_projects_by_user
async def get_all_projects_by_user(
    user_id: uuid.UUID,  # Changed from username to user_id
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """
    Get paginated projects created by a specific user with total count.

    Args:
        user_id: ID of the user whose projects to retrieve (changed from username)
        db: Database session
        current_user: The currently authenticated user
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Tuple of (projects, total_count)

    Raises:
        HTTPException: If user not found or unauthorized to view private projects
    """
    # Check if the target user exists
    target_user_exists = await db.scalar(select(exists().where(User.id == user_id)))
    if not target_user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if current user is requesting their own projects
    is_self = current_user.id == user_id

    # Count total projects
    count_query = (
        select(func.count(PortfolioProject.id))
        .join(
            UserProjectAssociation,
            PortfolioProject.id == UserProjectAssociation.project_id,
        )
        .filter(
            UserProjectAssociation.user_id == user_id,
            UserProjectAssociation.role == "owner",
        )
    )

    if not is_self:
        count_query = count_query.filter(PortfolioProject.is_public == True)

    total_count = (await db.execute(count_query)).scalar_one()

    # Base query for projects owned by the target user
    query = (
        select(PortfolioProject)
        .join(
            UserProjectAssociation,
            PortfolioProject.id == UserProjectAssociation.project_id,
        )
        .filter(
            UserProjectAssociation.user_id == user_id,
            UserProjectAssociation.role == "owner",
        )
        .offset(skip)
        .limit(limit)
    )

    # If not requesting their own projects, filter for public projects only
    if not is_self:
        query = query.filter(PortfolioProject.is_public == True)

    result = await db.execute(query)
    projects = result.scalars().all()

    return projects, total_count


# UPDATED: Added pagination to search_projects
async def search_projects(
    search_term: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_public: bool = True,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """
    Search projects by name or description with pagination.
    Returns matching projects the user has access to plus public ones if requested.
    """
    # Create the search condition
    search_condition = or_(
        PortfolioProject.project_name.ilike(f"%{search_term}%"),
        PortfolioProject.project_description.ilike(f"%{search_term}%"),
        PortfolioProject.project_category.ilike(f"%{search_term}%"),
    )

    # Count queries
    user_count_query = (
        select(func.count(PortfolioProject.id))
        .join(UserProjectAssociation)
        .where(UserProjectAssociation.user_id == current_user.id)
        .where(search_condition)
    )

    if include_public:
        public_count_query = (
            select(func.count(PortfolioProject.id))
            .where(PortfolioProject.is_public == True)
            .where(
                ~PortfolioProject.id.in_(
                    select(UserProjectAssociation.project_id).where(
                        UserProjectAssociation.user_id == current_user.id
                    )
                )
            )
            .where(search_condition)
        )
        
        user_count = (await db.execute(user_count_query)).scalar_one()
        public_count = (await db.execute(public_count_query)).scalar_one()
        total_count = user_count + public_count
    else:
        total_count = (await db.execute(user_count_query)).scalar_one()

    # Base query for projects user has access to
    user_projects = (
        select(PortfolioProject)
        .join(UserProjectAssociation)
        .where(UserProjectAssociation.user_id == current_user.id)
        .where(search_condition)
    )

    if include_public:
        # Public projects query
        public_projects = (
            select(PortfolioProject)
            .where(PortfolioProject.is_public == True)
            .where(
                ~PortfolioProject.id.in_(
                    select(UserProjectAssociation.project_id).where(
                        UserProjectAssociation.user_id == current_user.id
                    )
                )
            )
            .where(search_condition)
        )

        # Combine using UNION and apply pagination
        combined = union(user_projects, public_projects).alias("combined_projects")
        PortfolioProjectAlias = aliased(PortfolioProject, combined)
        query = select(PortfolioProjectAlias).offset(skip).limit(limit)
    else:
        query = user_projects.offset(skip).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    return projects, total_count


# UPDATED: Added pagination to get_projects_by_status
async def get_projects_by_status(
    is_completed: Optional[bool] = None,
    is_concept: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """
    Filter projects by completion status and/or concept status with pagination.
    """
    # Count query
    count_query = (
        select(func.count(PortfolioProject.id))
        .join(UserProjectAssociation)
        .filter(UserProjectAssociation.user_id == current_user.id)
    )

    # Main query
    query = (
        select(PortfolioProject)
        .join(UserProjectAssociation)
        .filter(UserProjectAssociation.user_id == current_user.id)
    )

    if is_completed is not None:
        count_query = count_query.filter(PortfolioProject.is_completed == is_completed)
        query = query.filter(PortfolioProject.is_completed == is_completed)

    if is_concept is not None:
        count_query = count_query.filter(PortfolioProject.is_concept == is_concept)
        query = query.filter(PortfolioProject.is_concept == is_concept)

    # Get total count
    total_count = (await db.execute(count_query)).scalar_one()

    # Apply pagination to main query
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    return projects, total_count


async def verify_edit_permission(
    project_id: uuid.UUID, user: User, db: AsyncSession
) -> None:
    """Verify user has edit permissions on project."""
    # Correct way to select using ORM model
    stmt = select(UserProjectAssociation).where(
        UserProjectAssociation.user_id == user.id,
        UserProjectAssociation.project_id == project_id,
        UserProjectAssociation.can_edit == True,  # or whatever your permission check is
    )

    result = await db.execute(stmt)
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have edit permissions for this project",
        )


async def update_collaborator_permissions(
    project_id: uuid.UUID,
    user_id: uuid.UUID,  # Changed from username to user_id
    role: Optional[str] = None,
    can_edit: Optional[bool] = None,
    contribution_description: Optional[str] = None,
    contribution: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollaboratorResponseUpdate:
    """
    Update a collaborator's permissions on a project.
    """
    # Verify requesting user has edit rights
    await verify_edit_permission(project_id, current_user, db)

    # Check if the collaborator user exists using user_id
    collaborator_exists = await db.scalar(select(exists().where(User.id == user_id)))
    if not collaborator_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Correct select statement
    stmt = select(UserProjectAssociation).where(
        UserProjectAssociation.user_id == user_id,
        UserProjectAssociation.project_id == project_id,
    )

    result = await db.execute(stmt)
    association = result.scalars().first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user is not a collaborator on the project",
        )

    # Update fields if provided
    if role is not None:
        print("role exist")
        association.role = role
    if can_edit is not None:
        print("can edit exist")
        association.can_edit = can_edit
    if contribution_description is not None:
        print("contribution_description exist")
        association.contribution_description = contribution_description
    if contribution is not None:
        print("contribution exist")  # Fixed: corrected debug message
        association.contribution = contribution

    association.created_at = datetime.now()
    await db.commit()
    await db.refresh(association)  # Refresh to get updated values

    return CollaboratorResponseUpdate(
        message="Collaborator permissions updated successfully"
    )


# UPDATED: Added pagination to get_recent_projects
async def get_recent_projects(
    days: int = 30,
    limit: int = 10,
    skip: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """
    Get recently created or updated projects with pagination.
    """
    cutoff_date = datetime.now() - timedelta(days=days)

    # Count query
    count_query = (
        select(func.count(PortfolioProject.id))
        .join(UserProjectAssociation)
        .filter(
            UserProjectAssociation.user_id == current_user.id,
            or_(
                PortfolioProject.created_at >= cutoff_date,
                PortfolioProject.created_at >= cutoff_date,
            ),
        )
    )

    total_count = (await db.execute(count_query)).scalar_one()

    # Main query with pagination
    query = (
        select(PortfolioProject)
        .join(UserProjectAssociation)
        .filter(
            UserProjectAssociation.user_id == current_user.id,
            or_(
                PortfolioProject.created_at >= cutoff_date,
            ),
        )
        .order_by(
            coalesce(
                PortfolioProject.created_at, PortfolioProject.created_at
            ).desc()
        )
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    projects = result.scalars().all()

    return projects, total_count


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
