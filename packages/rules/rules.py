"""
The five GIS-backed permit validation rules.

Each function returns a RuleResult if a violation is found, or None if the rule passes.
Only violations (non-None returns) are collected and stored on the permit.
"""

from dataclasses import dataclass

from .gis_client import GisData

# Permit types that map to a required land-use category
_USE_REQUIREMENTS: dict[str, str] = {
    "agricultural": "agricultural",
    "construction": "residential",
    "water":        "agricultural",
    # "other" has no automatic use requirement — reviewer checks manually
}


@dataclass
class RuleResult:
    rule: str
    severity: str   # "block" | "warn"
    message: str

    def to_dict(self) -> dict:
        return {"rule": self.rule, "severity": self.severity, "message": self.message}


# ── Rule 1: number of floors ────────────────────────────────────────────────

def check_floors(gis: GisData, requested_floors: int | None) -> RuleResult | None:
    if requested_floors is None:
        return None
    if requested_floors > gis.max_floors:
        return RuleResult(
            rule="floors",
            severity="block",
            message=(
                f"מספר קומות מבוקש ({requested_floors}) "
                f"עולה על המותר בתכנית {gis.zone_plan_id} "
                f"({gis.max_floors} קומות)"
            ),
        )
    return None


# ── Rule 2: permitted land use ───────────────────────────────────────────────

def check_permitted_use(gis: GisData, permit_type: str) -> RuleResult | None:
    required = _USE_REQUIREMENTS.get(permit_type)
    if required is None:
        return None
    if required not in gis.permitted_uses:
        return RuleResult(
            rule="permitted_use",
            severity="block",
            message=(
                f"ייעוד המגרש אינו מתיר שימוש הנדרש לרישיון '{permit_type}'. "
                f"ייעודים מותרים: {', '.join(gis.permitted_uses)}"
            ),
        )
    return None


# ── Rule 3: building coverage percentage ────────────────────────────────────

def check_coverage(gis: GisData, requested_coverage_pct: float | None) -> RuleResult | None:
    if requested_coverage_pct is None:
        return None
    if requested_coverage_pct > gis.max_coverage_pct:
        return RuleResult(
            rule="coverage",
            severity="block",
            message=(
                f"אחוז בנייה מבוקש ({requested_coverage_pct}%) "
                f"עולה על המותר ({gis.max_coverage_pct}%)"
            ),
        )
    return None


# ── Rule 4: protected / conservation zone ───────────────────────────────────

def check_protected_zone(gis: GisData) -> RuleResult | None:
    if gis.is_protected_zone:
        return RuleResult(
            rule="protected_zone",
            severity="block",
            message="המגרש ממוקם באזור מוגן (שמורת טבע / אתר מורשת). נדרש אישור מיוחד",
        )
    return None


# ── Rule 5: agricultural land freeze ────────────────────────────────────────

def check_agricultural_freeze(gis: GisData, permit_type: str) -> RuleResult | None:
    if not gis.is_agricultural_freeze:
        return None
    if permit_type == "construction":
        return RuleResult(
            rule="agricultural_freeze",
            severity="block",
            message="קרקע חקלאית מוקפאת — בנייה אינה מותרת ללא שינוי ייעוד מוסדר (הליך תב\"ע)",
        )
    # non-construction permits on frozen ag land are flagged but not hard-blocked
    return RuleResult(
        rule="agricultural_freeze",
        severity="warn",
        message="קרקע חקלאית מוקפאת — נדרשת בדיקה נוספת של הרשות המקומית",
    )


# ── Collect all rules ────────────────────────────────────────────────────────

def run_all_rules(
    gis: GisData,
    permit_type: str,
    requested_floors: int | None,
    requested_coverage_pct: float | None,
) -> list[RuleResult]:
    candidates = [
        check_floors(gis, requested_floors),
        check_permitted_use(gis, permit_type),
        check_coverage(gis, requested_coverage_pct),
        check_protected_zone(gis),
        check_agricultural_freeze(gis, permit_type),
    ]
    return [r for r in candidates if r is not None]
