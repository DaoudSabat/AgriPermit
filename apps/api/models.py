import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Enum as SAEnum, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class OrgPlan(str, enum.Enum):
    free       = "free"
    pro        = "pro"
    enterprise = "enterprise"


class Organization(Base):
    __tablename__ = "organizations"

    id:         Mapped[str]     = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:       Mapped[str]     = mapped_column(String(150), nullable=False)
    slug:       Mapped[str]     = mapped_column(String(80), unique=True, nullable=False)
    plan:       Mapped[OrgPlan] = mapped_column(SAEnum(OrgPlan), nullable=False, default=OrgPlan.free)
    is_active:  Mapped[bool]    = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    users:   Mapped[list["User"]]   = relationship("User",   back_populates="org")
    parcels: Mapped[list["Parcel"]] = relationship("Parcel", back_populates="org")
    permits: Mapped[list["Permit"]] = relationship("Permit", back_populates="org")


class UserRole(str, enum.Enum):
    admin    = "admin"
    reviewer = "reviewer"
    viewer   = "viewer"


class User(Base):
    __tablename__ = "users"

    id:              Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username:        Mapped[str]      = mapped_column(String(80), unique=True, nullable=False)
    email:           Mapped[str]      = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str]      = mapped_column(String(255), nullable=False)
    full_name:       Mapped[str]      = mapped_column(String(150), nullable=False)
    role:            Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.viewer)
    is_active:       Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    created_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    org_id:          Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    org:             Mapped["Organization | None"] = relationship("Organization", back_populates="users")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PermitStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


class PermitType(str, enum.Enum):
    agricultural = "agricultural"
    construction = "construction"
    water        = "water"
    other        = "other"


class Parcel(Base):
    __tablename__ = "parcels"

    id:       Mapped[str]        = mapped_column(String(50), primary_key=True)
    address:  Mapped[str]        = mapped_column(String(255), nullable=False)
    zone:     Mapped[str]        = mapped_column(String(100), nullable=False)
    area_sqm: Mapped[float]      = mapped_column(Float,       nullable=False)
    # Israeli cadastral identifiers — required for real GIS lookups
    gush:     Mapped[int | None] = mapped_column(Integer, nullable=True)
    helka:    Mapped[int | None] = mapped_column(Integer, nullable=True)
    org_id:   Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    org:      Mapped["Organization | None"] = relationship("Organization", back_populates="parcels")

    permits: Mapped[list["Permit"]] = relationship("Permit", back_populates="parcel")


class Permit(Base):
    __tablename__ = "permits"

    id:            Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    permit_number: Mapped[str]      = mapped_column(String(20), unique=True, nullable=False)
    parcel_id:     Mapped[str]      = mapped_column(String(50), ForeignKey("parcels.id"), nullable=False)
    applicant_name:  Mapped[str]    = mapped_column(String(150), nullable=False)
    applicant_email: Mapped[str]    = mapped_column(String(254), nullable=False)
    permit_type:   Mapped[PermitType]   = mapped_column(SAEnum(PermitType),   nullable=False, default=PermitType.agricultural)
    status:        Mapped[PermitStatus] = mapped_column(SAEnum(PermitStatus), nullable=False, default=PermitStatus.pending)
    description:   Mapped[str | None]  = mapped_column(Text, nullable=True)

    # Construction-specific parameters used by the GIS rules engine
    requested_floors:       Mapped[int | None]   = mapped_column(Integer, nullable=True)
    requested_coverage_pct: Mapped[float | None] = mapped_column(Float,   nullable=True)

    # GIS check results — populated at submission time, immutable afterwards
    gis_flagged:    Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    gis_blocked:    Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    gis_snapshot:   Mapped[dict | None]  = mapped_column(JSON, nullable=True)   # raw GIS data
    gis_violations: Mapped[list | None]  = mapped_column(JSON, nullable=True)   # list[{rule, severity, message}]

    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None]    = mapped_column(String(150), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    org_id:      Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    org:         Mapped["Organization | None"] = relationship("Organization", back_populates="permits")

    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="permits")
    designs: Mapped[list["DesignSubmission"]] = relationship("DesignSubmission", back_populates="permit")


class DesignSubmission(Base):
    """An engineering design file uploaded against a permit application."""
    __tablename__ = "design_submissions"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    permit_id:   Mapped[str | None] = mapped_column(String(36), ForeignKey("permits.id"), nullable=True)
    parcel_id:   Mapped[str | None] = mapped_column(String(50), ForeignKey("parcels.id"), nullable=True)

    # File metadata
    filename:    Mapped[str] = mapped_column(String(255), nullable=False)
    file_path:   Mapped[str] = mapped_column(String(512), nullable=False)  # local or MinIO path
    file_size:   Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Parsed design parameters (auto-extracted from the file)
    parsed_floors:       Mapped[int | None]   = mapped_column(Integer, nullable=True)
    parsed_coverage_pct: Mapped[float | None] = mapped_column(Float,   nullable=True)
    parsed_area_sqm:     Mapped[float | None] = mapped_column(Float,   nullable=True)
    engineer_name:       Mapped[str | None]   = mapped_column(String(150), nullable=True)
    engineer_license:    Mapped[str | None]   = mapped_column(String(50),  nullable=True)
    parse_warnings:      Mapped[list | None]  = mapped_column(JSON, nullable=True)

    # GIS compliance result — computed at upload time
    gis_compliant:   Mapped[bool | None]   = mapped_column(Boolean, nullable=True)
    gis_violations:  Mapped[list | None]   = mapped_column(JSON, nullable=True)
    gis_snapshot:    Mapped[dict | None]   = mapped_column(JSON, nullable=True)
    gis_data_version: Mapped[str | None]  = mapped_column(String(100), nullable=True)  # e.g. "govmap-20260401"

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    permit: Mapped["Permit | None"] = relationship("Permit", back_populates="designs")
    parcel: Mapped["Parcel | None"] = relationship("Parcel")
