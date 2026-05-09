import argparse
import json
import sys
import time

from .archive import fetch_event_circulars
from .extractor import extract_circular
from .csv_export import build_lightcurve_csv


def _run(event: str, output_path: str | None, csv_path: str | None, model: str | None):
    print(f"Fetching circulars for {event} ...", file=sys.stderr)
    circulars = fetch_event_circulars(event)
    if not circulars:
        print("No circulars found.", file=sys.stderr)
        return

    results = []
    for idx, c in enumerate(circulars):
        gcn_number = c["gcn"]
        text = c["text"]
        print(f"Extracting {gcn_number} ...", file=sys.stderr)
        try:
            extraction = extract_circular(text, model=model)
        except Exception as exc:
            print(f"  ERROR extracting {gcn_number}: {exc}", file=sys.stderr)
            continue
        results.append({"gcn": gcn_number, "extraction": extraction.model_dump()})
        # long delay between requests to respect free-tier rate limits
        if idx < len(circulars) - 1:
            time.sleep(45.0)

    # JSON output
    json_output = json.dumps(results, indent=2, ensure_ascii=False)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(json_output)
        print(f"Wrote JSON to {output_path}", file=sys.stderr)
    else:
        print(json_output)

    # CSV output
    if csv_path:
        build_lightcurve_csv(results, csv_path)
        print(f"Wrote CSV to {csv_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured information from GCN circulars via LLM."
    )
    parser.add_argument("event", help="Event identifier, e.g. GRB250101A")
    parser.add_argument("--output", "-o", help="JSON output file path (default: stdout)")
    parser.add_argument("--csv", "-c", help="CSV output file path for light-curve data")
    parser.add_argument("--model", "-m", default=None, help="OpenRouter model override")
    args = parser.parse_args()

    _run(args.event, args.output, args.csv, args.model)


if __name__ == "__main__":
    main()
