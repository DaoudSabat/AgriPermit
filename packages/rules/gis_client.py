"""
GIS client abstraction — Israel-wide coverage.

GIS_PROVIDER options:
  mock        — deterministic synthetic data, no network (default for dev/CI)
  jerusalem   — Jerusalem Municipality ArcGIS REST (layers 50 + 186)
  govmap      — GovMap national ArcGIS (ags.govmap.gov.il) — all Israel
  iplan       — IPLAN/Mavat national planning authority
  auto        — routes by gush: Jerusalem parcels → JerusalemGisClient,
                everything else → GovMapNationalClient, falls back to mock

Israel-wide coverage (GIS_PROVIDER=auto or govmap):
  Primary:  https://ags.govmap.gov.il/arcgis/rest/services/
  Fallback: https://mavat.iplan.gov.il/SV4/api/
  Local municipalities override for precision:
    Jerusalem  gush 30000-30999  → JerusalemGisClient
    (Tel Aviv, Haifa etc. added as municipality clients are confirmed)

Caching:
  All live GIS responses are written to SQLite (gis_zone_cache table).
  TTL defaults to 24 hours; configurable via GIS_CACHE_TTL_HOURS.
  Stale entries are refreshed in the background by APScheduler.
"""

import logging
import os
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class GisData:
    parcel_id: str
    gush: int | None
    helka: int | None
    zone: str
    zone_plan_id: str            # e.g. "תמא/35"
    max_floors: int              # קומות מותרות
    permitted_uses: list[str]    # e.g. ["agricultural", "residential"]
    max_coverage_pct: float      # אחוזי בנייה מקסימליים
    is_protected_zone: bool      # שמורת טבע / אתר מורשת
    is_agricultural_freeze: bool # הקפאת קרקע חקלאית
    data_version: str = ""       # provider version / fetch timestamp for audit
    raw: dict = field(default_factory=dict)


class GisClient(ABC):
    @abstractmethod
    def fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> GisData:
        ...


# ── Mock ─────────────────────────────────────────────────────────────────────

class MockGisClient(GisClient):
    """Deterministic synthetic data — safe for dev/CI, no network calls."""

    _PROFILES = [
        dict(zone="חקלאי מוגן",   plan="TM/35-A", floors=1, cov=5.0,   uses=["agricultural"],                                    protected=True,  freeze=True),
        dict(zone="חקלאי מדברי",  plan="TM/35-B", floors=2, cov=10.0,  uses=["agricultural"],                                    protected=False, freeze=True),
        dict(zone="חקלאי פרטי",   plan="TM/35-C", floors=3, cov=20.0,  uses=["agricultural", "residential"],                     protected=False, freeze=True),
        dict(zone="חקלאי עירוני", plan="TM/35-D", floors=4, cov=25.0,  uses=["agricultural", "residential", "commercial"],       protected=False, freeze=False),
        dict(zone="מגורים א",     plan="TM/35-E", floors=5, cov=40.0,  uses=["residential"],                                     protected=False, freeze=False),
        dict(zone="מגורים ב",     plan="TM/35-F", floors=8, cov=50.0,  uses=["residential", "commercial"],                      protected=False, freeze=False),
        dict(zone="מסחר ומשרדים", plan="TM/35-G", floors=12, cov=70.0, uses=["residential", "commercial"],                      protected=False, freeze=False),
        dict(zone="תעשייה",       plan="TM/35-H", floors=6, cov=60.0,  uses=["industrial"],                                     protected=False, freeze=False),
        dict(zone="שמורת טבע",    plan="TM/35-I", floors=0, cov=2.0,   uses=["agricultural"],                                   protected=True,  freeze=True),
        dict(zone="גן לאומי",     plan="TM/35-J", floors=1, cov=5.0,   uses=["agricultural"],                                   protected=True,  freeze=True),
        dict(zone="חקלאי",        plan="TM/35-K", floors=2, cov=15.0,  uses=["agricultural"],                                   protected=False, freeze=True),
        dict(zone="מגורים כפרי",  plan="TM/35-L", floors=3, cov=30.0,  uses=["agricultural", "residential"],                   protected=False, freeze=False),
    ]

    def fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> GisData:
        seed = (gush or 0) * 1000 + (helka or 0)
        p = self._PROFILES[seed % len(self._PROFILES)]
        explicit = next((x for x in self._PROFILES if x["zone"] == zone), None)
        if explicit:
            p = explicit
        return GisData(
            parcel_id=parcel_id, gush=gush, helka=helka,
            zone=p["zone"], zone_plan_id=p["plan"],
            max_floors=p["floors"], permitted_uses=p["uses"],
            max_coverage_pct=p["cov"],
            is_protected_zone=p["protected"], is_agricultural_freeze=p["freeze"],
            data_version="mock-v1",
            raw={"source": "mock", "gush": gush, "helka": helka},
        )


