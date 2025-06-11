"""
Portfolio API Router

This module provides RESTful API endpoints for portfolio management, including creation,
retrieval, updating, and deletion of portfolios. All routes are prefixed with '/portfolios'.

Routes:
    POST /
        Create a new portfolio for the authenticated user.
        - Requires authentication
        - Returns: Newly created portfolio
        - Status Codes:
            201: Successfully created
            401: Unauthorized
            400: Invalid input data

    GET /my/portfolios
        Get all portfolios belonging to the authenticated user.
        - Requires authentication
        - Supports pagination via skip and limit parameters
        - Returns: List of user's portfolios
        - Status Codes:
            200: Success
            401: Unauthorized

    GET /public
        Get all public portfolios (no authentication required).
        - Supports pagination via skip and limit parameters
        - Returns: List of public portfolios
        - Status Codes:
            200: Success

    GET /public/{portfolio_slug}
        Get a specific public portfolio by its slug (no authentication required).
        - Returns: Public portfolio details
        - Status Codes:
            200: Success
            404: Portfolio not found or not public

    GET /{portfolio_id}
        Get a specific portfolio by ID (must be owner).
        - Requires authentication
        - Returns: Portfolio details
        - Status Codes:
            200: Success
            401: Unauthorized
            403: Forbidden (not owner)
            404: Portfolio not found

    PUT /{portfolio_id}
        Update an existing portfolio (must be owner).
        - Requires authentication
        - Returns: Updated portfolio details
        - Status Codes:
            200: Success
            400: Invalid input data
            401: Unauthorized
            403: Forbidden (not owner)
            404: Portfolio not found

    DELETE /{portfolio_id}
        Delete a portfolio (must be owner).
        - Requires authentication
        - Returns: No content
        - Status Codes:
            204: Successfully deleted
            401: Unauthorized
            403: Forbidden (not owner)
            404: Portfolio not found

Parameters:
    skip (int): Number of items to skip (for pagination)
    limit (int): Number of items to return (for pagination, max 100)
    portfolio_slug (str): Unique human-readable identifier for public portfolios
    portfolio_id (UUID): Unique identifier for portfolios
    portfolio_data: Portfolio data for creation/updating

Dependencies:
    get_current_user: Authentication dependency
    get_db: Database session dependency
"""





from app.core.projectcore.coreportfolio import (
    create_portfolio,
    get_portfolio,
    get_public_portfolios,
    get_public_portfolio_by_slug,  # Added this import
    get_user_portfolios,
    update_portfolio,
    delete_portfolio
)
from app.models.schemas import PortfolioUpdate, PortfolioBase, PortfolioResponse
from fastapi import APIRouter, status, Depends, Query
from typing import List
from app.core.security import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import User
from uuid import UUID 

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.post(
    "/",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new portfolio"
)
async def create_new_portfolio(
    portfolio_data: PortfolioBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new portfolio for the authenticated user"""
    return await create_portfolio(portfolio_data, current_user, db)


@router.get(
    "/my/portfolios",
    response_model=List[PortfolioResponse],
    summary="Get all portfolios for current user"
)
async def list_user_portfolios(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all portfolios belonging to the authenticated user"""
    return await get_user_portfolios(skip, limit, current_user, db)


@router.get(
    "/public",
    response_model=List[PortfolioResponse],
    summary="Get all public portfolios"
)
async def list_public_portfolios(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get all public portfolios (no authentication required)"""
    return await get_public_portfolios(skip, limit, db)


@router.get(
    "/public/{portfolio_slug}",
    response_model=PortfolioResponse,
    summary="Get a public portfolio by slug"
)
async def get_public_portfolio_by_slug_endpoint(
    portfolio_slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a public portfolio by slug (no authentication required)"""
    return await get_public_portfolio_by_slug(portfolio_slug, db)


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Get a specific portfolio"
)
async def get_specific_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific portfolio by ID (must be owner)"""
    return await get_portfolio(portfolio_id, current_user, db)


@router.put(
    "/{portfolio_id}",
    response_model=PortfolioUpdate,
    summary="Update a portfolio"
)
async def update_existing_portfolio(
    portfolio_id: UUID,
    portfolio_data: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing portfolio (must be owner)"""
    return await update_portfolio(portfolio_id, portfolio_data, current_user, db)


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a portfolio"
)
async def remove_portfolio(
    portfolio_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a portfolio (must be owner)"""
    await delete_portfolio(portfolio_id, current_user, db)
    return None