from app.models.schemas import (
    PortfolioProjectAssociationCreate,
    PortfolioProjectAssociationUpdate,
    PortfolioProjectAssociation as PortfolioProjectAssociationSchema,
)
from app.models.db_models import (
    Portfolio,
    User,
    PortfolioProjectAssociation,
    PortfolioProject,
)
from typing import Dict, Union, List, Optional, Any, Sequence, Tuple
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from app.core.security import get_current_user
from app.database import get_db
from uuid import UUID
from sqlalchemy.sql import Select, union
from sqlalchemy import  func
from sqlalchemy.orm import selectinload


async def create_association(
    association_data: PortfolioProjectAssociationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectAssociationSchema:
    """
    Creates a validated association between a project and portfolio with:
    - Ownership verification
    - Project visibility checks
    - Duplicate prevention
    - Automatic position handling
    """
    # Portfolio verification
    portfolio_result = await db.execute(
        select(Portfolio)
        .where(Portfolio.id == association_data.portfolio_id)
    )
    portfolio: Optional[Portfolio] = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    if str(portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add projects to another user's portfolio"
        )

    # Project verification with eager-loaded relationships
    project_result = await db.execute(
        select(PortfolioProject)
        .options(selectinload(PortfolioProject.user_associations))
        .where(PortfolioProject.id == association_data.project_id)
    )
    project: Optional[PortfolioProject] = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Duplicate check
    existing_assoc_result = await db.execute(
        select(PortfolioProjectAssociation)
        .where(
            PortfolioProjectAssociation.project_id == association_data.project_id,
            PortfolioProjectAssociation.portfolio_id == association_data.portfolio_id
        )
    )
    if existing_assoc_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project already exists in this portfolio"
        )

    # Calculate position if not provided
    position = association_data.position
    if position is None or position == 0:
        max_pos_result = await db.execute(
            select(func.max(PortfolioProjectAssociation.position))
            .where(PortfolioProjectAssociation.portfolio_id == association_data.portfolio_id)
        )
        position = (max_pos_result.scalar() or 0) + 1

    # Create association
    try:
        association = PortfolioProjectAssociation(
            project_id=association_data.project_id,
            portfolio_id=association_data.portfolio_id,
            position=position,
            notes=association_data.notes
        )

        db.add(association)
        await db.commit()
        await db.refresh(association)
        return PortfolioProjectAssociationSchema.model_validate(association)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create association: {str(e)}"
        )


async def get_association(
    association_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectAssociationSchema:
    """
    Retrieves a specific portfolio-project association by ID with permission checks.
    """
    result = await db.execute(
        select(PortfolioProjectAssociation)
        .options(
            selectinload(PortfolioProjectAssociation.portfolio),
            selectinload(PortfolioProjectAssociation.project)
        )
        .where(PortfolioProjectAssociation.id == association_id)
    )
    association = result.scalar_one_or_none()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found"
        )

    # Check if user owns the portfolio
    if str(association.portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's portfolio associations"
        )

    return PortfolioProjectAssociationSchema.model_validate(association)


async def get_portfolio_associations(
    portfolio_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> List[PortfolioProjectAssociationSchema]:
    """
    Retrieves all associations for a specific portfolio with pagination.
    """
    # Verify portfolio ownership
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    if str(portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's portfolio"
        )

    # Get associations ordered by position
    result = await db.execute(
        select(PortfolioProjectAssociation)
        .options(
            selectinload(PortfolioProjectAssociation.project),
            selectinload(PortfolioProjectAssociation.portfolio)
        )
        .where(PortfolioProjectAssociation.portfolio_id == portfolio_id)
        .order_by(PortfolioProjectAssociation.position)
        .offset(skip)
        .limit(limit)
    )

    associations = result.scalars().all()
    return [PortfolioProjectAssociationSchema.model_validate(assoc) for assoc in associations]


async def update_association(
    association_id: UUID,
    update_data: PortfolioProjectAssociationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioProjectAssociationSchema:
    """
    Updates a portfolio-project association with validation.
    Allows updating position and notes.
    """
    # Get existing association
    result = await db.execute(
        select(PortfolioProjectAssociation)
        .options(selectinload(PortfolioProjectAssociation.portfolio))
        .where(PortfolioProjectAssociation.id == association_id)
    )
    association = result.scalar_one_or_none()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found"
        )

    # Check ownership
    if str(association.portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify another user's portfolio associations"
        )

    # Validate and apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    # If updating position, validate it's reasonable
    if "position" in update_dict:
        new_position = update_dict["position"]
        if new_position is not None and new_position < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Position must be a positive integer"
            )

    try:
        # Update the association
        await db.execute(
            update(PortfolioProjectAssociation)
            .where(PortfolioProjectAssociation.id == association_id)
            .values(**update_dict)
        )

        await db.commit()

        # Refresh and return updated association
        await db.refresh(association)
        return PortfolioProjectAssociationSchema.model_validate(association)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update association: {str(e)}"
        )


