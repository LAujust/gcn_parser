from gcn_parser.models import Measurement, CircularExtraction


class TestMeasurement:
    def test_alias_serialization(self):
        m = Measurement(value=18.5, magerr=0.3, band="r")
        d = m.model_dump(by_alias=True)
        assert "err" in d
        assert d["err"] == 0.3
        assert "magerr" not in d

    def test_populate_by_name(self):
        m = Measurement.model_validate({"value": 18.5, "err": 0.3, "band": "r"})
        assert m.magerr == 0.3

    def test_asymmetric_err_dict(self):
        m = Measurement.model_validate({"value": 6.3e-10, "err": {"minus": 1.5e-10, "plus": 3.6e-10}})
        assert m.magerr == 2.55e-10

    def test_err_dict_fallback_to_none(self):
        m = Measurement.model_validate({"value": 18.5, "err": {"foo": "bar"}})
        assert m.magerr is None


class TestCircularExtraction:
    def test_nested_alias(self):
        m = Measurement(value=18.5, magerr=0.3, band="r")
        c = CircularExtraction(event_type="GRB", flux_magnitude=[m])
        d = c.model_dump(by_alias=True)
        assert d["flux_magnitude"][0]["err"] == 0.3

    def test_defaults(self):
        c = CircularExtraction()
        assert c.flux_magnitude == []
        assert c.observations == []
        assert c.references == []
