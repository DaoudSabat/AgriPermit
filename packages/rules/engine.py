from dataclasses import dataclass, field

from .gis_client import get_gis_client
from .rules import RuleResult, run_all_rules


@dataclass
class GisCheckResult:
    flagged: bool                       # any violation present
    blocked: bool                       # at least one severity="block"
    violations: list[RuleResult] = field(default_factory=list)
    snapshot: dict = field(default_factory=dict)   # frozen GIS data for audit trail


def run_gis_check(
    parcel_id: str,
    gush: int | None,
    helka: int | None,
    zone: str,
    permit_type: str,
    requested_floors: int | None = None,
    requested_coverage_pct: float | None = None,
) -> GisCheckResult:
    client = get_gis_client()
    gis_data = client.fetch(parcel_id=parcel_id, gush=gush, helka=helka, zone=zone)

    violations = run_all_rules(
        gis=gis_data,
        permit_type=permit_type,
        requested_floors=requested_floors,
        requested_coverage_pct=requested_coverage_pct,
    )

    return GisCheckResult(
        flagged=len(violations) > 0,
        blocked=any(v.severity == "block" for v in violations),
        violations=violations,
        snapshot={
            # Full GIS zone fields — used by compliance reports and audit trail
            "zone":                 gis_data.zone,
            "zone_plan_id":         gis_data.zone_plan_id,
            "max_floors":           gis_data.max_floors,
            "max_coverage_pct":     gis_data.max_coverage_pct,
            "permitted_uses":       gis_data.permitted_uses,
            "is_protected_zone":    gis_data.is_protected_zone,
            "is_agricultural_freeze": gis_data.is_agricultural_freeze,
            "data_version":         gis_data.data_version,
            "raw":                  gis_data.raw,
        },
    )
