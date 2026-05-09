import json
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from .models import CircularExtraction

load_dotenv()

_DEFAULT_MODEL = "minimax/minimax-m2.5:free"
_BASE_URL = "https://openrouter.ai/api/v1"

_SYSTEM_PROMPT = (
    "You are an expert astronomy research assistant. "
    "Given the raw text of a GCN (Gamma-ray Coordinates Network) circular, "
    "extract the following fields and return them as a single JSON object. "
    "Use 'null' for missing values and empty lists [] for missing arrays. "
    "Be precise with coordinates, redshifts, and flux/magnitude measurements.\n\n"
    "IMPORTANT: Return ONLY the raw JSON object. Do not wrap it in markdown code blocks or add any extra text.\n\n"
    "JSON schema:\n"
    "- event_type: string or null (e.g. 'GRB', 'SGRB', 'AGN flare', 'Supernova')\n"
    "- coordinates: object with ra (string), dec (string), system (string, e.g. 'J2000'), error_arcsec (number or null)\n"
    "- redshift: number or null\n"
    "- host_galaxy: string or null\n"
    "- classification: string or null\n"
    "- flux_magnitude: list of objects, each with:\n"
    "    value (number or null), band (string or null), instrument (string or null),\n"
    "    utc (string or null, ISO-8601 UTC datetime, e.g. '2025-01-01T12:00:00Z'),\n"
    "    mjd (number or null, Modified Julian Date),\n"
    "    unit (string or null, e.g. 'mag', 'AB mag', 'erg cm^-2 s^-1'), upper_limit (boolean or null)\n"
    "- observations: list of strings\n"
    "- references: list of strings\n"
    "- confidence: string ('high', 'medium', 'low')\n"
    "- summary: string (one-sentence summary of the circular)\n"
)


def _api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY environment variable is not set. "
            "Export it or add it to a .env file."
        )
    return key


def _extract_json(raw: str) -> dict:
    """Extract a JSON object from raw text, stripping markdown fences if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        # Drop opening fence line
        lines = raw.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return json.loads(raw)


def extract_circular(
    text: str,
    model: Optional[str] = None,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> CircularExtraction:
    """Extract structured information from a single GCN circular text.

    Retries on 429 (rate limit) and 5xx server errors with exponential backoff.

    Args:
        text: Raw text content of the circular.
        model: OpenRouter model identifier. Defaults to ``minimax/minimax-m2.5:free``.
        max_retries: Maximum number of retries.
        base_delay: Initial delay between retries in seconds.

    Returns:
        Parsed ``CircularExtraction`` object.

    Raises:
        RuntimeError: On API or parsing failures after retries are exhausted.
    """
    model = model or _DEFAULT_MODEL
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.0,
    }

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                f"{_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else 0
            if status == 429 or status >= 500:
                last_exc = exc
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
            raise RuntimeError(f"OpenRouter API call failed: {exc}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenRouter API call failed: {exc}") from exc

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned no choices.")

        raw = choices[0].get("message", {}).get("content", "")
        if not raw:
            raise RuntimeError("OpenRouter returned an empty response.")

        try:
            parsed = _extract_json(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"OpenRouter returned invalid JSON: {exc}") from exc

        return CircularExtraction.model_validate(parsed)

    raise RuntimeError(
        f"OpenRouter API call failed after {max_retries} retries: {last_exc}"
    ) from last_exc