# ── Jerusalem Municipality ArcGIS REST ───────────────────────────────────────

class JerusalemGisClient(GisClient):
    """
    Jerusalem Municipality ArcGIS REST.
    Layer 50: ייעודי קרקע (land use)
    Layer 186: תממ 1_30 מגבלות (restrictions)
    Auth: Referer header only — no API key required.
    """

    BASE    = "https://gisviewer.jerusalem.muni.il/arcgis/rest/services/BaseLayers/MapServer"
    REFERER = "https://jergisng.jerusalem.muni.il/"

    _GUSH_CANDIDATES  = ["GUSH_",  "GUSH",  "GUS_NUM",  "GUS_",  "BLOCK_NUM"]
    _HELKA_CANDIDATES = ["HELKA_", "HELKA", "HLK_NUM",  "HLK_",  "PARCEL_NUM"]
    _ZONE_NAME_KEYS   = ["YAYUD",    "DESIGNATION", "ZONE_NAME", "YIYUD",    "ZONE_HEB", "SHIMUSH"]
    _PLAN_ID_KEYS     = ["TABA",     "PLAN_NUM",    "TABA_NUM",  "TOCHNI",   "PLAN_ID"]
    _FLOORS_KEYS      = ["KOMOTOT",  "MAX_FLOORS",  "KOMOT",     "FLOORS",   "KOM_"]
    _COVERAGE_KEYS    = ["AHUZIM",   "COVERAGE_PCT","ACHUZIM",   "MAX_COV",  "COV_PCT"]
    _PROTECTED_KEYS   = ["IS_PROTECTED", "SHMURAH", "MEHUGAN",   "PROTECTED"]
    _AG_FREEZE_KEYS   = ["AG_FREEZE",    "HAKPAA",  "HEKPAAT",   "FREEZE"]

    def __init__(self):
        import requests
        self._s = requests.Session()
        self._s.headers.update({
            "Referer":    self.REFERER,
            "Origin":     "https://jergisng.jerusalem.muni.il",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        })
        self._gush_field:  str | None = os.getenv("JGIS_GUSH_FIELD")
        self._helka_field: str | None = os.getenv("JGIS_HELKA_FIELD")

    def _layer_fields(self, layer_id: int) -> list[str]:
        r = self._s.get(f"{self.BASE}/{layer_id}", params={"f": "json"}, timeout=10)
        r.raise_for_status()
        return [f["name"] for f in r.json().get("fields", [])]

    def _discover_gush_helka(self) -> tuple[str, str]:
        if self._gush_field and self._helka_field:
            return self._gush_field, self._helka_field
        fields = self._layer_fields(50)
        gf = next((f for f in self._GUSH_CANDIDATES  if f in fields), None)
        hf = next((f for f in self._HELKA_CANDIDATES if f in fields), None)
        if not gf or not hf:
            raise RuntimeError(
                f"Cannot detect גוש/חלקה fields in layer 50. "
                f"Available: {fields}. Override with JGIS_GUSH_FIELD / JGIS_HELKA_FIELD."
            )
        self._gush_field, self._helka_field = gf, hf
        logger.info("Jerusalem GIS: detected גוש=%s חלקה=%s", gf, hf)
        return gf, hf

    def _query(self, layer_id: int, where: str) -> list[dict]:
        r = self._s.get(
            f"{self.BASE}/{layer_id}/query",
            params={"where": where, "outFields": "*", "returnGeometry": "false", "f": "json"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"ArcGIS layer {layer_id} error: {data['error']}")
        return [feat["attributes"] for feat in data.get("features", [])]

    @staticmethod
    def _pick(attrs: dict, *keys):
        for k in keys:
            if k in attrs and attrs[k] is not None:
                return attrs[k]
        return None

    def fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> GisData:
        if gush is None or helka is None:
            raise ValueError(f"Parcel {parcel_id} missing גוש/חלקה — required for Jerusalem GIS")

        gf, hf = self._discover_gush_helka()
        where   = f"{gf}={gush} AND {hf}={helka}"

        features = self._query(50, where)
        if not features:
            raise RuntimeError(f"Jerusalem GIS: no record for גוש {gush} חלקה {helka}")
        a = features[0]

        try:
            restrictions = self._query(186, where)
            r = restrictions[0] if restrictions else {}
        except Exception as exc:
            logger.warning("Jerusalem GIS layer 186 failed (%s) — skipped", exc)
            r = {}

        pick = self._pick
        zone_name    = str(pick(a, *self._ZONE_NAME_KEYS) or zone)
        zone_plan    = str(pick(a, *self._PLAN_ID_KEYS)   or "N/A")
        max_floors   = int(pick(a, *self._FLOORS_KEYS)    or 2)
        max_coverage = float(pick(a, *self._COVERAGE_KEYS) or 15.0)

        uses_raw = pick(a, "YAYUD_TYPE", "PERMITTED_USE", "SHIMUSH_MATAR")
        permitted_uses = (
            [u.strip() for u in str(uses_raw).split(",")]
            if uses_raw else _uses_from_zone(zone_name)
        )

        is_protected = bool(
            pick(r, *self._PROTECTED_KEYS) or
            any(kw in zone_name for kw in ("מוגן", "שמורה", "עתיקות", "ירוק"))
        )
        is_ag_freeze = bool(
            pick(r, *self._AG_FREEZE_KEYS) or "חקלאי" in zone_name
        )

        return GisData(
            parcel_id=parcel_id, gush=gush, helka=helka,
            zone=zone_name, zone_plan_id=zone_plan,
            max_floors=max_floors, permitted_uses=permitted_uses,
            max_coverage_pct=max_coverage,
            is_protected_zone=is_protected, is_agricultural_freeze=is_ag_freeze,
            data_version=f"jerusalem-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            raw={"source": "jerusalem_gis", "gush": gush, "helka": helka,
                 "layer_50": a, "layer_186": r},
        )


