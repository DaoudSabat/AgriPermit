"""
Design file parser — extracts permit-relevant parameters from uploaded engineering documents.

Supported formats:
  PDF  — extracts text with pdfplumber, scans for Hebrew/English keywords
  DXF  — (future) requires ezdxf; placeholder returns empty result

Extracted parameters:
  floors          — number of storeys requested
  coverage_pct    — building footprint as % of parcel area
  area_sqm        — total built area in m²
  description     — free-text project description found in the document
  engineer_name   — signatory engineer name (if found)
  engineer_license— engineer license number (if found)
  raw_text        — first 2000 chars of extracted text (for audit / manual review)

Usage:
    with open("design.pdf", "rb") as f:
        result = parse_design_file(f.read(), filename="design.pdf")
    print(result.floors, result.coverage_pct)
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DesignParams:
    floors: int | None             = None
    coverage_pct: float | None     = None
    area_sqm: float | None         = None
    description: str               = ""
    engineer_name: str             = ""
    engineer_license: str          = ""
    raw_text: str                  = ""
    warnings: list[str]            = field(default_factory=list)
    source_format: str             = "unknown"


# ── Regex patterns (Hebrew + English) ─────────────────────────────────────────

# Floors: "3 קומות", "קומות: 3", "floors: 3", "3 floors", "3-story", "3 storeys"
_RE_FLOORS = re.compile(
    r'(?:'
    r'(\d+)\s*(?:קומות|קומה|floors?|storeys?|stories)'  # number first
    r'|(?:קומות|קומה|floors?|storeys?|stories)\s*[:\-]?\s*(\d+)'  # label first
    r'|(?:מספר\s*קומות|num(?:ber)?\s*of\s*floors?)\s*[:\-]?\s*(\d+)'
    r')',
    re.IGNORECASE,
)

# Coverage %: "אחוז בנייה: 25%", "coverage: 25%", "25% coverage", "25 אחוז"
_RE_COVERAGE = re.compile(
    r'(?:'
    r'(\d+(?:\.\d+)?)\s*%?\s*(?:אחוז(?:י)?\s*בנייה|coverage|כיסוי|building\s*coverage)'
    r'|(?:אחוז(?:י)?\s*בנייה|coverage|כיסוי|building\s*coverage)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?'
    r')',
    re.IGNORECASE,
)

# Area m²: "שטח: 250 מ"ר", "total area: 250 m2", "250 sqm", "250מ"ר"
_RE_AREA = re.compile(
    r'(?:'
    r'(\d+(?:\.\d+)?)\s*(?:מ["\']ר|m²|m2|sqm|sq\.?m)'
    r'|(?:שטח(?:\s*כולל)?|total\s*area|built\s*area)\s*[:\-]?\s*(\d+(?:\.\d+)?)'
    r')',
    re.IGNORECASE,
)

# Engineer name: "מהנדס: ישראל ישראלי", "Eng. John Smith", "engineer: ..."
_RE_ENGINEER = re.compile(
    r'(?:מהנדס(?:\s*מוסמך)?|Eng(?:ineer)?\.?)\s*[:\-]?\s*([^\n\r,]{3,40})',
    re.IGNORECASE,
)

# Engineer license: "רישיון מס' 12345", "license no. 12345", "lic: 12345"
_RE_LICENSE = re.compile(
    r'(?:רישיון\s*(?:מס[\'"]?|מספר)?|lic(?:ense|ensure)?\.?\s*(?:no\.?)?)\s*[:\-]?\s*([A-Z]?\d{4,8})',
    re.IGNORECASE,
)

# Description: first paragraph after "תיאור הפרויקט" / "project description"
_RE_DESCRIPTION = re.compile(
    r'(?:תיאור\s*הפרויקט|project\s*description)\s*[:\-]?\s*(.{10,300}?)(?:\n|$)',
    re.IGNORECASE | re.DOTALL,
)


# ── Extraction helpers ─────────────────────────────────────────────────────────

def _first_int(m: re.Match | None) -> int | None:
    if not m:
        return None
    for g in m.groups():
        if g is not None:
            try:
                return int(g)
            except ValueError:
                pass
    return None


def _first_float(m: re.Match | None) -> float | None:
    if not m:
        return None
    for g in m.groups():
        if g is not None:
            try:
                return float(g)
            except ValueError:
                pass
    return None


def _scan_text(text: str) -> DesignParams:
    params = DesignParams(raw_text=text[:2000], source_format="pdf")

    params.floors       = _first_int(_RE_FLOORS.search(text))
    params.coverage_pct = _first_float(_RE_COVERAGE.search(text))
    params.area_sqm     = _first_float(_RE_AREA.search(text))

    m_eng = _RE_ENGINEER.search(text)
    if m_eng:
        params.engineer_name = m_eng.group(1).strip()

    m_lic = _RE_LICENSE.search(text)
    if m_lic:
        params.engineer_license = m_lic.group(1).strip()

    m_desc = _RE_DESCRIPTION.search(text)
    if m_desc:
        params.description = m_desc.group(1).strip()

    # Sanity warnings
    if params.floors is None:
        params.warnings.append("Could not detect number of floors — please enter manually")
    elif params.floors > 20:
        params.warnings.append(f"Unusually high floor count detected ({params.floors}) — please verify")

    if params.coverage_pct is None:
        params.warnings.append("Could not detect coverage % — please enter manually")
    elif params.coverage_pct > 100:
        params.warnings.append(f"Coverage {params.coverage_pct}% > 100% — likely a parsing error")

    return params


# ── Format-specific parsers ────────────────────────────────────────────────────

def _parse_pdf(data: bytes) -> str:
    try:
        import pdfplumber
        import io
        text_parts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages[:10]:  # limit to first 10 pages
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("pdfplumber not installed — PDF text extraction unavailable")
        return ""
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return ""


def _parse_dxf(data: bytes) -> str:
    """DXF/DWG text extraction — extracts MTEXT and TEXT entities."""
    try:
        import ezdxf
        import io
        doc = ezdxf.read(io.BytesIO(data))
        texts = []
        for entity in doc.modelspace():
            if entity.dxftype() in ("TEXT", "MTEXT"):
                t = getattr(entity.dxf, "text", "") or getattr(entity.dxf, "plain_mtext", "")
                if t:
                    texts.append(str(t))
        return "\n".join(texts)
    except ImportError:
        return ""  # ezdxf optional — not required for PDF-only flow
    except Exception as exc:
        logger.warning("DXF extraction failed: %s", exc)
        return ""


# ── Public API ────────────────────────────────────────────────────────────────

def parse_design_file(data: bytes, filename: str) -> DesignParams:
    """
    Parse a design file and return extracted DesignParams.
    Supports PDF (pdfplumber) and DXF/DWG (ezdxf if installed).
    Falls back to empty params with a warning if format is unsupported.
    """
    lower = filename.lower()

    if lower.endswith(".pdf"):
        text = _parse_pdf(data)
        if not text.strip():
            params = DesignParams(source_format="pdf")
            params.warnings.append("PDF has no extractable text (may be scanned image). Enter parameters manually.")
            return params
        return _scan_text(text)

    if lower.endswith((".dxf", ".dwg")):
        text = _parse_dxf(data)
        params = _scan_text(text) if text.strip() else DesignParams(source_format="dxf")
        params.source_format = "dxf"
        if not text.strip():
            params.warnings.append("DXF/DWG has no extractable text annotations. Enter parameters manually.")
        return params

    params = DesignParams(source_format="unsupported")
    params.warnings.append(f"Unsupported file format: {filename}. Supported: PDF, DXF, DWG.")
    return params
