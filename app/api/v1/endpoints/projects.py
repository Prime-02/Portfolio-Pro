"""
Project Management Routes

This module provides API endpoints for managing portfolio projects and their collaborators.
All routes require authentication unless otherwise noted.

Routes:

CREATE OPERATIONS:
1. POST /projects/
   - Summary: Add a new project
   - Description: Creates a new portfolio project with the provided data. The authenticated user becomes the owner.
   - Request Body: Project details (project_name, project_description, project_category, project_url, project_image_url, is_public, is_completed, is_concept .)
   - Returns: The created project with generated ID and timestamps

2. POST /projects/{project_id}/collaborators
   - Summary: Add a collaborator to a project
   - Description: Adds a user as a collaborator to the specified project. Requires edit permissions.
   - Path Parameters: project_id (UUID)
   - Request Body: Collaborator details (user_id, username, role, can_edit, created_at, contribution_description, contribution )
   - Returns: Success message with collaborator details

READ OPERATIONS:
3. GET /projects/
   - Summary: Get all visible projects
   - Description: Returns paginated list of projects visible to the user. Public projects are always included.
   - Query Parameters:
     - include_private: bool (default False) - Include private projects you have access to
     - skip: int (pagination offset)
     - limit: int (max items per page, 1-100)
   - Returns: List of projects with pagination info

4. GET /projects/{project_id}
   - Summary: Get a specific project by ID
   - Description: Returns full details of a project. Private projects require authentication and access.
   - Path Parameters: project_id (UUID)
   - Returns: Complete project details

5. GET /projects/user/{user_id}
   - Summary: Get all projects by a specific user
   - Description: Returns paginated projects created by the specified user. Only includes public projects unless requesting your own.
   - Path Parameters: user_id (UUID)
   - Query Parameters: skip, limit (pagination)
   - Returns: List of projects with total count

6. GET /projects/my/projects
   - Summary: Get current user's projects
   - Description: Returns paginated projects owned by or shared with the authenticated user.
   - Query Parameters:
     - include_public: bool (include public projects from others)
     - skip, limit (pagination)
   - Returns: List of projects with total count

7. GET /projects/search
   - Summary: Search projects by name or description
   - Description: Searches project names/descriptions using the provided term.
   - Query Parameters:
     - search_term: str (required)
     - include_public: bool (include public projects)
     - skip, limit (pagination)
   - Returns: Matching projects with total count

8. GET /projects/filter/status
   - Summary: Filter projects by completion and concept status
   - Description: Filters projects based on is_completed and/or is_concept flags.
   - Query Parameters:
     - is_completed: Optional[bool]
     - is_concept: Optional[bool]
     - skip, limit (pagination)
   - Returns: Filtered projects with total count

9. GET /projects/recent
   - Summary: Get recently created or updated projects
   - Description: Returns projects modified within the specified timeframe.
   - Query Parameters:
     - days: int (1-365, default 30)
     - limit: int (max items)
     - skip: int (pagination offset)
   - Returns: Recent projects with total count

10. GET /projects/stats
    - Summary: Get project statistics
    - Description: Returns aggregate statistics about projects (counts by status, visibility, etc.)
    - Query Parameters:
      - user_id: Optional[UUID] (defaults to current user)
    - Returns: Dictionary of statistical metrics

11. GET /projects/{project_id}/collaborators
    - Summary: Get project collaborators
    - Description: Returns paginated list of collaborators for a project.
    - Path Parameters: project_id (UUID)
    - Query Parameters: skip, limit (pagination)
    - Returns: List of collaborators with total count

UPDATE OPERATIONS:
12. PUT /projects/{project_id}
    - Summary: Update a project
    - Description: Modifies project details. Requires owner or edit permissions.
    - Path Parameters: project_id (UUID)
    - Request Body: Updated project fields
    - Returns: Updated project details

13. PUT /projects/{project_id}/collaborators/{user_id}
    - Summary: Update collaborator permissions
    - Description: Modifies a collaborator's role or permissions. Requires owner permissions.
    - Path Parameters: See No 2 for editable data
    - Request Body: Updated collaborator details
    - Returns: Updated collaborator record

DELETE OPERATIONS:
14. DELETE /projects/{project_id}
    - Summary: Delete a project
    - Description: Permanently deletes a project and its associations. Requires owner permissions.
    - Path Parameters: project_id (UUID)
    - Returns: Success message

15. DELETE /projects/{project_id}/collaborators/{user_id}
    - Summary: Remove a collaborator from a project
    - Description: Removes a user's collaboration from a project. Requires owner permissions.
    - Path Parameters: project_id, user_id (UUIDs)
    - Returns: Success message

Authentication:
- Most routes require valid JWT token (except public GET endpoints)
- Optional authentication is supported for some public read operations

Error Responses:
- 401 Unauthorized: Missing or invalid credentials
- 403 Forbidden: Insufficient permissions
- 404 Not Found: Resource doesn't exist or not accessible
"""