# ── GovMap National (Survey of Israel) ───────────────────────────────────────

class GovMapNationalClient(GisClient):
    """
    Survey of Israel / GovMap national ArcGIS REST service.
    Covers ALL of Israel — queryable by גוש/חלקה.

    Service root: https://ags.govmap.gov.il/arcgis/rest/services/
    Key layers:
      Yayud/          — land-use designations (ייעוד קרקע)
      Cadastre/       — parcel registry (גוש/חלקה)
      NaturalReserves/ — protected zones
    Referer: https://www.govmap.gov.il/ (required by the server)

    Requires no API key for public layers.
    """

    BASE    = "https://ags.govmap.gov.il/arcgis/rest/services"
    REFERER = "https://www.govmap.gov.il/"

    # Layer paths (confirmed from govmap.gov.il network inspector)
    LAND_USE_LAYER = "Yayud/MapServer/0"        # ייעוד קרקע ארצי
    CADASTRE_LAYER = "Cadastre/MapServer/0"      # גוש/חלקה
    NATURE_LAYER   = "NaturalReserves/MapServer/0"  # שמורות טבע

    _ZONE_KEYS     = ["YAYUD", "DESIGNATION", "SHIMUSH", "ZONE_NAME", "YIYUD_KARKA"]
    _PLAN_KEYS     = ["TABA", "TOCHNI", "PLAN_NUM", "TACHLIT"]
    _FLOORS_KEYS   = ["KOMOTOT", "MAX_FLOORS", "KOM_MAX", "KOMOT"]
    _COVERAGE_KEYS = ["AHUZIM", "COV_PCT", "MAX_COVERAGE", "ACHUZIM"]

    def __init__(self):
        import requests
        self._s = requests.Session()
        self._s.headers.update({
            "Referer":    self.REFERER,
            "Origin":     "https://www.govmap.gov.il",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        })

    def _query_layer(self, layer_path: str, where: str) -> list[dict]:
        url = f"{self.BASE}/{layer_path}/query"
        r = self._s.get(url, params={
            "where": where,
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }, timeout=12)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"GovMap layer {layer_path} error: {data['error']}")
        return [feat["attributes"] for feat in data.get("features", [])]

    @staticmethod
    def _pick(attrs: dict, *keys):
        for k in keys:
            if k in attrs and attrs[k] is not None:
                return attrs[k]
        return None

    def fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> GisData:
        if gush is None or helka is None:
            raise ValueError(f"Parcel {parcel_id} missing גוש/חלקה — required for GovMap national lookup")

        where = f"GUSH={gush} AND HELKA={helka}"

        # Land use layer (primary)
        try:
            features = self._query_layer(self.LAND_USE_LAYER, where)
        except Exception as exc:
            logger.warning("GovMap land-use layer failed (%s) — trying cadastre fallback", exc)
            features = []

        # If land-use layer has no result, try cadastre layer with same gush/helka
        if not features:
            try:
                features = self._query_layer(self.CADASTRE_LAYER, where)
            except Exception as exc:
                logger.warning("GovMap cadastre layer also failed (%s)", exc)
                features = []

        if not features:
            raise RuntimeError(
                f"GovMap: no record for גוש {gush} חלקה {helka}. "
                f"Check that the parcel exists in the national cadastre."
            )

        a = features[0]
        pick = self._pick

        # Protected zone lookup (best-effort)
        try:
            nature = self._query_layer(self.NATURE_LAYER, where)
            r = nature[0] if nature else {}
        except Exception:
            r = {}

        zone_name    = str(pick(a, *self._ZONE_KEYS)     or zone)
        zone_plan    = str(pick(a, *self._PLAN_KEYS)     or "תמא/35")
        max_floors   = int(pick(a, *self._FLOORS_KEYS)   or 2)
        max_coverage = float(pick(a, *self._COVERAGE_KEYS) or 15.0)

        is_protected = bool(r or any(kw in zone_name for kw in ("מוגן", "שמורה", "עתיקות", "ירוק", "פארק")))
        is_ag_freeze = "חקלאי" in zone_name

        return GisData(
            parcel_id=parcel_id, gush=gush, helka=helka,
            zone=zone_name, zone_plan_id=zone_plan,
            max_floors=max_floors,
            permitted_uses=_uses_from_zone(zone_name),
            max_coverage_pct=max_coverage,
            is_protected_zone=is_protected, is_agricultural_freeze=is_ag_freeze,
            data_version=f"govmap-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            raw={"source": "govmap_national", "gush": gush, "helka": helka,
                 "land_use": a, "nature": r},
        )


