from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Parcel, Permit, PermitStatus, User
from rules import run_gis_check
from schemas import PermitApprove, PermitCreate, PermitListResponse, PermitResponse

router = APIRouter(prefix="/api/v1/permits", tags=["permits"])


def _generate_permit_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.scalar(select(func.count()).select_from(Permit)) or 0
    return f"AGR-{year}-{count + 1:05d}"


@router.post(
    "",
    response_model=PermitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new permit application",
)
def create_permit(
    payload: PermitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parcel = db.get(Parcel, payload.parcel_id)
    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parcel '{payload.parcel_id}' not found",
        )

    gis = run_gis_check(
        parcel_id=parcel.id,
        gush=parcel.gush,
        helka=parcel.helka,
        zone=parcel.zone,
        permit_type=payload.permit_type.value,
        requested_floors=payload.requested_floors,
        requested_coverage_pct=payload.requested_coverage_pct,
    )

    permit = Permit(
        permit_number=_generate_permit_number(db),
        parcel_id=payload.parcel_id,
        applicant_name=payload.applicant_name,
        applicant_email=payload.applicant_email,
        permit_type=payload.permit_type,
        description=payload.description,
        requested_floors=payload.requested_floors,
        requested_coverage_pct=payload.requested_coverage_pct,
        gis_flagged=gis.flagged,
        gis_blocked=gis.blocked,
        gis_snapshot=gis.snapshot,
        gis_violations=[v.to_dict() for v in gis.violations],
        org_id=current_user.org_id,
    )
    db.add(permit)
    db.commit()
    db.refresh(permit)
    return permit


@router.get(
    "",
    response_model=PermitListResponse,
    summary="List permits with optional filters",
)
def list_permits(
    parcel_id: Optional[str] = Query(None, description="Filter by parcel ID"),
    status: Optional[PermitStatus] = Query(None, description="Filter by status"),
    gis_flagged: Optional[bool] = Query(None, description="Filter to flagged/clean permits"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Permit)
    if current_user.org_id:
        query = query.where(Permit.org_id == current_user.org_id)
    if parcel_id:
        query = query.where(Permit.parcel_id == parcel_id)
    if status:
        query = query.where(Permit.status == status)
    if gis_flagged is not None:
        query = query.where(Permit.gis_flagged == gis_flagged)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    permits = db.scalars(query.offset(skip).limit(limit)).all()

    return PermitListResponse(total=total, items=list(permits))


@router.get(
    "/{permit_id}",
    response_model=PermitResponse,
    summary="Get a single permit by ID",
)
def get_permit(permit_id: str, db: Session = Depends(get_db)):
    permit = db.get(Permit, permit_id)
    if permit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permit '{permit_id}' not found",
        )
    return permit


@router.post(
    "/{permit_id}/approve",
    response_model=PermitResponse,
    summary="Approve or reject a permit",
)
def approve_permit(
    permit_id: str,
    payload: PermitApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permit = db.get(Permit, permit_id)
    if permit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permit '{permit_id}' not found",
        )
    if permit.status != PermitStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permit is already '{permit.status}' and cannot be actioned again",
        )

    now = datetime.now(timezone.utc)
    approved_by = payload.approved_by or current_user.full_name
    if payload.action == "approve":
        permit.status = PermitStatus.approved
        permit.approved_at = now
        permit.approved_by = approved_by
    else:
        permit.status = PermitStatus.rejected
        permit.rejection_reason = payload.rejection_reason
        permit.approved_by = approved_by

    permit.updated_at = now
    db.commit()
    db.refresh(permit)
    return permit
