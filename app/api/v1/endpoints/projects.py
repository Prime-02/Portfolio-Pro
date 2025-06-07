from fastapi import APIRouter, status, Depends, Query, HTTPException
from typing import Dict, Union, List, Sequence, Optional
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
    portfolio_data: Dict[str, str],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectBase:
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
    user: User = Depends(optional_current_user),  # Optional auth
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


@router.put(
    "/{project_id}",
    response_model=PortfolioProjectBase,
    status_code=status.HTTP_200_OK,
    summary="Update a project",
)
async def update_portfolio_project(
    project_id: UUID,
    project_data: PortfolioProjectUpdate,
    user: User = Depends(get_current_user),  # Requires auth
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectBase:
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
    username: str = Query(..., description="Username of the collaborator to add"),
    role: str = Query(
        ..., description="Role of the collaborator (e.g., 'contributor')"
    ),
    can_edit: bool = Query(
        ..., description="Whether collaborator can edit the project"
    ),
    contribution_description: Optional[str] = Query(
        None, description="Description of the collaborator's contribution"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Add a collaborator to a project (requires edit permissions)"""
    return await add_collaborator(
        project_id=project_id,
        username=username,
        role=role,
        can_edit=can_edit,
        contribution_description=contribution_description,
        user=user,
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
