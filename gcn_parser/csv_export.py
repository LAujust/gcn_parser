import csv
import sys
from typing import Optional

from .models import CircularExtraction


_CSV_FIELDNAMES = [
    "gcn_number",
    "utc",
    "mjd",
    "value",
    "unit",
    "band",
    "instrument",
    "upper_limit",
]


def build_lightcurve_csv(
    extractions: list[dict],
    csv_path: Optional[str] = None,
) -> None:
    """Flatten flux/magnitude measurements from all circulars into a single CSV.

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
            rows.append(
                {
                    "gcn_number": gcn_number,
                    "utc": m.utc if hasattr(m, "utc") else m.get("utc", ""),
                    "mjd": (
                        m.mjd if hasattr(m, "mjd") and m.mjd is not None
                        else m.get("mjd") if m.get("mjd") is not None
                        else ""
                    ),
                    "value": (
                        m.value if hasattr(m, "value") and m.value is not None
                        else m.get("value") if m.get("value") is not None
                        else ""
                    ),
                    "unit": m.unit if hasattr(m, "unit") else m.get("unit", ""),
                    "band": m.band if hasattr(m, "band") else m.get("band", ""),
                    "instrument": m.instrument if hasattr(m, "instrument") else m.get("instrument", ""),
                    "upper_limit": "true" if (
                        m.upper_limit if hasattr(m, "upper_limit") else m.get("upper_limit")
                    ) else "false",
                }
            )

    # Sort by UTC string if present (simple lexicographic sort)
    rows.sort(key=lambda r: r["utc"] or "")

    output = open(csv_path, "w", newline="") if csv_path else sys.stdout
    try:
        writer = csv.DictWriter(output, fieldnames=_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if csv_path:
            output.close()