# ── IPLAN / Mavat (National Planning Authority) ──────────────────────────────

class IPlanClient(GisClient):
    """
    National Planning Administration (מנהל התכנון) — Mavat system.
    Provides active תוכניות (building plans) per parcel.
    Portal: https://mavat.iplan.gov.il/
    API:    https://mavat.iplan.gov.il/SV4/api/

    Used as a secondary enrichment source: the plan number, status, and
    restrictions come from here; zoning data from GovMap or Jerusalem.
    No API key required for public plan data.
    """

    API_BASE = "https://mavat.iplan.gov.il/SV4/api"

    def __init__(self):
        import requests
        self._s = requests.Session()
        self._s.headers.update({
            "Referer":    "https://mavat.iplan.gov.il/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        })

    def _get_plans(self, gush: int, helka: int) -> list[dict]:
        """Returns list of active תוכניות for the parcel."""
        r = self._s.get(
            f"{self.API_BASE}/PlansByParcel",
            params={"gush": gush, "helka": helka, "status": "active"},
            timeout=12,
        )
        r.raise_for_status()
        return r.json().get("plans", [])

    def fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> GisData:
        if gush is None or helka is None:
            raise ValueError(f"Parcel {parcel_id} missing גוש/חלקה — required for IPLAN")

        plans = self._get_plans(gush, helka)
        if not plans:
            raise RuntimeError(f"IPLAN: no active plans for גוש {gush} חלקה {helka}")

        # Use the most recently approved plan
        plan = plans[0]
        zone_name  = plan.get("zoneDesignation", zone)
        zone_plan  = plan.get("planNumber", "N/A")
        max_floors = int(plan.get("maxFloors", 2))
        max_cov    = float(plan.get("maxCoveragePct", 15.0))

        is_protected = bool(plan.get("isProtected", False))
        is_ag_freeze = "חקלאי" in zone_name

        return GisData(
            parcel_id=parcel_id, gush=gush, helka=helka,
            zone=zone_name, zone_plan_id=zone_plan,
            max_floors=max_floors,
            permitted_uses=_uses_from_zone(zone_name),
            max_coverage_pct=max_cov,
            is_protected_zone=is_protected, is_agricultural_freeze=is_ag_freeze,
            data_version=f"iplan-{plan.get('approvalDate', datetime.now(timezone.utc).strftime('%Y%m%d'))}",
            raw={"source": "iplan", "gush": gush, "helka": helka, "plans": plans},
        )


# ── Legacy GovMap WFS (kept for backward compat) ─────────────────────────────

class GovMapClient(GisClient):
    """GovMap WFS — configure with GOVMAP_WFS_URL env var."""

    def __init__(self):
        self.wfs_url = os.environ["GOVMAP_WFS_URL"]
        self.api_key = os.getenv("GOVMAP_API_KEY", "")

    def fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> GisData:
        if gush is None or helka is None:
            raise ValueError(f"Parcel {parcel_id} missing גוש/חלקה — required for GovMap WFS")

        import requests
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        params  = {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeName": os.getenv("GOVMAP_LAYER", "ZONING_PLAN"),
            "CQL_FILTER": f"GUSH={gush} AND HELKA={helka}",
            "outputFormat": "application/json",
        }
        resp = requests.get(self.wfs_url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        props = resp.json()["features"][0]["properties"]

        return GisData(
            parcel_id=parcel_id, gush=gush, helka=helka,
            zone=props.get("ZONE_NAME", zone),
            zone_plan_id=props.get("PLAN_ID", ""),
            max_floors=int(props.get("MAX_FLOORS", 2)),
            permitted_uses=props.get("PERMITTED_USES", "agricultural").split(","),
            max_coverage_pct=float(props.get("MAX_COVERAGE_PCT", 15.0)),
            is_protected_zone=bool(props.get("IS_PROTECTED", False)),
            is_agricultural_freeze=bool(props.get("IS_AG_FREEZE", False)),
            data_version=f"govmap-wfs-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            raw={"source": "govmap_wfs", "gush": gush, "helka": helka, **props},
        )


# ── Israel-wide Router ────────────────────────────────────────────────────────

# Gush ranges by municipality (approximate — exact boundaries from ILA cadastre)
# Source: Israel Land Authority cadastre block allocations
_JERUSALEM_GUSH_RANGES = [(30000, 30999)]
_TEL_AVIV_GUSH_RANGES  = [(6000,  7499)]
_HAIFA_GUSH_RANGES     = [(10000, 12999)]
_SOUTH_GUSH_RANGES     = [(38000, 42999)]   # Beer Sheva / Negev
_NORTH_GUSH_RANGES     = [(14000, 22999)]   # Galilee / North


def _gush_in_ranges(gush: int | None, ranges: list[tuple[int, int]]) -> bool:
    if gush is None:
        return False
    return any(lo <= gush <= hi for lo, hi in ranges)


class IsraelGisRouter(GisClient):
    """
    Routes GIS queries to the most authoritative available source:
      - Jerusalem gush range → JerusalemGisClient (municipality ArcGIS)
      - Everything else      → GovMapNationalClient (Survey of Israel)
      - If live call fails   → GisZoneCache (last known value)
      - If no cache          → MockGisClient (dev fallback)

    On success, writes result to the GIS zone cache.
    """

    def __init__(self):
        self._mock     = MockGisClient()
        self._cache    = _get_cache()  # GisZoneCache helper (may be None if DB unavailable)

    def _live_fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> tuple[GisData, str]:
        """Returns (data, provider_name). Raises on total failure."""
        errors = []

        if _gush_in_ranges(gush, _JERUSALEM_GUSH_RANGES):
            try:
                client = JerusalemGisClient()
                return client.fetch(parcel_id, gush, helka, zone), "jerusalem"
            except Exception as exc:
                logger.warning("Jerusalem GIS failed (%s) — falling back to GovMap", exc)
                errors.append(f"jerusalem: {exc}")

        # GovMap national — covers all Israel
        try:
            client = GovMapNationalClient()
            return client.fetch(parcel_id, gush, helka, zone), "govmap_national"
        except Exception as exc:
            logger.warning("GovMap national failed (%s) — trying IPLAN", exc)
            errors.append(f"govmap: {exc}")

        # IPLAN as last live option
        try:
            client = IPlanClient()
            return client.fetch(parcel_id, gush, helka, zone), "iplan"
        except Exception as exc:
            errors.append(f"iplan: {exc}")

        raise RuntimeError("All live GIS sources failed: " + " | ".join(errors))

    def fetch(self, parcel_id: str, gush: int | None, helka: int | None, zone: str) -> GisData:
        # 1. Try live sources
        try:
            data, provider = self._live_fetch(parcel_id, gush, helka, zone)
            if self._cache:
                self._cache.store(gush, helka, provider, data)
            return data
        except Exception as live_exc:
            logger.warning("All live GIS sources failed: %s", live_exc)

        # 2. Cache fallback
        if self._cache:
            cached = self._cache.get(gush, helka)
            if cached:
                logger.info("Using cached GIS data for גוש %s חלקה %s (age: %s)", gush, helka, cached.age)
                return cached.to_gis_data()

        # 3. Mock fallback (dev / CI)
        logger.warning("GIS cache miss — using mock data for גוש %s חלקה %s", gush, helka)
        return self._mock.fetch(parcel_id, gush, helka, zone)


# ── GIS Zone Cache ────────────────────────────────────────────────────────────

_CACHE_TTL_HOURS = int(os.getenv("GIS_CACHE_TTL_HOURS", "24"))


class _CacheEntry:
    def __init__(self, gush, helka, provider, data_json: str, fetched_at: datetime):
        self.gush       = gush
        self.helka      = helka
        self.provider   = provider
        self._data      = json.loads(data_json)
        self.fetched_at = fetched_at

    @property
    def age(self) -> timedelta:
        return datetime.now(timezone.utc) - self.fetched_at

    @property
    def is_stale(self) -> bool:
        return self.age > timedelta(hours=_CACHE_TTL_HOURS)

    def to_gis_data(self) -> GisData:
        d = self._data
        return GisData(
            parcel_id=d.get("parcel_id", ""),
            gush=d.get("gush"), helka=d.get("helka"),
            zone=d.get("zone", "חקלאי"),
            zone_plan_id=d.get("zone_plan_id", "N/A"),
            max_floors=d.get("max_floors", 2),
            permitted_uses=d.get("permitted_uses", ["agricultural"]),
            max_coverage_pct=d.get("max_coverage_pct", 15.0),
            is_protected_zone=d.get("is_protected_zone", False),
            is_agricultural_freeze=d.get("is_agricultural_freeze", True),
            data_version=d.get("data_version", "cache"),
            raw={**d.get("raw", {}), "source": f"cache({self.provider})",
                 "cached_at": self.fetched_at.isoformat()},
        )


class _GisZoneCache:
    """SQLite-backed GIS response cache. Thread-safe via SQLAlchemy."""

    def __init__(self, engine):
        self._engine = engine
        self._ensure_table()

    def _ensure_table(self):
        from sqlalchemy import text
        with self._engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gis_zone_cache (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    gush       INTEGER NOT NULL,
                    helka      INTEGER NOT NULL,
                    provider   TEXT    NOT NULL,
                    data_json  TEXT    NOT NULL,
                    fetched_at TEXT    NOT NULL,
                    UNIQUE(gush, helka)
                )
            """))
            conn.commit()

    def get(self, gush: int | None, helka: int | None) -> _CacheEntry | None:
        if gush is None or helka is None:
            return None
        from sqlalchemy import text
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT provider, data_json, fetched_at FROM gis_zone_cache WHERE gush=:g AND helka=:h"),
                {"g": gush, "h": helka}
            ).fetchone()
        if not row:
            return None
        fetched_at = datetime.fromisoformat(row[2])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return _CacheEntry(gush, helka, row[0], row[1], fetched_at)

    def store(self, gush: int | None, helka: int | None, provider: str, data: GisData):
        if gush is None or helka is None:
            return
        payload = {
            "parcel_id": data.parcel_id, "gush": data.gush, "helka": data.helka,
            "zone": data.zone, "zone_plan_id": data.zone_plan_id,
            "max_floors": data.max_floors, "permitted_uses": data.permitted_uses,
            "max_coverage_pct": data.max_coverage_pct,
            "is_protected_zone": data.is_protected_zone,
            "is_agricultural_freeze": data.is_agricultural_freeze,
            "data_version": data.data_version, "raw": data.raw,
        }
        from sqlalchemy import text
        with self._engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO gis_zone_cache (gush, helka, provider, data_json, fetched_at)
                VALUES (:g, :h, :p, :d, :t)
                ON CONFLICT(gush, helka) DO UPDATE SET
                    provider=excluded.provider,
                    data_json=excluded.data_json,
                    fetched_at=excluded.fetched_at
            """), {"g": gush, "h": helka, "p": provider,
                   "d": json.dumps(payload, ensure_ascii=False),
                   "t": datetime.now(timezone.utc).isoformat()})
            conn.commit()

    def stale_entries(self) -> list[_CacheEntry]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=_CACHE_TTL_HOURS)).isoformat()
        from sqlalchemy import text
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT gush, helka, provider, data_json, fetched_at FROM gis_zone_cache WHERE fetched_at < :c"),
                {"c": cutoff}
            ).fetchall()
        result = []
        for row in rows:
            ft = datetime.fromisoformat(row[4])
            if ft.tzinfo is None:
                ft = ft.replace(tzinfo=timezone.utc)
            result.append(_CacheEntry(row[0], row[1], row[2], row[3], ft))
        return result


