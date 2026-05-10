# GCN Circular LLM Parser (gcn-circular-llm)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight Python package for extracting structured astrophysical information from NASA GCN (Gamma-ray Coordinates Network) circulars using an LLM via [OpenRouter](https://openrouter.ai/).

## Features

- **Fetch circulars** for a given transient event from the NASA GCN archive
- **Extract structured fields** with an LLM:
  - Event coordinates (RA, Dec, system, error)
  - Redshift and host galaxy
  - Classification (e.g. Long GRB, SGRB, Supernova)
  - Flux / magnitude measurements with UTC timestamps and optional MJD
  - Observations and instrument references
  - A one-sentence summary per circular
- **Export light-curve CSV** that aggregates all measurements across circulars with automatic UTC/MJD cross-fill and standardized photometric band names

## Installation

### From PyPI (recommended)

```bash
pip install gcn-circular-llm
```

### From source

```bash
git clone git@github.com:LAujust/gcn_parser.git
cd gcn_parser
pip install .
```

### Requirements

- Python >= 3.10
- An [OpenRouter](https://openrouter.ai/) API key (free to sign up)

## Configuration

### 1. Get an OpenRouter API key

1. Sign up at [openrouter.ai](https://openrouter.ai/)
2. Go to **Keys** and create a new API key
3. Copy the key (starts with `sk-or-v1-...`)

### 2. Provide the key to the package

**Option A: Environment variable (recommended)**

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

**Option B: `.env` file**

Create a `.env` file in your working directory:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

See `.env.example` for the template.

## Usage

### CLI

After installation, the `gcn-parser` command is available globally:

```bash
# Basic extraction (JSON to stdout)
gcn-parser GRB250101A

# Save JSON and generate light-curve CSV
gcn-parser GRB250101A -o output.json --csv lightcurve.csv

# Use a faster or more capable model
gcn-parser GRB250101A -m openai/gpt-4o-mini

# List all options
gcn-parser --help
```

**CLI options**

| Option | Description |
|--------|-------------|
| `event` | Event identifier, e.g. `GRB250101A` or `EP260321a` |
| `-o, --output` | Path to write JSON output (default: stdout) |
| `-c, --csv` | Path to write light-curve CSV |
| `-m, --model` | Override the default OpenRouter model |

You can also run it as a Python module:

```bash
python -m gcn_parser GRB250101A --csv lightcurve.csv
```

### Python API

Use the package programmatically in your own scripts:

```python
from gcn_parser import fetch_event_circulars, extract_circular, build_lightcurve_csv

# Fetch all circulars for an event
circulars = fetch_event_circulars("EP260321a")

# Extract structured info from the first circular
# Pass the API key directly (or omit it to use env / .env)
result = extract_circular(
    circulars[0]["text"],
    api_key="sk-or-v1-...",
    model="openai/gpt-4o-mini",
)
print(result.summary)
print(result.redshift)
print(result.coordinates.ra, result.coordinates.dec)

# Iterate over flux/magnitude measurements
for m in result.flux_magnitude:
    print(f"{m.utc}  {m.band:>3}  {m.value} {m.unit}")
```

## Output

### JSON

Each circular produces an object with the following schema:

```json
[
  {
    "gcn": "GCN 12345",
    "extraction": {
      "event_type": "GRB",
      "coordinates": {
        "ra": "12:34:56.78",
        "dec": "+12:34:56.7",
        "system": "J2000",
        "error_arcsec": 1.2
      },
      "redshift": 0.5,
      "host_galaxy": "Host Galaxy Name",
      "classification": "Long GRB",
      "flux_magnitude": [
        {
          "value": 18.5,
          "band": "r",
          "instrument": "ZTF",
          "utc": "2025-01-01T12:00:00Z",
          "mjd": null,
          "unit": "AB mag",
          "upper_limit": false
        }
      ],
      "observations": ["Swift/XRT follow-up"],
      "references": ["GCN 12344"],
      "confidence": "high",
      "summary": "..."
    }
  }
]
```

### CSV Light-Curve

The `--csv` option flattens all `flux_magnitude` entries across circulars into a single table. Before writing, the exporter performs two clean-up steps automatically:

1. **UTC / MJD cross-fill** — if one timestamp field is missing, it is computed from the other (UTC ↔ MJD conversion using the MJD epoch).
2. **Band standardization** — common aliases are normalized (e.g. `r-band`, `R band`, `VT_R` → `r` or `R`).

| Column | Description |
|--------|-------------|
| `gcn_number` | Source circular number |
| `utc` | Observation time in ISO-8601 UTC |
| `mjd` | Modified Julian Date (optional) |
| `value` | Numeric measurement |
| `unit` | e.g. `mag`, `AB mag`, `uJy`, `mJy/beam` |
| `band` | Standardized photometric band or frequency |
| `instrument` | Telescope or instrument name |
| `upper_limit` | `true` if the measurement is an upper limit |

Rows are sorted chronologically (by UTC, with MJD as fallback).

## Models & Rate Limiting

The default model is `minimax/minimax-m2.5:free` and time lag is `2s` by default, which is free to use but has strict rate limits. If you see `429 Too Many Requests` or empty responses, the package automatically retries with exponential backoff, but processing many circulars can still take 20–30 minutes. Detailed rate limits can be found in https://openrouter.ai/docs/api/reference/limits. If you want to use `free` model (with `:free` in model name), strongly recommend add credit more than $10 to raise the daily rate limit. 

For faster analysis, switch to a low-cost paid model:

```bash
gcn-parser EP260321a -m openai/gpt-4o-mini
```

**Suggested models**

| Model | Speed | Cost | Notes |
|-------|-------|------|-------|
| `minimax/minimax-m2.5:free` | Slow | Free | Rate-limited; good for testing |
| `openai/gpt-5-nano` | Fast | Very low | Best balance of speed, cost, and accuracy |
| `openai/gpt-4o` | Fast | Low | Higher accuracy for complex circulars |
| `qwen/qwen3.5-flash-02-23` | Fast | Very low | Good budget option |

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `429 Too Many Requests` | Free model rate limit | Add `--model openai/gpt-4o-mini` or wait longer between requests |
| `OpenRouter returned an empty response` | Model does not support JSON mode | The package now uses prompt-only JSON; if this persists, switch model |
| `OPENROUTER_API_KEY is not set` | Missing API key | Export the key or create a `.env` file |
| `No circulars found` | Event name typo or GCN has no circulars | Check the exact event name on [gcn.nasa.gov](https://gcn.nasa.gov/) |

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
