from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.attendance import AttendanceStatus
from backend.app.models.checklist import ChecklistStatus
from backend.app.models.occurrence import OccurrenceSeverity, OccurrenceStatus
from backend.app.models.photo import PhotoEntityType
from backend.app.schemas.base import ORMModel
from backend.app.schemas.employees import EmployeeRead
from backend.app.schemas.locations import LocationRead


class CheckInCreate(BaseModel):
    location_id: int
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AttendanceRead(ORMModel):
    id: int
    employee_id: int
    location_id: int
    status: AttendanceStatus
    check_in_at: datetime
    check_out_at: datetime | None
    check_in_latitude: float | None
    check_in_longitude: float | None
    notes: str | None


class ChecklistTaskCreate(BaseModel):
    description: str = Field(min_length=2, max_length=180)


class ChecklistCreate(BaseModel):
    location_id: int
    title: str = Field(min_length=2, max_length=160)
    shift: str = Field(min_length=2, max_length=40)
    observations: str | None = Field(default=None, max_length=2000)
    tasks: list[ChecklistTaskCreate] = Field(min_length=1)


class ChecklistTaskUpdate(BaseModel):
    is_done: bool
    observation: str | None = Field(default=None, max_length=1000)


class ChecklistTaskRead(ORMModel):
    id: int
    description: str
    is_done: bool
    observation: str | None
    completed_at: datetime | None


class ChecklistRead(ORMModel):
    id: int
    title: str
    shift: str
    observations: str | None
    status: ChecklistStatus
    employee: EmployeeRead
    location: LocationRead
    tasks: list[ChecklistTaskRead]
    created_at: datetime
    completed_at: datetime | None
    approved_at: datetime | None


class OccurrenceCreate(BaseModel):
    location_id: int
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=5000)
    severity: OccurrenceSeverity = OccurrenceSeverity.medium


class OccurrenceUpdate(BaseModel):
    status: OccurrenceStatus | None = None
    severity: OccurrenceSeverity | None = None
    description: str | None = Field(default=None, min_length=5, max_length=5000)


class OccurrenceRead(ORMModel):
    id: int
    title: str
    description: str
    severity: OccurrenceSeverity
    status: OccurrenceStatus
    location: LocationRead
    reported_by: EmployeeRead
    created_at: datetime
    resolved_at: datetime | None


class PhotoRead(ORMModel):
    id: int
    original_filename: str
    url: str
    content_type: str
    size_bytes: int
    entity_type: PhotoEntityType
    entity_id: int | None
    uploaded_by_id: int
    created_at: datetime
