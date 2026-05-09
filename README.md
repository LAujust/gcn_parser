# GCN Circular Parser

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Extract structured astrophysical information from NASA GCN circulars using an LLM via [OpenRouter](https://openrouter.ai/).

## Features

- Fetch all circulars for a given event from the GCN archive
- Extract structured fields with an LLM: coordinates, redshift, host galaxy, classification, flux/magnitude measurements, observations, references, and a one-sentence summary
- Export magnitude/flux measurements across all circulars into a single time-sorted CSV light-curve table

## Installation

```bash
git clone git@github.com:LAujust/gcn_parser.git
cd gcn_parser
pip install -r requirements.txt
```

## Configuration

Set your OpenRouter API key:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```

Or create a `.env` file (see `.env.example`).

## Usage

Run the CLI for an event identifier:

```bash
# JSON to stdout
python -m gcn_parser GRB250101A

# Save JSON and CSV light-curve
python -m gcn_parser GRB250101A -o output.json --csv lightcurve.csv

# Use a different model
python -m gcn_parser GRB250101A -m openai/gpt-4o
```

## Output

### JSON
Each circular is an object containing the GCN number and the extracted fields.

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
          "date": "2025-01-01T12:00:00",
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
The `--csv` option aggregates all `flux_magnitude` measurements across circulars into a single table:

| Column | Description |
|--------|-------------|
| `gcn_number` | Source circular |
| `date` | Observation date/time or MJD |
| `value` | Numeric measurement |
| `unit` | e.g. `mag`, `AB mag`, `erg cm^-2 s^-1` |
| `band` | Photometric band |
| `instrument` | Telescope or instrument |
| `upper_limit` | `true` if upper limit |

Rows are sorted by date.

## Project Structure

```
gcn_parser/
├── archive.py       # Fetch circulars from GCN archive
├── models.py        # Pydantic schema for structured extraction
├── extractor.py     # OpenRouter LLM client and prompt
├── csv_export.py    # Flatten measurements to CSV
├── cli.py           # argparse CLI entry point
└── __main__.py      # Enables `python -m gcn_parser`
```

## Default Model

`minimax/minimax-m2.5:free` via OpenRouter.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
