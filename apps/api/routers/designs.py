"""
Design file upload and GIS compliance check.

POST /api/v1/designs/upload
    Accepts a multipart file upload (PDF, DXF, DWG).
    1. Saves the file locally (or to MinIO when available).
    2. Parses it with design_parser to extract floors/coverage/area.
    3. Runs the GIS rules engine against the parcel's zone data.
    4. Returns a full DesignSubmissionResponse including compliance report.

GET /api/v1/designs/{design_id}
    Returns a previously uploaded design submission.

GET /api/v1/designs/{design_id}/report
    Returns the structured compliance report (printable JSON).

GET /api/v1/designs
    Lists all design submissions, optionally filtered by permit_id or parcel_id.
"""

import os
import pathlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import DesignSubmission, Parcel, Permit
from rules import run_gis_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/designs", tags=["designs"])

# Local upload directory (dev fallback — replace with MinIO in production)
_UPLOAD_DIR = pathlib.Path(__file__).parent.parent / "uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)

_MAX_FILE_MB = int(os.getenv("DESIGN_MAX_MB", "20"))
_ALLOWED_EXT = {".pdf", ".dxf", ".dwg"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class ViolationOut(BaseModel):
    rule:     str
    severity: str   # "block" | "warn"
    message:  str


class ComplianceReport(BaseModel):
    compliant:      bool
    blocked:        bool
    violations:     list[ViolationOut]
    gis_zone:       str
    gis_plan_id:    str
    gis_max_floors: int
    gis_max_cov:    float
    gis_protected:  bool
    gis_ag_freeze:  bool
    gis_source:     str
    gis_data_version: str
    checked_at:     str


class DesignSubmissionResponse(BaseModel):
    id:               str
    permit_id:        Optional[str]
    parcel_id:        Optional[str]
    filename:         str
    file_size:        int

    parsed_floors:       Optional[int]
    parsed_coverage_pct: Optional[float]
    parsed_area_sqm:     Optional[float]
    engineer_name:       Optional[str]
    engineer_license:    Optional[str]
    parse_warnings:      list[str]

    compliance:   Optional[ComplianceReport]
    uploaded_at:  str

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_compliance(submission: DesignSubmission) -> ComplianceReport | None:
    if submission.gis_snapshot is None:
        return None
    snap = submission.gis_snapshot
    violations = [ViolationOut(**v) for v in (submission.gis_violations or [])]
    blocked = any(v.severity == "block" for v in violations)
    return ComplianceReport(
        compliant=submission.gis_compliant or False,
        blocked=blocked,
        violations=violations,
        gis_zone=snap.get("zone", ""),
        gis_plan_id=snap.get("zone_plan_id", ""),
        gis_max_floors=snap.get("max_floors", 0),
        gis_max_cov=snap.get("max_coverage_pct", 0.0),
        gis_protected=snap.get("is_protected_zone", False),
        gis_ag_freeze=snap.get("is_agricultural_freeze", False),
        gis_source=snap.get("raw", {}).get("source", snap.get("source", "unknown")),
        gis_data_version=submission.gis_data_version or "",
        checked_at=submission.uploaded_at.isoformat() if submission.uploaded_at else "",
    )


def _submission_to_response(s: DesignSubmission) -> DesignSubmissionResponse:
    return DesignSubmissionResponse(
        id=s.id,
        permit_id=s.permit_id,
        parcel_id=s.parcel_id,
        filename=s.filename,
        file_size=s.file_size,
        parsed_floors=s.parsed_floors,
        parsed_coverage_pct=s.parsed_coverage_pct,
        parsed_area_sqm=s.parsed_area_sqm,
        engineer_name=s.engineer_name,
        engineer_license=s.engineer_license,
        parse_warnings=s.parse_warnings or [],
        compliance=_build_compliance(s),
        uploaded_at=s.uploaded_at.isoformat(),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=DesignSubmissionResponse,
    summary="Upload an engineering design file and validate against GIS zoning",
)
async def upload_design(
    file:      UploadFile = File(..., description="PDF, DXF, or DWG design file"),
    parcel_id: Optional[str] = Form(None, description="Parcel ID to validate against"),
    permit_id: Optional[str] = Form(None, description="Existing permit to attach this design to"),
    # Manual overrides — used when auto-extraction fails or needs correction
    floors_override:    Optional[int]   = Form(None, description="Override extracted floor count"),
    coverage_override:  Optional[float] = Form(None, description="Override extracted coverage %"),
    db: Session = Depends(get_db),
):
    # ── 1. Validate file ──────────────────────────────────────────────────────
    suffix = pathlib.Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Accepted: {', '.join(_ALLOWED_EXT)}")

    data = await file.read()
    if len(data) > _MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {_MAX_FILE_MB} MB limit")

    # ── 2. Resolve parcel ─────────────────────────────────────────────────────
    parcel: Parcel | None = None
    if parcel_id:
        parcel = db.get(Parcel, parcel_id)
        if parcel is None:
            raise HTTPException(404, f"Parcel '{parcel_id}' not found")

    if permit_id:
        permit = db.get(Permit, permit_id)
        if permit is None:
            raise HTTPException(404, f"Permit '{permit_id}' not found")
        if parcel is None and permit.parcel:
            parcel = permit.parcel
            parcel_id = parcel.id

    # ── 3. Save file ──────────────────────────────────────────────────────────
    import uuid
    safe_name  = f"{uuid.uuid4()}{suffix}"
    dest_path  = _UPLOAD_DIR / safe_name
    dest_path.write_bytes(data)
    logger.info("Saved design file: %s (%d bytes)", dest_path, len(data))

    # ── 4. Parse design parameters ────────────────────────────────────────────
    from rules.design_parser import parse_design_file
    params = parse_design_file(data, file.filename or safe_name)

    floors      = floors_override   if floors_override   is not None else params.floors
    coverage    = coverage_override if coverage_override is not None else params.coverage_pct

    # ── 5. GIS compliance check ───────────────────────────────────────────────
    gis_snapshot  = None
    gis_violations = []
    gis_compliant  = None
    gis_version    = None

    if parcel:
        try:
            result = run_gis_check(
                parcel_id=parcel.id,
                gush=parcel.gush,
                helka=parcel.helka,
                zone=parcel.zone,
                permit_type="agricultural",   # use generic type for design checks
                requested_floors=floors,
                requested_coverage_pct=coverage,
            )
            gis_snapshot   = result.snapshot
            gis_violations = [v.to_dict() for v in result.violations]
            gis_compliant  = not result.blocked
            gis_version    = result.snapshot.get("data_version") or result.snapshot.get("raw", {}).get("source", "")
        except Exception as exc:
            logger.warning("GIS check failed for design upload: %s", exc)
            params.warnings.append(f"GIS validation unavailable: {exc}")
    else:
        params.warnings.append("No parcel selected — GIS validation skipped. Attach a parcel to get compliance results.")

    # ── 6. Persist ────────────────────────────────────────────────────────────
    submission = DesignSubmission(
        permit_id=permit_id,
        parcel_id=parcel_id,
        filename=file.filename or safe_name,
        file_path=str(dest_path),
        file_size=len(data),
        parsed_floors=floors,
        parsed_coverage_pct=coverage,
        parsed_area_sqm=params.area_sqm,
        engineer_name=params.engineer_name or None,
        engineer_license=params.engineer_license or None,
        parse_warnings=params.warnings or None,
        gis_compliant=gis_compliant,
        gis_violations=gis_violations or None,
        gis_snapshot=gis_snapshot,
        gis_data_version=gis_version,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return _submission_to_response(submission)


@router.get(
    "",
    response_model=list[DesignSubmissionResponse],
    summary="List design submissions",
)
def list_designs(
    permit_id: Optional[str] = Query(None),
    parcel_id: Optional[str] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    q = select(DesignSubmission)
    if permit_id:
        q = q.where(DesignSubmission.permit_id == permit_id)
    if parcel_id:
        q = q.where(DesignSubmission.parcel_id == parcel_id)
    q = q.order_by(DesignSubmission.uploaded_at.desc()).offset(skip).limit(limit)
    return [_submission_to_response(s) for s in db.scalars(q).all()]


@router.get(
    "/{design_id}",
    response_model=DesignSubmissionResponse,
    summary="Get a design submission",
)
def get_design(design_id: str, db: Session = Depends(get_db)):
    s = db.get(DesignSubmission, design_id)
    if s is None:
        raise HTTPException(404, f"Design '{design_id}' not found")
    return _submission_to_response(s)


@router.get(
    "/{design_id}/report",
    response_model=ComplianceReport,
    summary="Get the GIS compliance report for a design submission",
)
def get_compliance_report(design_id: str, db: Session = Depends(get_db)):
    s = db.get(DesignSubmission, design_id)
    if s is None:
        raise HTTPException(404, f"Design '{design_id}' not found")
    report = _build_compliance(s)
    if report is None:
        raise HTTPException(404, "No GIS compliance data for this design — resubmit with a parcel selected")
    return report