_cache_instance: _GisZoneCache | None = None


def _get_cache() -> _GisZoneCache | None:
    global _cache_instance
    if _cache_instance is not None:
        return _cache_instance
    try:
        import sys, pathlib
        # Try to import the app's SQLAlchemy engine
        _api = pathlib.Path(__file__).parent.parent.parent / "apps" / "api"
        if str(_api) not in sys.path:
            sys.path.insert(0, str(_api))
        from database import engine
        _cache_instance = _GisZoneCache(engine)
        return _cache_instance
    except Exception as exc:
        logger.warning("GIS cache unavailable (%s) — live-only mode", exc)
        return None


def refresh_stale_cache():
    """Refresh all stale cache entries. Called by the APScheduler background job."""
    cache = _get_cache()
    if not cache:
        return
    stale = cache.stale_entries()
    if not stale:
        logger.info("GIS cache refresh: all entries are fresh")
        return
    logger.info("GIS cache refresh: refreshing %d stale entries", len(stale))
    router = IsraelGisRouter()
    for entry in stale:
        try:
            data = router._live_fetch(
                parcel_id=f"{entry.gush}/{entry.helka}",
                gush=entry.gush, helka=entry.helka, zone="חקלאי"
            )[0]
            cache.store(entry.gush, entry.helka, entry.provider, data)
            logger.info("Refreshed GIS cache for גוש %s חלקה %s", entry.gush, entry.helka)
        except Exception as exc:
            logger.warning("Cache refresh failed for גוש %s חלקה %s: %s", entry.gush, entry.helka, exc)


# ── helpers ───────────────────────────────────────────────────────────────────

def _uses_from_zone(zone_name: str) -> list[str]:
    z = zone_name or ""
    if any(kw in z for kw in ("מסחר", "עסקים")):        return ["agricultural", "residential", "commercial"]
    if any(kw in z for kw in ("מגורים", "דיור")):        return ["agricultural", "residential"]
    if any(kw in z for kw in ("תעשייה", "תעש")):         return ["industrial"]
    if any(kw in z for kw in ("חקלאי", "כפרי", "חקל")): return ["agricultural"]
    return ["agricultural"]


def get_gis_client() -> GisClient:
    provider = os.getenv("GIS_PROVIDER", "mock").lower()
    if provider == "jerusalem":
        return JerusalemGisClient()
    if provider == "govmap_national" or provider == "national":
        return GovMapNationalClient()
    if provider == "iplan":
        return IPlanClient()
    if provider == "govmap" or os.getenv("GOVMAP_WFS_URL"):
        return GovMapClient()
    if provider == "auto":
        return IsraelGisRouter()
    return MockGisClient()
