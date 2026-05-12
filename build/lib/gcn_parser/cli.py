import argparse
import json
import sys
import time

from .archive import fetch_event_circulars
from .extractor import extract_circular, extract_circulars_batch
from .csv_export import build_lightcurve_csv
from .models import CircularExtraction


def _split_into_batches(
    circulars: list[dict], max_chars: int = 20000, max_per_batch: int = 5
) -> list[list[dict]]:
    """Split circulars into batches respecting character and count limits."""
    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_chars = 0

    for c in circulars:
        text_len = len(c["text"])
        oversized = text_len > max_chars
        count_full = len(current_batch) >= max_per_batch
        chars_full = current_chars + text_len > max_chars and current_batch

        if oversized:
            if current_batch:
                batches.append(current_batch)
            batches.append([c])
            current_batch = []
            current_chars = 0
        elif count_full or chars_full:
            batches.append(current_batch)
            current_batch = [c]
            current_chars = text_len
        else:
            current_batch.append(c)
            current_chars += text_len

    if current_batch:
        batches.append(current_batch)
    return batches


def _run(event: str, output_path: str | None, csv_path: str | None, model: str | None):
    print(f"Fetching circulars for {event} ...", file=sys.stderr)
    circulars = fetch_event_circulars(event)
    if not circulars:
        print("No circulars found.", file=sys.stderr)
        return

    batches = _split_into_batches(circulars, max_chars=20000, max_per_batch=5)
    results = []
    failed_circulars: list[dict] = []

    for batch_idx, batch in enumerate(batches):
        gcn_numbers = [c["gcn"] for c in batch]
        print(
            f"Extracting batch {batch_idx + 1}/{len(batches)} ({', '.join(gcn_numbers)}) ...",
            file=sys.stderr,
        )
        try:
            extractions = extract_circulars_batch(batch, model=model)
            for c, extraction in zip(batch, extractions):
                returned_gcn = extraction.get("gcn_number", c["gcn"])
                if returned_gcn != c["gcn"]:
                    print(
                        f"  WARNING: gcn_number mismatch ({returned_gcn} vs {c['gcn']}), using input order.",
                        file=sys.stderr,
                    )
                extraction_copy = {k: v for k, v in extraction.items() if k != "gcn_number"}
                validated = CircularExtraction.model_validate(extraction_copy)
                results.append({"gcn": c["gcn"], "extraction": validated.model_dump(by_alias=True)})
        except Exception as exc:
            print(f"  Batch failed: {exc}. Falling back to individual extraction.", file=sys.stderr)
            for c in batch:
                gcn_number = c["gcn"]
                text = c["text"]
                print(f"  Extracting {gcn_number} individually ...", file=sys.stderr)
                try:
                    extraction = extract_circular(text, model=model)
                    results.append({"gcn": gcn_number, "extraction": extraction.model_dump(by_alias=True)})
                except Exception as exc2:
                    print(f"    ERROR extracting {gcn_number}: {exc2}", file=sys.stderr)
                    failed_circulars.append(c)
                    continue
                # short delay between individual fallback extractions
                if c != batch[-1]:
                    time.sleep(5.0)

        # short delay between batches to respect free-tier rate limits
        if batch_idx < len(batches) - 1:
            time.sleep(5.0)

    # Final retry pass for any circulars that failed both batch and individual extraction
    if failed_circulars:
        print(
            f"\nRe-analyzing {len(failed_circulars)} failed circular(s) ...",
            file=sys.stderr,
        )
        still_failed: list[str] = []
        for idx, c in enumerate(failed_circulars):
            gcn_number = c["gcn"]
            print(f"  Final retry {gcn_number} ...", file=sys.stderr)
            try:
                extraction = extract_circular(c["text"], model=model)
                results.append({"gcn": gcn_number, "extraction": extraction.model_dump(by_alias=True)})
            except Exception as exc:
                print(f"    FAILED again: {exc}", file=sys.stderr)
                still_failed.append(gcn_number)
            if idx < len(failed_circulars) - 1:
                time.sleep(10.0)

        if still_failed:
            print(
                f"\nWarning: {len(still_failed)} circular(s) could not be extracted after all retries: {', '.join(still_failed)}",
                file=sys.stderr,
            )

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
