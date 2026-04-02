from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Permit, PermitStatus, User

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


class StatsResponse(BaseModel):
    total: int
    pending: int
    approved: int
    rejected: int
    gis_blocked: int
    gis_flagged: int


@router.get("", response_model=StatsResponse, summary="Dashboard permit counts")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    def count(where=None):
        q = select(func.count()).select_from(Permit)
        if current_user.org_id:
            q = q.where(Permit.org_id == current_user.org_id)
        if where is not None:
            q = q.where(where)
        return db.scalar(q) or 0

    return StatsResponse(
        total=count(),
        pending=count(Permit.status == PermitStatus.pending),
        approved=count(Permit.status == PermitStatus.approved),
        rejected=count(Permit.status == PermitStatus.rejected),
        gis_blocked=count(Permit.gis_blocked == True),
        gis_flagged=count(Permit.gis_flagged == True),
    )
