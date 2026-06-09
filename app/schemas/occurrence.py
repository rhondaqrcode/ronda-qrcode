from datetime import datetime

from pydantic import BaseModel, Field

from app.models.occurrence import OccurrenceSeverity, OccurrenceStatus
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeRead


class OccurrenceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=5000)
    location: str = Field(min_length=2, max_length=160)
    severity: OccurrenceSeverity = OccurrenceSeverity.medium


class OccurrenceUpdate(BaseModel):
    status: OccurrenceStatus | None = None
    severity: OccurrenceSeverity | None = None
    description: str | None = Field(default=None, min_length=5, max_length=5000)


class OccurrenceRead(ORMModel):
    id: int
    title: str
    description: str
    location: str
    severity: OccurrenceSeverity
    status: OccurrenceStatus
    reporter: EmployeeRead
    created_at: datetime
    resolved_at: datetime | None
