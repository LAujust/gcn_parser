from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Any


class Measurement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    value: Optional[float] = None
    magerr: Optional[float] = Field(default=None, alias="err")

    @field_validator("magerr", mode="before")
    @classmethod
    def _coerce_err(cls, v: Any) -> Any:
        """Handle asymmetric errors returned as {'minus': x, 'plus': y}."""
        if isinstance(v, dict):
            minus = v.get("minus")
            plus = v.get("plus")
            if minus is not None and plus is not None:
                try:
                    return (float(minus) + float(plus)) / 2.0
                except (ValueError, TypeError):
                    pass
            # If dict parsing fails, return None rather than crash
            return None
        return v

    band: Optional[str] = None
    instrument: Optional[str] = None
    utc: Optional[str] = None
    mjd: Optional[float] = None
    unit: Optional[str] = None
    upper_limit: Optional[bool] = None

    def model_dump(self, **kwargs):
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)


class Coordinates(BaseModel):
    ra: Optional[str] = None
    dec: Optional[str] = None
    system: Optional[str] = None
    error_arcsec: Optional[float] = None


class CircularExtraction(BaseModel):
    event_type: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    redshift: Optional[float] = None
    host_galaxy: Optional[str] = None
    classification: Optional[str] = None
    flux_magnitude: Optional[list[Measurement]] = []
    observations: Optional[list[str]] = []
    references: Optional[list[str]] = []
    confidence: Optional[str] = None
    summary: Optional[str] = None
