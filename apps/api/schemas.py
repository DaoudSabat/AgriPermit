from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from models import OrgPlan, PermitStatus, PermitType, UserRole


# ---------- Auth ----------

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.viewer

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("password must be at least 6 characters")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("username must not be blank")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Parcel ----------

class ParcelResponse(BaseModel):
    id: str
    address: str
    zone: str
    area_sqm: float
    gush: Optional[int] = None
    helka: Optional[int] = None

    model_config = {"from_attributes": True}


# ---------- Permit ----------

class PermitCreate(BaseModel):
    parcel_id: str
    applicant_name: str
    applicant_email: EmailStr
    permit_type: PermitType = PermitType.agricultural
    description: Optional[str] = None
    # Construction-specific — used by the GIS rules engine
    requested_floors: Optional[int] = None
    requested_coverage_pct: Optional[float] = None

    @field_validator("applicant_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("applicant_name must not be blank")
        return v.strip()

    @field_validator("requested_floors")
    @classmethod
    def floors_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("requested_floors must be at least 1")
        return v

    @field_validator("requested_coverage_pct")
    @classmethod
    def coverage_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 < v <= 100):
            raise ValueError("requested_coverage_pct must be between 0 and 100")
        return v


class PermitApprove(BaseModel):
    approved_by: str
    rejection_reason: Optional[str] = None
    action: str  # "approve" | "reject"

    @field_validator("action")
    @classmethod
    def valid_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v

    @field_validator("rejection_reason")
    @classmethod
    def reason_required_on_reject(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("action") == "reject" and not v:
            raise ValueError("rejection_reason is required when action is 'reject'")
        return v


class GisViolation(BaseModel):
    rule: str
    severity: str   # "block" | "warn"
    message: str


class PermitResponse(BaseModel):
    id: str
    permit_number: str
    parcel_id: str
    applicant_name: str
    applicant_email: str
    permit_type: PermitType
    status: PermitStatus
    description: Optional[str]
    requested_floors: Optional[int]
    requested_coverage_pct: Optional[float]
    # GIS check results
    gis_flagged: bool = False
    gis_blocked: bool = False
    gis_violations: Optional[list[GisViolation]] = None
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    rejection_reason: Optional[str]

    model_config = {"from_attributes": True}


class PermitListResponse(BaseModel):
    total: int
    items: list[PermitResponse]


# ---------- Organization ----------

class OrgRegister(BaseModel):
    org_name: str
    org_slug: str
    admin_username: str
    admin_email: EmailStr
    admin_full_name: str
    password: str


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: OrgPlan
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgWithMembersResponse(OrgResponse):
    member_count: int
