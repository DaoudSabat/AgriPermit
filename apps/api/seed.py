"""
Seed the parcels table with initial agricultural land data and create a default admin user.
Run once after the DB is up:
    docker-compose exec api python seed.py   (Docker)
    python seed.py                           (local)

gush/helka values are illustrative Jerusalem cadastral IDs.
Replace with verified values from the Israel Land Registry when going live.
"""
import sys
from pathlib import Path

_packages = Path(__file__).parent.parent.parent / "packages"
if _packages.exists() and str(_packages) not in sys.path:
    sys.path.insert(0, str(_packages))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from database import SessionLocal, Base, engine
from models import Organization, Parcel, User, UserRole
from auth import hash_password

# Ensure all tables exist (idempotent)
Base.metadata.create_all(bind=engine)

PARCELS = [
    Parcel(id="jer_1001", gush=30001, helka=12,  address="רחוב הרצל 1, ירושלים",           zone="חקלאי",         area_sqm=1000.0),
    Parcel(id="jer_1002", gush=30001, helka=45,  address="שכונת עיר גנים, ירושלים",        zone="חקלאי פרטי",    area_sqm=1500.0),
    Parcel(id="jer_1003", gush=30018, helka=7,   address="אזור התעשייה, מלחה, ירושלים",    zone="חקלאי מוגן",    area_sqm=2200.0),
    Parcel(id="tlv_2001", gush=6645,  helka=101, address="שדרות רוטשילד 50, תל אביב",      zone="חקלאי עירוני",  area_sqm=800.0),
    Parcel(id="tlv_2002", gush=6646,  helka=23,  address="רחוב דיזנגוף 100, תל אביב",      zone="חקלאי פרטי",    area_sqm=950.0),
    Parcel(id="hfa_3001", gush=10950, helka=56,  address="שדרות הנשיא 12, חיפה",           zone="חקלאי",         area_sqm=1750.0),
    Parcel(id="hfa_3002", gush=10952, helka=3,   address="רחוב הגפן 8, קריית חיים",        zone="חקלאי מוגן",    area_sqm=3100.0),
    Parcel(id="be7_4001", gush=40011, helka=88,  address="רחוב הפלמ\"ח 3, באר שבע",        zone="חקלאי מדברי",   area_sqm=5000.0),
    Parcel(id="be7_4002", gush=40015, helka=14,  address="אזור חווה לימודית, רהט",         zone="חקלאי",         area_sqm=4200.0),
    Parcel(id="naz_5001", gush=17280, helka=31,  address="רחוב פאולוס השישי 7, נצרת",      zone="חקלאי פרטי",    area_sqm=1300.0),
]


DEFAULT_ADMIN = dict(
    username="admin",
    email="admin@agripermit.local",
    full_name="System Admin",
    password="admin123",
    role=UserRole.admin,
)


def seed():
    db = SessionLocal()
    try:
        # Default organization
        org = db.query(Organization).filter(Organization.slug == "demo").first()
        if not org:
            org = Organization(name="AgriPermit Demo", slug="demo")
            db.add(org)
            db.commit()
            db.refresh(org)
            print("Created default organization: AgriPermit Demo (slug: demo)")
        else:
            print("Default organization already exists.")

        # Parcels
        existing_ids = {row.id for row in db.query(Parcel.id).all()}
        new_parcels = [p for p in PARCELS if p.id not in existing_ids]
        for p in new_parcels:
            p.org_id = org.id
        if new_parcels:
            db.add_all(new_parcels)
            db.commit()
            print(f"Seeded {len(new_parcels)} parcel(s).")
        else:
            print("Parcels already seeded.")

        # Default admin user
        if not db.query(User).filter(User.username == DEFAULT_ADMIN["username"]).first():
            admin = User(
                username=DEFAULT_ADMIN["username"],
                email=DEFAULT_ADMIN["email"],
                full_name=DEFAULT_ADMIN["full_name"],
                hashed_password=hash_password(DEFAULT_ADMIN["password"]),
                role=DEFAULT_ADMIN["role"],
                org_id=org.id,
            )
            db.add(admin)
            db.commit()
            print(f"Created default admin user: {DEFAULT_ADMIN['username']} / {DEFAULT_ADMIN['password']}")
        else:
            admin = db.query(User).filter(User.username == DEFAULT_ADMIN["username"]).first()
            if admin and not admin.org_id:
                admin.org_id = org.id
                db.commit()
            print("Admin user already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
