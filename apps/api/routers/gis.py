from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Parcel
from rules.gis_client import get_gis_client

router = APIRouter(prefix="/api/v1/gis", tags=["gis"])


class GisCheckResponse(BaseModel):
    parcel_id: Optional[str]
    gush: Optional[int]
    helka: Optional[int]
    zone: str
    zone_plan_id: str
    max_floors: int
    permitted_uses: list[str]
    max_coverage_pct: float
    is_protected_zone: bool
    is_agricultural_freeze: bool
    source: str


@router.get(
    "/check",
    response_model=GisCheckResponse,
    summary="Instant GIS lookup by parcel ID or block/plot numbers",
)
def check_land(
    parcel_id: Optional[str] = Query(None, description="Known parcel ID (looks up גוש/חלקה from DB)"),
    gush:      Optional[int] = Query(None, description="גוש (block) number"),
    helka:     Optional[int] = Query(None, description="חלקה (plot) number"),
    zone:      Optional[str] = Query(None, description="Zone override when using gush/helka directly"),
    db: Session = Depends(get_db),
):
    if parcel_id:
        parcel = db.get(Parcel, parcel_id)
        if parcel is None:
            raise HTTPException(status_code=404, detail=f"Parcel '{parcel_id}' not found")
        pid   = parcel.id
        gush  = parcel.gush
        helka = parcel.helka
        zone  = parcel.zone
    elif gush is not None and helka is not None:
        pid  = None
        zone = zone or "חקלאי"
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either parcel_id or both gush and helka",
        )

    client = get_gis_client()
    data   = client.fetch(parcel_id=pid or f"{gush}/{helka}", gush=gush, helka=helka, zone=zone)

    return GisCheckResponse(
        parcel_id=pid,
        gush=data.gush,
        helka=data.helka,
        zone=data.zone,
        zone_plan_id=data.zone_plan_id,
        max_floors=data.max_floors,
        permitted_uses=data.permitted_uses,
        max_coverage_pct=data.max_coverage_pct,
        is_protected_zone=data.is_protected_zone,
        is_agricultural_freeze=data.is_agricultural_freeze,
        source=data.raw.get("source", "unknown"),
    )
