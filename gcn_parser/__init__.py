"""GCN Circular structured extractor."""

__version__ = "0.1.0"

from .archive import fetch_event_circulars
from .extractor import extract_circular
from .csv_export import build_lightcurve_csv

__all__ = ["fetch_event_circulars", "extract_circular", "build_lightcurve_csv"]
