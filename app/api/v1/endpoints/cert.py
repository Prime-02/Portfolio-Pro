from fastapi import APIRouter, status, Depends, HTTPException
from typing import Dict, Union, List
from app.models.schemas import (
    CertificationBase,
    CertificationUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.cert import (
    add_cert,
    get_all_certs as core_get_all_certs,
    get_cert_by_id as core_get_cert_by_id,
    update_cert as core_update_cert,
    delete_cert as core_delete_cert,
)
from app.models.db_models import User
from app.core.security import get_current_user
from app.database import get_db
from datetime import datetime
router = APIRouter(prefix="/certification", tags=["certification"])

@router.post(
    "/",
    response_model=CertificationBase,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new certification"
)
async def create_certification(
    cert_data: Dict[str, Union[str, bool, datetime]],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new certification for the current user.
    
    Required fields:
    - certification_name: str
    - issuing_organization: str
    
    Optional fields:
    - issue_date: datetime
    - expiration_date: datetime
    """
    return await add_cert({"data": cert_data, "user": current_user, "db": db})

@router.get(
    "/",
    response_model=List[CertificationBase],
    status_code=status.HTTP_200_OK,
    summary="Get all certifications for current user"
)
async def get_all_certifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all certifications for the currently authenticated user.
    """
    return await core_get_all_certs(user=current_user, db=db)

@router.get(
    "/{cert_id}",
    response_model=CertificationBase,
    status_code=status.HTTP_200_OK,
    summary="Get a specific certification by ID"
)
async def get_certification(
    cert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a specific certification by its ID.
    
    Parameters:
    - cert_id: UUID of the certification to retrieve
    """
    return await core_get_cert_by_id(cert_id=cert_id, user=current_user, db=db)

@router.put(
    "/{cert_id}",
    response_model=CertificationUpdate,
    status_code=status.HTTP_200_OK,
    summary="Update a certification"
)
async def update_certification(
    cert_id: UUID,
    cert_data: CertificationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a certification.
    
    Parameters:
    - cert_id: UUID of the certification to update
    
    Can update any of these fields:
    - certification_name
    - issuing_organization
    - issue_date
    - expiration_date
    """
    return await core_update_cert(
        cert_id=cert_id,
        cert_data=cert_data,
        user=current_user,
        db=db
    )

@router.delete(
    "/{cert_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a certification"
)
async def delete_certification(
    cert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a specific certification.
    
    Parameters:
    - cert_id: UUID of the certification to delete
    """
    return await core_delete_cert(cert_id=cert_id, user=current_user, db=db)