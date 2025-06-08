"""
project_routes = [
    {"method": "POST", "path": "/projects/", "summary": "Add a new project"},
    {"method": "POST", "path": "/projects/{project_id}/collaborators", "summary": "Add a collaborator to a project"},

    {"method": "GET", "path": "/projects/", "summary": "Get all visible projects"},
    {"method": "GET", "path": "/projects/{project_id}", "summary": "Get a specific project by ID"},
    {"method": "GET", "path": "/projects/user/{username}", "summary": "Get all projects by a specific user"},
    {"method": "GET", "path": "/projects/my/projects", "summary": "Get current user's projects"},
    {"method": "GET", "path": "/projects/search", "summary": "Search projects by name or description"},
    {"method": "GET", "path": "/projects/filter/status", "summary": "Filter projects by completion and concept status"},
    {"method": "GET", "path": "/projects/recent", "summary": "Get recently created or updated projects"},
    {"method": "GET", "path": "/projects/stats", "summary": "Get project statistics"},
    {"method": "GET", "path": "/projects/{project_id}/collaborators", "summary": "Get project collaborators"},

    {"method": "PUT", "path": "/projects/{project_id}", "summary": "Update a project"},
    {"method": "PUT", "path": "/projects/{project_id}/collaborators/{username}", "summary": "Update collaborator permissions"},

    {"method": "DELETE", "path": "/projects/{project_id}", "summary": "Delete a project"},
    {"method": "DELETE", "path": "/projects/{project_id}/collaborators/{username}", "summary": "Remove a collaborator from a project"},
]

"""

from fastapi import APIRouter, status, Depends, Query, HTTPException
from typing import Dict, Union, List, Sequence, Optional, Any
from app.models.schemas import (
    PortfolioProjectBase,
    PortfolioProjectUpdate,
    CollaboratorResponse,
)
from app.models.db_models import PortfolioProject, User, UserProjectAssociation
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select
from datetime import datetime
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
)
async def get_all_projects(
    user: Optional[User] = Depends(optional_current_user),  # Optional auth
    db: AsyncSession = Depends(get_db),
    include_private: bool = Query(
        default=False, description="Include private projects you have access to"
    ),
) -> Sequence[PortfolioProjectBase]:
    # Base query for public projects
    query = select(PortfolioProject).filter(PortfolioProject.is_public == True)

    # If user is authenticated and wants to include private projects
    if user and include_private:
        # Get projects where:
        # - either public OR
        # - private but user has access
        query = (
            select(PortfolioProject)
            .join(
                UserProjectAssociation,
                PortfolioProject.id == UserProjectAssociation.project_id,
                isouter=True,
            )
            .filter(
                or_(
                    PortfolioProject.is_public == True,
                    and_(
                        PortfolioProject.is_public == False,
                        UserProjectAssociation.user_id == user.id,
                    ),
                )
            )
            .distinct()
        )

    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/user/{username}",
    response_model=Sequence[PortfolioProjectBase],
    status_code=status.HTTP_200_OK,
    summary="Get all projects by a specific user",
)
async def get_projects_by_username(
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[PortfolioProjectBase]:
    """Get all projects created by a specific user."""
    return await get_all_projects_by_user(username, db, current_user)


@router.get(
    "/my/projects",
    response_model=Sequence[PortfolioProjectBase],
    status_code=status.HTTP_200_OK,
    summary="Get current user's projects",
)
async def get_my_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_public: bool = Query(
        default=False, description="Include public projects from other users"
    ),
) -> Sequence[PortfolioProjectBase]:
    """Get all projects for the current authenticated user."""
    return await get_all_user_projects(user, db, include_public)


@router.get(
    "/search",
    response_model=Sequence[PortfolioProjectBase],
    status_code=status.HTTP_200_OK,
    summary="Search projects by name or description",
)
async def search_portfolio_projects(
    q: str = Query(..., description="Search term for project name or description"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_public: bool = Query(
        default=True, description="Include public projects in search results"
    ),
) -> Sequence[PortfolioProjectBase]:
    """Search projects by name or description."""
    return await search_projects(q, db, user, include_public)


@router.get(
    "/filter/status",
    response_model=Sequence[PortfolioProjectBase],
    status_code=status.HTTP_200_OK,
    summary="Filter projects by completion and concept status",
)
async def filter_projects_by_status(
    is_completed: Optional[bool] = Query(
        default=None, description="Filter by completion status"
    ),
    is_concept: Optional[bool] = Query(
        default=None, description="Filter by concept status"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[PortfolioProjectBase]:
    """Filter projects by completion status and/or concept status."""
    return await get_projects_by_status(is_completed, is_concept, db, user)


@router.get(
    "/recent",
    response_model=Sequence[PortfolioProjectBase],
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Sequence[PortfolioProjectBase]:
    """Get recently created or updated projects."""
    return await get_recent_projects(days, limit, db, user)


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
    response_model=List[CollaboratorResponse],
    status_code=status.HTTP_200_OK,
    summary="Get project collaborators",
)
async def get_portfolio_project_collaborators(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[CollaboratorResponse]:
    return await get_project_collaborators(project_id, db)


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
        username=request.username,
        role=request.role,
        can_edit=request.can_edit,
        contribution_description=request.contribution_description,
        contribution=request.contribution,
        user=user,
        db=db
    )


@router.put(
    "/{project_id}/collaborators/{username}",
    status_code=status.HTTP_200_OK,
    summary="Update collaborator permissions",
)
async def update_project_collaborator_permissions(
    project_id: UUID,
    username: str,
    role: Optional[str] = Query(
        default=None, description="New role for the collaborator"
    ),
    can_edit: Optional[bool] = Query(default=None, description="Edit permissions"),
    contribution_description: Optional[str] = Query(
        default=None, description="Updated contribution description"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Update a collaborator's permissions on a project."""
    return await update_collaborator_permissions(
        project_id=project_id,
        username=username,
        role=role,
        can_edit=can_edit,
        contribution_description=contribution_description,
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/{project_id}/collaborators/{username}",
    status_code=status.HTTP_200_OK,
    summary="Remove a collaborator from a project",
)
async def remove_project_collaborator(
    project_id: UUID,
    username: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Remove a collaborator from a project (requires owner permissions)"""
    return await remove_collaborator(
        project_id=project_id, username=username, user=user, db=db
    )
