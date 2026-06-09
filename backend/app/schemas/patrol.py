from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.base import ORMModel
from backend.app.schemas.employees import EmployeeRead
from backend.app.schemas.locations import LocationRead


class PatrolPointCreate(BaseModel):
    location_id: int
    name: str = Field(min_length=2, max_length=140)
    qr_code: str | None = Field(default=None, min_length=3, max_length=120)
    instructions: str | None = Field(default=None, max_length=1000)


class PatrolPointRead(ORMModel):
    id: int
    location_id: int
    name: str
    qr_code: str
    instructions: str | None
    is_active: bool
    created_at: datetime
    location: LocationRead


class PatrolScanCreate(BaseModel):
    qr_code: str = Field(min_length=3, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class PatrolScanRead(ORMModel):
    id: int
    qr_code: str
    notes: str | None
    scanned_at: datetime
    point: PatrolPointRead
    employee: EmployeeRead
