from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.schemas.base import ORMModel


class LocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    address: str = Field(min_length=2, max_length=255)
    city: str | None = Field(default=None, max_length=80)


class LocationRead(ORMModel):
    id: int
    name: str
    address: str
    city: str | None
    is_active: bool
    created_at: datetime
