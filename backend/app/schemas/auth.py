from datetime import datetime

from pydantic import BaseModel

from backend.app.models.user import UserRole
from backend.app.schemas.base import ORMModel


class UserRead(ORMModel):
    id: int
    email: str
    name: str
    role: UserRole
    is_active: bool
    employee_id: int | None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
