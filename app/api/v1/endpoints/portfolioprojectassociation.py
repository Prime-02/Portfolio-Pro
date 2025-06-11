from app.core.projectcore.coreportfolioprojectassociation import (
    create_association,
    delete_association,
    update_association,
    get_association,
    get_association_stats,
    get_portfolio_associations,
    reorder_associations,
    bulk_add_projects
)
from fastapi import APIRouter, status, Depends, Query, HTTPException
from typing import Dict, Union, List, Sequence, Optional, Any, Tuple
from app.models.schemas import (
    PortfolioProjectAssociationCreate,
    PortfolioProjectAssociationUpdate,
    PortfolioProjectAssociation as PortfolioProjectAssociationSchema,
)
from app.models.db_models import PortfolioProject, User, PortfolioProjectAssociation
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select
from datetime import datetime
import uuid
from app.core.security import get_current_user
from app.database import get_db
from sqlalchemy import or_, and_


router = APIRouter(prefix="/associations", tags=["portfolio-project-associations"])

@router.post(
    "/",
    response_model=PortfolioProjectAssociationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new portfolio-project association"
)
async def create_portfolio_project_association(
    association_data: PortfolioProjectAssociationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_association(association_data, user, db)

@router.get(
    "/{association_id}",
    response_model=PortfolioProjectAssociationSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a specific portfolio-project association"
)
async def get_portfolio_project_association(
    association_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_association(association_id, user, db)

@router.get(
    "/portfolio/{portfolio_id}",
    response_model=List[PortfolioProjectAssociationSchema],
    status_code=status.HTTP_200_OK,
    summary="Get all associations for a portfolio"
)
async def get_all_portfolio_associations(
    portfolio_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_portfolio_associations(portfolio_id, user, db, skip, limit)

@router.put(
    "/{association_id}",
    response_model=PortfolioProjectAssociationSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a portfolio-project association"
)
async def update_portfolio_project_association(
    association_id: UUID,
    update_data: PortfolioProjectAssociationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await update_association(association_id, update_data, user, db)

@router.delete(
    "/{association_id}",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Delete a portfolio-project association"
)
async def delete_portfolio_project_association(
    association_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await delete_association(association_id, user, db)

@router.post(
    "/portfolio/{portfolio_id}/reorder",
    response_model=List[PortfolioProjectAssociationSchema],
    status_code=status.HTTP_200_OK,
    summary="Reorder associations in a portfolio"
)
async def reorder_portfolio_associations(
    portfolio_id: UUID,
    new_positions: List[Dict[str, Union[UUID, int]]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await reorder_associations(portfolio_id, new_positions, user, db)

@router.post(
    "/portfolio/{portfolio_id}/bulk",
    response_model=List[PortfolioProjectAssociationSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add projects to a portfolio"
)
async def bulk_add_projects_to_portfolio(
    portfolio_id: UUID,
    project_data: List[PortfolioProjectAssociationCreate],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await bulk_add_projects(portfolio_id, project_data, user, db)

@router.get(
    "/portfolio/{portfolio_id}/stats",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get statistics about a portfolio's associations"
)
async def get_portfolio_association_stats(
    portfolio_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_association_stats(portfolio_id, user, db)