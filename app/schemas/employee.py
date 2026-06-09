from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class EmployeeBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(default="employee", max_length=40)
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    password: str = Field(min_length=6, max_length=128)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class EmployeeRead(ORMModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
