from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import re

from auth import create_access_token, hash_password
from database import get_db
from deps import get_current_user
from models import Organization, User, UserRole
from schemas import OrgRegister, OrgResponse, OrgWithMembersResponse, TokenResponse, UserResponse

router = APIRouter(prefix="/api/v1/orgs", tags=["organizations"])


def _slugify(s: str) -> str:
    return re.sub(r'[^a-z0-9-]', '-', s.lower().strip()).strip('-')


@router.post("/register", response_model=TokenResponse, status_code=201,
             summary="Create a new organization + admin user (SaaS onboarding)")
def register_org(payload: OrgRegister, db: Session = Depends(get_db)):
    slug = _slugify(payload.org_slug or payload.org_name)
    if db.query(Organization).filter(Organization.slug == slug).first():
        raise HTTPException(409, detail="Organization slug already taken")
    if db.query(User).filter(User.username == payload.admin_username).first():
        raise HTTPException(409, detail="Username already taken")
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(409, detail="Email already registered")

    org = Organization(name=payload.org_name, slug=slug)
    db.add(org)
    db.flush()

    admin = User(
        username=payload.admin_username,
        email=payload.admin_email,
        full_name=payload.admin_full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.admin,
        org_id=org.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = create_access_token(subject=admin.username, role=admin.role.value)
    return TokenResponse(
        access_token=token,
        username=admin.username,
        full_name=admin.full_name,
        role=admin.role.value,
    )


@router.get("/me", response_model=OrgResponse, summary="Get current user's organization")
def get_my_org(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.org_id:
        raise HTTPException(404, detail="User has no organization")
    org = db.get(Organization, user.org_id)
    if not org:
        raise HTTPException(404, detail="Organization not found")
    return org


@router.get("/me/members", response_model=list[UserResponse], summary="List org members")
def get_org_members(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.org_id:
        return []
    return db.query(User).filter(User.org_id == user.org_id).all()
