import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env from apps/api/ before anything else reads os.getenv()
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# When running locally (start-local.bat), packages/ isn't on sys.path.
# This insert makes `from rules import ...` work without setting PYTHONPATH manually.
_packages = Path(__file__).parent.parent.parent / "packages"
if _packages.exists() and str(_packages) not in sys.path:
    sys.path.insert(0, str(_packages))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from database import Base, engine
from routers import permits, parcels, gis, users, stats, designs, orgs


def _refresh_gis_cache():
    """Background job: re-fetch GIS data for any cached parcel older than TTL."""
    try:
        from rules.gis_client import refresh_stale_cache
        refresh_stale_cache()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("GIS cache refresh job failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"[warning] Could not create DB tables: {exc}")

    # Start background GIS cache refresh (every 6 hours)
    scheduler = BackgroundScheduler()
    scheduler.add_job(_refresh_gis_cache, "interval", hours=6, id="gis_cache_refresh")
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(
    title="AgriPermit API",
    description="Agricultural Land Permit System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(permits.router)
app.include_router(parcels.router)
app.include_router(gis.router)
app.include_router(users.router)
app.include_router(stats.router)
app.include_router(designs.router)
app.include_router(orgs.router)


@app.get("/", tags=["meta"])
def root():
    return {"message": "AgriPermit API", "status": "running", "version": "1.0.0"}


@app.get("/health", tags=["meta"])
def health():
    return {"status": "healthy"}
