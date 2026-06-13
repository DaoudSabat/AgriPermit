# 🌾 AgriPermit

Full B2B SaaS for agricultural land permit management — parcel GIS lookup, AI-generated compliance reports, and multi-tenant organisation support.

## Overview

AgriPermit lets municipalities and planning consultants manage the full permit lifecycle: select a parcel on an interactive map, run automated GIS compliance checks against Israeli zoning rules (gush/helka identifiers), submit a structured permit application, and receive a Claude-generated compliance report with inline SVG floor plan visualisations. The platform supports Arabic, English, and Hebrew out of the box.

## Architecture

```
AgriPermit/
├── apps/
│   ├── api/                  # FastAPI backend
│   │   ├── routers/          # permits, parcels, gis, users, stats, designs, orgs
│   │   ├── main.py           # app factory, CORS, APScheduler GIS cache refresh
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── auth.py           # JWT authentication
│   │   └── database.py       # DB session factory
│   ├── web/                  # React + Vite frontend
│   │   └── src/
│   │       ├── components/   # PermitList, NewPermitForm, LandCheck, DesignUpload, StatsBar
│   │       ├── i18n/         # en / ar / he translation files
│   │       ├── api.js        # Axios client
│   │       └── AuthContext.jsx
│   └── worker/               # Celery async task worker
├── packages/
│   └── rules/                # GIS compliance rule engine (shared package)
│       ├── engine.py         # run_gis_check() — orchestrates all rules
│       ├── rules.py          # per-rule validators (floors, coverage, protected zones)
│       └── gis_client.py     # GIS API client with 6-hour background cache refresh
├── AgriPermitMobile/         # Expo React Native companion app
├── deploy/
│   ├── docker-compose.prod.yml
│   ├── nginx/nginx.conf
│   └── ssl-init.sh
└── docker-compose.yml
```

## Design Patterns

- **Rule Engine** — `packages/rules/engine.py` collects all validators and returns a typed `GisCheckResult` with `violations[]` and a frozen GIS snapshot for the audit trail
- **Repository** — each FastAPI router owns its DB queries; shared schemas in `schemas.py` decouple transport from ORM models
- **Multi-tenant** — every resource is scoped to an `org_id`; `deps.py` injects the current organisation into every authenticated request
- **Background Scheduler** — APScheduler job refreshes stale GIS cache entries every 6 hours without blocking request threads
- **i18n / RTL** — all UI strings are externalised to `en/ar/he.json`; Arabic and Hebrew render RTL automatically

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 · Vite · i18next · CSS (no UI framework) |
| **Backend** | FastAPI · SQLAlchemy · APScheduler · Pydantic v2 |
| **AI** | Claude API — compliance report generation + SVG floor plan output |
| **Mobile** | Expo (React Native) |
| **Worker** | Celery + Redis |
| **Database** | PostgreSQL (prod) · SQLite (local dev) |
| **Infra** | Docker · Nginx · Let's Encrypt SSL |

## Installation

### Local (no Docker)

```bash
git clone https://github.com/DaoudSabat/AgriPermit.git
cd AgriPermit
```

Copy and fill in the environment files:

```bash
cp apps/api/.env.example apps/api/.env
cp deploy/.env.prod.example deploy/.env.prod
```

Then start all services:

```bat
start-local.bat
```

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Web | http://localhost:5173 |
| API docs | http://localhost:8000/docs |

### Docker (production)

```bash
docker compose -f deploy/docker-compose.prod.yml up -d
```

## Usage

1. Log in with your organisation credentials
2. **Land Check** tab — enter gush/helka parcel identifiers to run a GIS compliance check
3. **New Permit** tab — fill the MUI-style form; blocked violations prevent submission
4. **Design Upload** — attach a PDF floor plan; Claude generates an SVG overlay and compliance summary
5. **Permit List** — track status, download compliance reports

## Mobile

```bash
cd AgriPermitMobile
npm install
npx expo start
```

Scan the QR code with the Expo Go app.

## License

MIT
