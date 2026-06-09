from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.models.user import UserRole
from backend.app.schemas.base import ORMModel


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = Field(default=None, max_length=40)
    position: str = Field(default="Auxiliar de limpeza", max_length=80)
    role: UserRole = UserRole.employee


class EmployeeUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    position: str = Field(default="Auxiliar de limpeza", max_length=80)
    role: UserRole = UserRole.employee
    is_active: bool = True


class PasswordReset(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class EmployeeRead(ORMModel):
    id: int
    name: str
    phone: str | None
    position: str
    is_active: bool
    created_at: datetime
    user_email: str | None = None
    user_role: str | None = None
