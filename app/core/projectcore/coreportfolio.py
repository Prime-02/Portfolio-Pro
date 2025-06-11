from typing import List, Optional
from app.models.schemas import PortfolioUpdate, PortfolioBase, PortfolioResponse
from app.models.db_models import (
    Portfolio,
    User,
    PortfolioProjectAssociation,
    PortfolioProject,
    UserProjectAssociation,
)
from sqlalchemy.future import select
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.database import get_db
from app.core.user import slugify
from sqlalchemy.orm import selectinload
from uuid import UUID


async def create_portfolio(
    portfolio_data: PortfolioBase,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """Create a new portfolio for the current user with proper validation and initialization."""
    # Validate input data
    if not portfolio_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio information is required",
        )
    if not portfolio_data.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Portfolio name is required"
        )

    # Check for existing portfolio with same name
    existing_portfolio = await db.execute(
        select(Portfolio)
        .where(Portfolio.name == portfolio_data.name)
        .where(Portfolio.user_id == user.id)
    )
    if existing_portfolio.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Portfolio '{portfolio_data.name}' already exists for this user",
        )

    # Create new portfolio
    new_portfolio = Portfolio(
        user_id=user.id,
        name=portfolio_data.name,
        slug=slugify(portfolio_data.name),
        description=portfolio_data.description,
        is_public=portfolio_data.is_public,
        cover_image_url=portfolio_data.cover_image_url,
        is_default=False,  # Explicitly set default status
    )

    db.add(new_portfolio)

    try:
        await db.commit()
        await db.refresh(new_portfolio)

        # If you want to include projects in the response (empty initially)
        # You would need to eager load the relationship even though it's empty
        portfolio_with_relations = await db.execute(
            select(Portfolio)
            .where(Portfolio.id == new_portfolio.id)
            .options(
                selectinload(Portfolio.project_associations).selectinload(
                    PortfolioProjectAssociation.project
                )
            )
        )
        portfolio = portfolio_with_relations.scalar_one()

        return PortfolioResponse.model_validate(portfolio)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating portfolio: {str(e)}",
        )


async def get_portfolio(
    portfolio_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """Get a specific portfolio by ID."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id)
        .where(Portfolio.user_id == user.id)
        .options(
            selectinload(Portfolio.project_associations).selectinload(
                PortfolioProjectAssociation.project
            )
        )
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    return PortfolioResponse.model_validate(portfolio)


async def get_public_portfolio_by_slug(
    portfolio_slug: str,
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """Get a public portfolio by slug."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.slug == portfolio_slug)
        .where(Portfolio.is_public == True)
        .options(
            selectinload(Portfolio.project_associations).selectinload(
                PortfolioProjectAssociation.project
            )
        )
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public portfolio not found",
        )

    return PortfolioResponse.model_validate(portfolio)


async def get_user_portfolios(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PortfolioResponse]:
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == user.id)
        .options(
            # Load owner (user) with profile
            selectinload(Portfolio.user).selectinload(User.profile),
            # Load projects with their users
            selectinload(Portfolio.project_associations)
            .selectinload(PortfolioProjectAssociation.project)
            .selectinload(PortfolioProject.user_associations)
            .selectinload(UserProjectAssociation.user),
        )
        .offset(skip)
        .limit(limit)
    )
    portfolios = result.scalars().all()

    # Calculate project counts
    for portfolio in portfolios:
        portfolio.project_count = len(portfolio.project_associations)

        # Ensure owner is properly set (should be automatic with from_attributes=True)
        portfolio.owner = portfolio.user

    return [PortfolioResponse.model_validate(p) for p in portfolios]


async def get_public_portfolios(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[PortfolioResponse]:
    """Get public portfolios."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.is_public == True)
        .order_by(Portfolio.created_at.desc())
        .offset(skip)
        .limit(limit)
        .options(
            # Load the owner (user) with profile
            selectinload(Portfolio.user).selectinload(User.profile),
            # Load projects
            selectinload(Portfolio.project_associations).selectinload(
                PortfolioProjectAssociation.project
            ),
        )
    )
    portfolios = result.scalars().all()

    # Set owner reference (same as in get_user_portfolios)
    for portfolio in portfolios:
        portfolio.project_count = len(portfolio.project_associations)
        portfolio.owner = portfolio.user  # This connects the relationship

    return [PortfolioResponse.model_validate(p) for p in portfolios]


async def update_portfolio(
    portfolio_id: UUID,
    portfolio_data: PortfolioUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioUpdate:
    """Update an existing portfolio."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id)
        .where(Portfolio.user_id == user.id)
        .options(
            selectinload(Portfolio.project_associations).selectinload(
                PortfolioProjectAssociation.project
            )
        )
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or you don't have permission to edit it",
        )

    # Check if new name already exists (if name is being updated)
    if portfolio_data.name and portfolio_data.name != portfolio.name:
        existing_portfolio = await db.execute(
            select(Portfolio)
            .where(Portfolio.name == portfolio_data.name)
            .where(Portfolio.user_id == user.id)
            .where(Portfolio.id != portfolio_id)
        )
        if existing_portfolio.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already have a portfolio with the name '{portfolio_data.name}'",
            )
        portfolio.name = portfolio_data.name
        portfolio.slug = slugify(portfolio_data.name)

    # Update other fields only if provided (not None)
    if portfolio_data.description is not None:
        portfolio.description = portfolio_data.description
    if portfolio_data.is_public is not None:
        portfolio.is_public = portfolio_data.is_public
    if portfolio_data.cover_image_url is not None:
        portfolio.cover_image_url = portfolio_data.cover_image_url

    await db.commit()
    await db.refresh(portfolio)

    # Replace the last line with:
    portfolio_dict = {
        "id": portfolio.id,
        "name": portfolio.name,
        "slug": portfolio.slug,
        "description": portfolio.description,
        "is_public": portfolio.is_public,
        "cover_image_url": portfolio.cover_image_url,
        "user_id": portfolio.user_id,
        # Explicitly load relationships if needed
        "projects": [{"id": p.id, "name": p.name} for p in portfolio.projects],
    }
    return PortfolioUpdate.model_validate(portfolio_dict)


async def delete_portfolio(
    portfolio_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a portfolio."""
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id)
        .where(Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or you don't have permission to delete it",
        )

    await db.delete(portfolio)
    await db.commit()

    return {"message": "Portfolio deleted successfully"}