from fastapi import APIRouter, status, Depends, Query, HTTPException
from typing import Dict, Union, List, Sequence, Optional, Any, Tuple
from app.models.schemas import (
    PortfolioProjectBase,
    PortfolioProjectUpdate,
    CollaboratorResponse,
    CollaboratorResponseUpdate,
    PortfolioProjectWithUsers,
)
from app.models.db_models import PortfolioProject, User, UserProjectAssociation
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select
from datetime import datetime
import uuid
from sqlalchemy.orm import selectinload
from app.core.projectcore.coreproject import (
    add_project,
    get_project_by_id,
    get_all_user_projects,
    update_project,
    delete_project,
    get_project_collaborators,
    remove_collaborator,
    add_collaborator,
    get_all_projects_by_user,
    search_projects,
    get_projects_by_status,
    update_collaborator_permissions,
    get_recent_projects,
    get_project_stats,
)
from app.core.security import get_current_user, optional_current_user
from app.database import get_db
from sqlalchemy import or_, and_


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "/search",
    response_model=Tuple[Sequence[PortfolioProjectBase], int],
    status_code=status.HTTP_200_OK,
    summary="Search projects by name or description",
    description="""Searches for portfolio projects matching a given search term in their name or description.
    Supports pagination via `skip` and `limit` parameters.
    """,
)
async def search_portfolio_projects(
    search_term: str = Query(
        ..., description="Search term to match against project names or descriptions"
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    include_public: bool = Query(
        default=True,
        description="If True, includes public projects in search results (even if not owned by the user)",
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip (for pagination). Defaults to 0.",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of records to return (for pagination). Defaults to 10, max 100.",
    ),
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """Search projects by name or description.

    Args:
        search_term (str): The text to search for in project names/descriptions.
        include_public (bool): Whether to include public projects in results.
        skip (int): Pagination offset (number of records to skip).
        limit (int): Maximum number of records to return per page.

    Returns:
        Tuple[Sequence[PortfolioProjectBase], int]: A tuple containing:
            - List of matching projects
            - Total count of matching projects (for pagination)
    """
    return await search_projects(search_term, db, user, include_public, skip, limit)


@router.get(
    "/recent",
    response_model=Tuple[Sequence[PortfolioProjectBase], int],
    status_code=status.HTTP_200_OK,
    summary="Get recently created or updated projects",
)
async def get_recent_portfolio_projects(
    days: int = Query(
        default=30, ge=1, le=365, description="Number of days to look back"
    ),
    limit: int = Query(
        default=10, ge=1, le=100, description="Maximum number of projects to return"
    ),
    skip: int = Query(
        default=0, ge=0, description="Number of records to skip for pagination"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """Get recently created or updated projects."""
    return await get_recent_projects(days, limit, skip, db, user)


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get project statistics",
)
async def get_portfolio_project_stats(
    user_id: Optional[UUID] = Query(
        default=None, description="User ID to get stats for (defaults to current user)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get statistics about projects (counts by status, visibility, etc.)."""
    return await get_project_stats(user_id, db, current_user)


@router.get(
    "/filter/status",
    response_model=Tuple[Sequence[PortfolioProjectBase], int],
    status_code=status.HTTP_200_OK,
    summary="Filter projects by completion and concept status",
    description="""Filters portfolio projects based on completion status (`is_completed`) 
    and/or concept status (`is_concept`). Supports pagination via `skip` and `limit`.
    """,
)
async def filter_projects_by_status(
    is_completed: Optional[bool] = Query(
        default=None,
        description="Filter projects by completion status (True=completed, False=in-progress).",
    ),
    is_concept: Optional[bool] = Query(
        default=None,
        description="Filter projects by concept status (True=concept, False=executed).",
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip (pagination offset). Defaults to 0.",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of records to return per page. Defaults to 10, max 100.",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """Filter projects by completion status and/or concept status.

    Args:
        is_completed (Optional[bool]): If provided, filters by completion status.
        is_concept (Optional[bool]): If provided, filters by concept status.
        skip (int): Pagination offset (records to skip). Default 0.
        limit (int): Maximum records per page. Default 10, max 100.

    Returns:
        Tuple[Sequence[PortfolioProjectBase], int]:
            - Filtered projects (paginated).
            - Total count of matching projects (for pagination).
    """
    return await get_projects_by_status(is_completed, is_concept, db, user, skip, limit)


@router.get(
    "/my/projects",
    response_model=Tuple[Sequence[PortfolioProjectBase], int],
    status_code=status.HTTP_200_OK,
    summary="Get current user's projects",
)
async def get_my_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_public: bool = Query(
        default=False, description="Include public projects from other users"
    ),
    skip: int = Query(
        default=0, ge=0, description="Number of items to skip (for pagination)"
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to return (for pagination)",
    ),
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """Get paginated projects for the current authenticated user.

    Parameters:
    - include_public: Whether to include public projects from other users
    - skip: Number of items to skip (pagination offset)
    - limit: Maximum number of items to return per page
    """
    return await get_all_user_projects(
        user=user, db=db, include_public=include_public, skip=skip, limit=limit
    )


@router.post(
    "/",
    response_model=PortfolioProjectBase,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new project",
)
async def create_portfolio_project(
    portfolio_data: Dict[str, Union[str, bool]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioProject:
    commons = {"data": portfolio_data, "user": user, "db": db}
    return await add_project(commons)


@router.get(
    "/{project_id}",
    response_model=PortfolioProjectBase,
    status_code=status.HTTP_200_OK,
    summary="Get a specific project by ID",
)
async def get_portfolio_project(
    project_id: UUID,
    user: User = Depends(optional_current_user),  # Now accepts optional auth
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectBase:
    # Get the project first
    result = await db.execute(
        select(PortfolioProject).filter(PortfolioProject.id == project_id)
    )
    project = result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Check visibility
    if not project.is_public:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This project is private"
            )

        # Check if user has access
        result = await db.execute(
            select(UserProjectAssociation).filter(
                UserProjectAssociation.user_id == user.id,
                UserProjectAssociation.project_id == project_id,
            )
        )
        if not result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this private project",
            )

    return project


@router.get(
    "/",
    response_model=Sequence[PortfolioProjectBase],
    status_code=status.HTTP_200_OK,
    summary="Get all visible projects",
    description="""Returns paginated list of projects visible to the user.
    Public projects are always included. Private projects are included only if:
    - User is authenticated
    - include_private=True
    - User has access to the private project
    """,
)
@router.get(
    "/",
    response_model=List[
        PortfolioProjectWithUsers
    ],  # Changed to List for clearer typing
    status_code=status.HTTP_200_OK,
    summary="Get all visible projects with associated users",
    description="""Returns paginated list of projects visible to the user with their associated users.
    Public projects are always included. Private projects are included only if:
    - User is authenticated
    - include_private=True
    - User has access to the private project
    """,
)
async def get_all_projects_with_users(
    user: Optional[User] = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
    include_private: bool = Query(
        default=False,
        description="Include private projects you have access to (requires auth)",
    ),
    skip: int = Query(
        default=0, ge=0, description="Number of items to skip for pagination"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of items to return (1-100)",
    ),
) -> List[PortfolioProjectWithUsers]:
    # Base query for public projects with eager loading of users
    query = (
        select(PortfolioProject)
        .options(
            selectinload(PortfolioProject.user_associations).selectinload(
                UserProjectAssociation.user
            )
        )
        .filter(PortfolioProject.is_public == True)
    )

    # If user is authenticated and wants to include private projects
    if user and include_private:
        # Get distinct project IDs that user has access to
        subquery = (
            select(UserProjectAssociation.project_id)
            .filter(UserProjectAssociation.user_id == user.id)
            .distinct()
            .subquery()
        )

        query = (
            select(PortfolioProject)
            .options(
                selectinload(PortfolioProject.user_associations).selectinload(
                    UserProjectAssociation.user
                )
            )
            .filter(
                or_(
                    PortfolioProject.is_public == True,
                    PortfolioProject.id.in_(subquery),
                )
            )
        )

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    # The SQLAlchemy models will have users loaded via the association
    # Pydantic will automatically convert them using PortfolioProjectWithUsers model
    return projects


@router.get(
    "/user/{user_id}",
    response_model=Tuple[Sequence[PortfolioProjectBase], int],
    status_code=status.HTTP_200_OK,
    summary="Get all projects by a specific user",
)
async def get_projects_by_username(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(
        default=0, ge=0, description="Number of items to skip for pagination"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of items to return (1-100)",
    ),
) -> Tuple[Sequence[PortfolioProjectBase], int]:
    """Get all projects created by a specific user."""
    return await get_all_projects_by_user(
        user_id, db, current_user, skip=skip, limit=limit
    )


@router.put(
    "/{project_id}",
    response_model=PortfolioProjectUpdate,
    status_code=status.HTTP_200_OK,
    summary="Update a project",
)
async def update_portfolio_project(
    project_id: UUID,
    project_data: PortfolioProjectUpdate,
    user: User = Depends(get_current_user),  # Requires auth
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectUpdate:
    return await update_project(project_id, project_data, user, db)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a project",
)
async def delete_portfolio_project(
    project_id: UUID,
    user: User = Depends(get_current_user),  # Requires auth
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    return await delete_project(project_id, user, db)


@router.get(
    "/{project_id}/collaborators",
    response_model=Tuple[List[CollaboratorResponse], int],
    status_code=status.HTTP_200_OK,
    summary="Get project collaborators",
)
async def get_portfolio_project_collaborators(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(
        default=0, ge=0, description="Number of items to skip for pagination"
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of items to return (1-100)",
    ),
) -> Tuple[List[CollaboratorResponse], int]:
    return await get_project_collaborators(project_id, db, skip, limit)


@router.post(
    "/{project_id}/collaborators",
    status_code=status.HTTP_201_CREATED,
    summary="Add a collaborator to a project",
)
async def add_project_collaborator(
    project_id: UUID,
    request: CollaboratorResponse,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[str, bool, datetime]]:
    """Add a collaborator to a project (requires edit permissions)"""
    return await add_collaborator(
        project_id=project_id,
        user_id=request.user_id,
        role=request.role,
        can_edit=request.can_edit,
        contribution_description=request.contribution_description,
        contribution=request.contribution,
        user=user,
        db=db,
    )


@router.put(
    "/{project_id}/collaborators/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Update collaborator permissions",
)
async def update_project_collaborator_permissions(
    project_id: UUID,
    user_id: UUID,
    update_data: CollaboratorResponseUpdate,  # ← Now expects JSON body
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollaboratorResponseUpdate:
    return await update_collaborator_permissions(
        project_id=project_id,
        user_id=user_id,
        role=update_data.role,
        can_edit=update_data.can_edit,
        contribution_description=update_data.contribution_description,
        contribution=update_data.contribution,
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/{project_id}/collaborators/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a collaborator from a project",
)
async def remove_project_collaborator(
    project_id: UUID,
    user_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Remove a collaborator from a project (requires owner permissions)"""
    return await remove_collaborator(
        project_id=project_id, user_id=user_id, user=user, db=db
    )