async def delete_association(
    association_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Deletes a portfolio-project association with ownership verification.
    """
    # Get association with portfolio info
    result = await db.execute(
        select(PortfolioProjectAssociation)
        .options(selectinload(PortfolioProjectAssociation.portfolio))
        .where(PortfolioProjectAssociation.id == association_id)
    )
    association = result.scalar_one_or_none()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found"
        )

    # Check ownership
    if str(association.portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's portfolio associations"
        )

    try:
        await db.execute(
            delete(PortfolioProjectAssociation)
            .where(PortfolioProjectAssociation.id == association_id)
        )
        await db.commit()

        return {"message": "Association deleted successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete association: {str(e)}"
        )


# Utility functions for improved user experience

async def reorder_associations(
    portfolio_id: UUID,
    association_positions: List[Dict[str, Union[UUID, int]]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PortfolioProjectAssociationSchema]:
    """
    Reorders multiple associations in a portfolio.
    
    Args:
        association_positions: List of dicts with 'association_id' and 'position'
    """
    # Verify portfolio ownership
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    if str(portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reorder another user's portfolio"
        )

    # Validate all associations belong to this portfolio
    association_ids = [item["association_id"] for item in association_positions]
    existing_result = await db.execute(
        select(PortfolioProjectAssociation)
        .where(
            PortfolioProjectAssociation.id.in_(association_ids),
            PortfolioProjectAssociation.portfolio_id == portfolio_id
        )
    )
    existing_associations = existing_result.scalars().all()

    if len(existing_associations) != len(association_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some associations not found or don't belong to this portfolio"
        )

    try:
        # Update positions
        for item in association_positions:
            await db.execute(
                update(PortfolioProjectAssociation)
                .where(PortfolioProjectAssociation.id == item["association_id"])
                .values(position=item["position"])
            )

        await db.commit()

        # Return updated associations
        updated_result = await db.execute(
            select(PortfolioProjectAssociation)
            .options(selectinload(PortfolioProjectAssociation.project))
            .where(PortfolioProjectAssociation.portfolio_id == portfolio_id)
            .order_by(PortfolioProjectAssociation.position)
        )

        associations = updated_result.scalars().all()
        return [PortfolioProjectAssociationSchema.model_validate(assoc) for assoc in associations]

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder associations: {str(e)}"
        )


async def bulk_add_projects(
    portfolio_id: UUID,
    project_data: List[PortfolioProjectAssociationCreate],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PortfolioProjectAssociationSchema]:
    """
    Adds multiple projects to a portfolio in bulk.
    """
    # Validate that all project data is for the same portfolio
    if not all(data.portfolio_id == portfolio_id for data in project_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All projects must be for the specified portfolio"
        )

    project_ids = [data.project_id for data in project_data]
    # Verify portfolio ownership
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    if str(portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add projects to another user's portfolio"
        )

    # Get starting position
    max_pos_result = await db.execute(
        select(func.max(PortfolioProjectAssociation.position))
        .where(PortfolioProjectAssociation.portfolio_id == portfolio_id)
    )
    current_max_position = max_pos_result.scalar() or 0

    # Verify all projects exist and are accessible
    projects_result = await db.execute(
        select(PortfolioProject)
        .options(selectinload(PortfolioProject.user_associations))
        .where(PortfolioProject.id.in_(project_ids))
    )
    projects = projects_result.scalars().all()

    if len(projects) != len(project_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some projects not found"
        )

    # Check permissions for each project
    for project in projects:
        if not project.is_public:
            if not project.user_associations or not any(
                str(ua.user_id) == str(user.id)
                for ua in project.user_associations
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No permission to add private project: {project.id}"
                )

    # Check for existing associations
    existing_result = await db.execute(
        select(PortfolioProjectAssociation.project_id)
        .where(
            PortfolioProjectAssociation.portfolio_id == portfolio_id,
            PortfolioProjectAssociation.project_id.in_(project_ids)
        )
    )
    existing_project_ids = {row[0] for row in existing_result.fetchall()}

    # Filter out already associated projects
    new_project_data = [data for data in project_data if data.project_id not in existing_project_ids]

    if not new_project_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All projects are already in the portfolio"
        )

    try:
        # Create associations
        new_associations = []
        for i, data in enumerate(new_project_data):
            position = data.position if data.position and data.position > 0 else current_max_position + i + 1
            association = PortfolioProjectAssociation(
                project_id=data.project_id,
                portfolio_id=portfolio_id,
                position=position,
                notes=data.notes
            )
            new_associations.append(association)
            db.add(association)

        await db.commit()

        # Refresh all associations
        for association in new_associations:
            await db.refresh(association)

        return [PortfolioProjectAssociationSchema.model_validate(assoc) for assoc in new_associations]

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add projects: {str(e)}"
        )


async def get_association_stats(
    portfolio_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Gets statistics about a portfolio's associations.
    """
    # Verify portfolio ownership
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    if str(portfolio.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's portfolio"
        )

    # Get association count
    count_result = await db.execute(
        select(func.count(PortfolioProjectAssociation.id))
        .where(PortfolioProjectAssociation.portfolio_id == portfolio_id)
    )
    total_associations = count_result.scalar()

    # Get associations with notes count
    notes_result = await db.execute(
        select(func.count(PortfolioProjectAssociation.id))
        .where(
            PortfolioProjectAssociation.portfolio_id == portfolio_id,
            PortfolioProjectAssociation.notes.isnot(None),
            PortfolioProjectAssociation.notes != ""
        )
    )
    associations_with_notes = notes_result.scalar()

    # Get last added association date
    last_added_result = await db.execute(
        select(func.max(PortfolioProjectAssociation.created_at))
        .where(PortfolioProjectAssociation.portfolio_id == portfolio_id)
    )
    last_added = last_added_result.scalar()

    return {
        "total_projects": total_associations,
        "projects_with_notes": associations_with_notes,
        "last_project_added": last_added,
        "portfolio_id": str(portfolio_id)
    }