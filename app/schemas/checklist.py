from datetime import datetime

from pydantic import BaseModel, Field

from app.models.checklist import ChecklistStatus
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeRead


class ChecklistTaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)


class ChecklistTaskUpdate(BaseModel):
    is_done: bool
    observation: str | None = Field(default=None, max_length=1000)


class ChecklistTaskRead(ORMModel):
    id: int
    title: str
    is_done: bool
    observation: str | None
    completed_at: datetime | None


class ChecklistCreate(BaseModel):
    area: str = Field(min_length=2, max_length=120)
    shift: str = Field(min_length=2, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    tasks: list[ChecklistTaskCreate] = Field(min_length=1)


class ChecklistRead(ORMModel):
    id: int
    area: str
    shift: str
    notes: str | None
    status: ChecklistStatus
    responsible: EmployeeRead
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    tasks: list[ChecklistTaskRead]
