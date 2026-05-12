import csv
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import CircularExtraction

_CSV_FIELDNAMES = [
    "gcn_number",
    "utc",
    "mjd",
    "value",
    "err",
    "unit",
    "band",
    "instrument",
    "upper_limit",
]

# MJD epoch: 1858-11-17 00:00:00 UTC
_MJD_EPOCH = datetime(1858, 11, 17, 0, 0, 0, tzinfo=timezone.utc)

# Band name normalization mapping (lowercase input -> canonical output)
_BAND_MAP = {
    "u": "u",
    "g": "g",
    "r": "r",
    "i": "i",
    "z": "z",
    "y": "y",
    "u-band": "u",
    "g-band": "g",
    "r-band": "r",
    "i-band": "i",
    "z-band": "z",
    "y-band": "y",
    "u band": "u",
    "g band": "g",
    "r band": "r",
    "i band": "i",
    "z band": "z",
    "y band": "y",
    "U": "U",
    "B": "B",
    "V": "V",
    "R": "R",
    "I": "I",
    "U-band": "U",
    "B-band": "B",
    "V-band": "V",
    "R-band": "R",
    "I-band": "I",
    "U band": "U",
    "B band": "B",
    "V band": "V",
    "R band": "R",
    "I band": "I",
    "J": "J",
    "H": "H",
    "K": "K",
    "Ks": "Ks",
    "K-short": "Ks",
    "K_s": "Ks",
    "L": "L",
    "M": "M",
    "vt_r": "R",
    "vt_b": "B",
    "vt_g": "g",
    "white": "White",
    "clear": "Clear",
}


def _parse_utc(utc_str: str) -> Optional[datetime]:
    """Parse a UTC datetime string with multiple fallback formats."""
    if not utc_str or not isinstance(utc_str, str):
        return None
    # Clean common suffixes/prefixes
    utc_str = utc_str.strip()
    utc_str = re.sub(r"\s+UTC$", "Z", utc_str, flags=re.IGNORECASE)
    utc_str = re.sub(r"UT$", "Z", utc_str, flags=re.IGNORECASE)
    utc_str = utc_str.replace(" ", "T")
    # Ensure Z suffix if no timezone info
    if "+" not in utc_str and "-" not in utc_str[10:] and not utc_str.endswith("Z"):
        utc_str = utc_str + "Z"
    # Replace Z with +00:00 for fromisoformat compatibility
    utc_str = utc_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(utc_str)
    except ValueError:
        pass
    # Fallback patterns
    patterns = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M%z",
        "%Y-%m-%dT%H:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ]
    for pat in patterns:
        try:
            return datetime.strptime(utc_str, pat)
        except ValueError:
            continue
    return None


def _utc_to_mjd(dt: datetime) -> float:
    """Convert a datetime to Modified Julian Date."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - _MJD_EPOCH
    return delta.total_seconds() / 86400.0


def _mjd_to_utc(mjd: float) -> str:
    """Convert Modified Julian Date to ISO-8601 UTC string."""
    dt = _MJD_EPOCH + timedelta(days=mjd)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _fill_utc_mjd(row: dict) -> dict:
    """Cross-fill UTC and MJD when one is present and the other is missing."""
    utc = row.get("utc")
    mjd = row.get("mjd")

    # Parse existing MJD
    mjd_val = None
    if mjd not in (None, ""):
        try:
            mjd_val = float(mjd)
        except (ValueError, TypeError):
            pass

    # Parse existing UTC
    dt = _parse_utc(utc) if utc not in (None, "") else None

    # Fill missing fields
    if dt is not None and mjd_val is None:
        row["mjd"] = round(_utc_to_mjd(dt), 6)
    elif mjd_val is not None and dt is None:
        row["utc"] = _mjd_to_utc(mjd_val)

    return row


def _standardize_band(band: str) -> str:
    """Standardize photometric band names."""
    if not band or not isinstance(band, str):
        return band
    raw = band.strip()
    # Direct lookup (case-sensitive first for multi-char like Ks)
    if raw in _BAND_MAP:
        return _BAND_MAP[raw]
    # Case-insensitive lookup
    lowered = raw.lower()
    if lowered in _BAND_MAP:
        return _BAND_MAP[lowered]
    # Remove common noise words and retry
    cleaned = re.sub(r"\s*(band|filter|mag|AB)\s*", "", raw, flags=re.IGNORECASE).strip()
    if cleaned in _BAND_MAP:
        return _BAND_MAP[cleaned]
    if cleaned.lower() in _BAND_MAP:
        return _BAND_MAP[cleaned.lower()]
    # Return original if no match found
    return raw


def _standardize_row(row: dict) -> dict:
    """Apply UTC/MJD fill and band standardization to a CSV row."""
    row = _fill_utc_mjd(row)
    row["band"] = _standardize_band(row.get("band", ""))
    return row


def build_lightcurve_csv(
    extractions: list[dict],
    csv_path: Optional[str] = None,
) -> None:
    """Flatten flux/magnitude measurements from all circulars into a single CSV.

    Missing UTC/MJD values are cross-filled when possible, and band names are
    standardized before writing.

    Args:
        extractions: List of dicts with keys ``gcn`` and ``extraction``.
        csv_path: Destination file path. If ``None``, writes to ``stdout``.
    """
    rows = []
    for item in extractions:
        gcn_number = item.get("gcn", "").split(" ")[-1]
        extraction = item.get("extraction")
        if not extraction:
            continue
        # Handle both CircularExtraction objects and plain dicts
        if isinstance(extraction, CircularExtraction):
            flux_list = extraction.flux_magnitude or []
        else:
            flux_list = extraction.get("flux_magnitude") or []
        if not flux_list:
            continue
        for m in flux_list:
            if isinstance(m, CircularExtraction):
                # shouldn't happen, but keep type checker happy
                continue
            val = (
                m.value if hasattr(m, "value") and m.value is not None
                else m.get("value") if m.get("value") is not None
                else ""
            )
            err = (
                m.err if hasattr(m, "err") and m.err is not None
                else m.get("err") if m.get("err") is not None
                else ""
            )
            is_ul = bool(
                m.upper_limit if hasattr(m, "upper_limit") else m.get("upper_limit")
            )

            # Transform upper limits: value=0, err=original value
            if is_ul and val not in (None, ""):
                err = val
                val = 0

            row = {
                "gcn_number": gcn_number,
                "utc": m.utc if hasattr(m, "utc") else m.get("utc", ""),
                "mjd": (
                    m.mjd if hasattr(m, "mjd") and m.mjd is not None
                    else m.get("mjd") if m.get("mjd") is not None
                    else ""
                ),
                "value": val,
                "err": err,
                "unit": m.unit if hasattr(m, "unit") else m.get("unit", ""),
                "band": m.band if hasattr(m, "band") else m.get("band", ""),
                "instrument": m.instrument if hasattr(m, "instrument") else m.get("instrument", ""),
                "upper_limit": int(is_ul),
            }
            rows.append(_standardize_row(row))

    # Sort by UTC string if present, fall back to MJD
    rows.sort(key=lambda r: (r.get("utc") or "", r.get("mjd") or 0))

    output = open(csv_path, "w", newline="") if csv_path else sys.stdout
    try:
        writer = csv.DictWriter(output, fieldnames=_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if csv_path:
            output.close()
