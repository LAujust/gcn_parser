import csv
import io
from datetime import datetime, timezone

from gcn_parser.csv_export import (
    _parse_utc,
    _utc_to_mjd,
    _mjd_to_utc,
    _standardize_band,
    build_lightcurve_csv,
)


class TestParseUtc:
    def test_iso8601_z(self):
        dt = _parse_utc("2025-01-01T12:00:00Z")
        assert dt == datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_iso8601_offset(self):
        dt = _parse_utc("2025-01-01T12:00:00+00:00")
        assert dt == datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_date_only(self):
        dt = _parse_utc("2025-01-01")
        assert dt == datetime(2025, 1, 1, 0, 0, 0)

    def test_utc_suffix(self):
        dt = _parse_utc("2025-01-01 12:00:00 UTC")
        assert dt == datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_none_and_empty(self):
        assert _parse_utc(None) is None
        assert _parse_utc("") is None


class TestUtcToMjd:
    def test_known_epoch(self):
        dt = datetime(1858, 11, 17, 0, 0, 0, tzinfo=timezone.utc)
        assert _utc_to_mjd(dt) == 0.0

    def test_round_trip(self):
        original = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mjd = _utc_to_mjd(original)
        back = _mjd_to_utc(mjd)
        assert _parse_utc(back) == original


class TestStandardizeBand:
    def test_common_bands(self):
        assert _standardize_band("r") == "r"
        assert _standardize_band("R") == "R"
        assert _standardize_band("r-band") == "r"
        assert _standardize_band("r band") == "r"
        assert _standardize_band("Ks") == "Ks"
        assert _standardize_band("K-short") == "Ks"

    def test_unknown_band(self):
        assert _standardize_band("foo") == "foo"

    def test_none(self):
        assert _standardize_band(None) is None


class TestBuildLightcurveCsv:
    def test_basic_output(self):
        extractions = [
            {
                "gcn": "GCN Circular 44412",
                "extraction": {
                    "flux_magnitude": [
                        {
                            "value": 18.5,
                            "err": 0.3,
                            "band": "r",
                            "instrument": "ZTF",
                            "utc": "2025-01-01T12:00:00Z",
                            "mjd": None,
                            "unit": "AB mag",
                            "upper_limit": False,
                        }
                    ]
                },
            }
        ]
        buf = io.StringIO()
        build_lightcurve_csv(extractions, csv_path="/tmp/test_output.csv")
        with open("/tmp/test_output.csv") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 1
        row = reader[0]
        assert row["value"] == "18.5"
        assert row["err"] == "0.3"
        assert row["band"] == "r"
        assert row["upper_limit"] == "0"

    def test_upper_limit_transform(self):
        extractions = [
            {
                "gcn": "GCN 44413",
                "extraction": {
                    "flux_magnitude": [
                        {
                            "value": 20.0,
                            "err": None,
                            "band": "g",
                            "instrument": "ZTF",
                            "utc": None,
                            "mjd": None,
                            "unit": "mag",
                            "upper_limit": True,
                        }
                    ]
                },
            }
        ]
        build_lightcurve_csv(extractions, csv_path="/tmp/test_ul.csv")
        with open("/tmp/test_ul.csv") as f:
            reader = list(csv.DictReader(f))
        row = reader[0]
        assert row["value"] == "0"
        assert row["err"] == "20.0"
        assert row["upper_limit"] == "1"

    def test_empty_extraction(self):
        extractions = [
            {"gcn": "GCN 44414", "extraction": {"flux_magnitude": []}}
        ]
        build_lightcurve_csv(extractions, csv_path="/tmp/test_empty.csv")
        with open("/tmp/test_empty.csv") as f:
            content = f.read()
        assert "gcn_number" in content
        lines = content.strip().splitlines()
        assert len(lines) == 1  # header only
