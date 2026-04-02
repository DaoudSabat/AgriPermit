from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import Parcel, User
from schemas import ParcelResponse

router = APIRouter(prefix="/api/v1/parcels", tags=["parcels"])


@router.get("", response_model=list[ParcelResponse], summary="List all parcels")
def list_parcels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Parcel).order_by(Parcel.id)
    if current_user.org_id:
        query = query.where(Parcel.org_id == current_user.org_id)
    return db.scalars(query).all()
