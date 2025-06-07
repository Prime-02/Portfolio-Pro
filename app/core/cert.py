from app.models.schemas import (
    CertificationUpdate,
    CertificationBase,
)
from app.models.db_models import Certification, User
from typing import Dict, Union, List, Optional, cast
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.database import get_db
from sqlalchemy.future import select
import uuid
from datetime import datetime, date
from sqlalchemy import Date, cast as sql_cast


async def get_common_params(
    data: Dict[str, Union[str, bool, datetime, date]],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Union[Dict[str, Union[str, bool, datetime, date]], User, AsyncSession]]:
    return {"data": data, "user": user, "db": db}


async def add_cert(
    commons: Dict[
        str, Union[Dict[str, Union[str, bool, datetime, date]], User, AsyncSession]
    ] = Depends(get_common_params),
) -> CertificationBase:
    cert_data = cast(Dict[str, Union[str, bool, datetime, date]], commons["data"])
    user = cast(User, commons["user"])
    db = cast(AsyncSession, commons["db"])

    if not cert_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No certification provided",
        )

    if "certification_name" not in cert_data or "issuing_organization" not in cert_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a certification and its issuing organization",
        )

    # Convert string date to date object if needed
    issue_date = cert_data.get("issue_date")
    if issue_date and isinstance(issue_date, str):
        try:
            issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid issue_date format. Use YYYY-MM-DD",
            )

    # Build the query with proper date handling
    query = select(Certification).where(
        Certification.user_id == user.id,
        Certification.certification_name == cast(str, cert_data["certification_name"]),
        Certification.issuing_organization == cast(str, cert_data["issuing_organization"]),
    )

    # Only add date comparison if date is provided
    if issue_date:
        query = query.where(
            sql_cast(Certification.issue_date, Date) == issue_date
        )

    existing_cert = await db.execute(query)
    
    if existing_cert.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{cert_data['certification_name']} with similar issuing organization and issue date already exists for this user",
        )

    cert_id = uuid.uuid4()
    created_at = datetime.now()

    # Handle expiration date conversion if it's a string
    expiration_date = cert_data.get("expiration_date")
    if expiration_date and isinstance(expiration_date, str):
        try:
            expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid expiration_date format. Use YYYY-MM-DD",
            )

    new_cert = Certification(
        id=cert_id,
        user_id=uuid.UUID(str(user.id)),
        certification_name=cast(str, cert_data["certification_name"]),
        issuing_organization=cast(str, cert_data["issuing_organization"]),
        created_at=created_at,
        issue_date=cast(Union[datetime, date], issue_date),
        expiration_date=cast(Union[datetime, date], expiration_date),
    )

    db.add(new_cert)
    await db.commit()
    await db.refresh(new_cert)

    return CertificationBase(
        id=cert_id,
        user_id=uuid.UUID(str(user.id)),
        certification_name=cast(str, cert_data["certification_name"]),
        issuing_organization=cast(str, cert_data["issuing_organization"]),
        created_at=created_at,
        issue_date=cast(Union[datetime, date], issue_date),
        expiration_date=cast(Union[datetime, date], expiration_date),
    )


async def get_all_certs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CertificationBase]:
    result = await db.execute(
        select(Certification).where(Certification.user_id == user.id)
    )
    certs = result.scalars().all()

    return [
        CertificationBase(
            id=uuid.UUID(str(cert.id)),
            user_id=uuid.UUID(str(user.id)),
            certification_name=cast(str, cert.certification_name),
            issuing_organization=cast(str, cert.issuing_organization),
            created_at=cast(datetime, cert.created_at),
            issue_date=cast(Union[datetime, date], cert.issue_date),
            expiration_date=cast(Union[datetime, date], cert.expiration_date),
        )
        for cert in certs
    ]


async def get_cert_by_id(
    cert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CertificationBase:
    result = await db.execute(
        select(Certification)
        .where(Certification.id == cert_id)
        .where(Certification.user_id == user.id)
    )
    cert = cast(Optional[Certification], result.scalar_one_or_none())

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found"
        )

    return CertificationBase(
        id=cert_id,
        user_id=uuid.UUID(str(user.id)),
        certification_name=cast(str, cert.certification_name),
        issuing_organization=cast(str, cert.issuing_organization),
        created_at=cast(datetime, cert.created_at),
        issue_date=cast(Union[datetime, date], cert.issue_date),
        expiration_date=cast(Union[datetime, date], cert.expiration_date),
    )


async def update_cert(
    cert_id: uuid.UUID,
    cert_data: CertificationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CertificationUpdate:
    result = await db.execute(
        select(Certification)
        .where(Certification.id == cert_id)
        .where(Certification.user_id == user.id)
    )
    cert = cast(Optional[Certification], result.scalar_one_or_none())

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found"
        )

    # Handle date conversions if they are strings
    issue_date = cert_data.issue_date
    if issue_date and isinstance(issue_date, str):
        try:
            issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid issue_date format. Use YYYY-MM-DD",
            )

    expiration_date = cert_data.expiration_date
    if expiration_date and isinstance(expiration_date, str):
        try:
            expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid expiration_date format. Use YYYY-MM-DD",
            )

    if (
        cert_data.certification_name
        and cert_data.certification_name != cert.certification_name
    ) or (
        cert_data.issuing_organization
        and cert_data.issuing_organization != cert.issuing_organization
    ):
        existing_cert = await db.execute(
            select(Certification)
            .where(Certification.user_id == user.id)
            .where(
                Certification.certification_name == cert_data.certification_name,
                Certification.issuing_organization == cert_data.issuing_organization,
            )
        )
        if existing_cert.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certification with this name and organization already exists for this user",
            )

    if cert_data.certification_name is not None:
        cert.certification_name = cast(str, cert_data.certification_name)

    if cert_data.issuing_organization is not None:
        cert.issuing_organization = cast(str, cert_data.issuing_organization)

    if issue_date is not None:
        cert.issue_date = cast(Union[datetime, date], issue_date)

    if expiration_date is not None:
        cert.expiration_date = cast(Union[datetime, date], expiration_date)

    await db.commit()
    await db.refresh(cert)

    return CertificationUpdate(
        certification_name=cast(str, cert.certification_name),
        issuing_organization=cast(str, cert.issuing_organization),
        issue_date=cast(Union[datetime, date], cert.issue_date),
        expiration_date=cast(Union[datetime, date], cert.expiration_date),
    )


async def delete_cert(
    cert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    result = await db.execute(
        select(Certification)
        .where(Certification.id == cert_id)
        .where(Certification.user_id == user.id)
    )
    cert = cast(Optional[Certification], result.scalar_one_or_none())

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found"
        )
    await db.delete(cert)
    await db.commit()

    return {"message": "Certification deleted successfully"}