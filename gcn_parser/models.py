from pydantic import BaseModel
from typing import Optional


class Measurement(BaseModel):
    value: Optional[float] = None
    magerr: Optional[float] = None
    band: Optional[str] = None
    instrument: Optional[str] = None
    utc: Optional[str] = None
    mjd: Optional[float] = None
    unit: Optional[str] = None
    upper_limit: Optional[bool] = None


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
