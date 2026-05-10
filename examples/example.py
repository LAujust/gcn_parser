"""Basic usage example for gcn-circular-llm.

This script demonstrates how to:
1. Fetch all GCN circulars for a given event
2. Extract structured astrophysical information from each circular
3. Save the results as JSON and a light-curve CSV

Before running, set your OpenRouter API key either:
- via environment variable: export OPENROUTER_API_KEY=sk-or-v1-...
- in a .env file in the working directory
- or pass it directly to extract_circular() as shown below
"""

import json
import os
import sys

from gcn_parser import extract_circular, fetch_event_circulars
from gcn_parser.csv_export import build_lightcurve_csv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EVENT = "EP260131a"  # Change this to any event, e.g. "GRB250101A"
OUTPUT_JSON = f"../data/{EVENT.lower()}.json"
OUTPUT_CSV = f"../data/{EVENT.lower()}.csv"

# Optional: override the default free model with a faster paid one
MODEL = "minimax/minimax-m2.5:free"

# Optional: pass the API key directly instead of using env / .env
# API_KEY = "sk-or-v1-..."
API_KEY = None

# ---------------------------------------------------------------------------
# 1. Fetch circulars from the GCN archive
# ---------------------------------------------------------------------------
print(f"Fetching circulars for {EVENT} ...")
circulars = fetch_event_circulars(EVENT)
if not circulars:
    print("No circulars found.")
    sys.exit(1)
print(f"Found {len(circulars)} circular(s).\n")

# ---------------------------------------------------------------------------
# 2. Extract structured information from each circular
# ---------------------------------------------------------------------------
results = []
for c in circulars:
    gcn_number = c["gcn"]
    text = c["text"]
    print(f"Extracting {gcn_number} ...")

    try:
        extraction = extract_circular(
            text,
            model=MODEL,
            api_key=API_KEY,
        )
    except Exception as exc:
        print(f"  ERROR: {exc}")
        continue

    results.append({"gcn": gcn_number, "extraction": extraction.model_dump()})
    print(f"  -> {extraction.summary or '(no summary)'}")

print(f"\nSuccessfully extracted {len(results)} / {len(circulars)} circular(s).\n")

# ---------------------------------------------------------------------------
# 3. Save JSON output
# ---------------------------------------------------------------------------
with open(OUTPUT_JSON, "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, ensure_ascii=False)
print(f"Saved JSON -> {OUTPUT_JSON}")

# ---------------------------------------------------------------------------
# 4. Build and save light-curve CSV
# ---------------------------------------------------------------------------
build_lightcurve_csv(results, OUTPUT_CSV)
print(f"Saved CSV  -> {OUTPUT_CSV}")
