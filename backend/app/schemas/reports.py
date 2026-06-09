from datetime import datetime

from pydantic import BaseModel

from backend.app.models.report import ReportType
from backend.app.schemas.base import ORMModel


class DashboardMetrics(BaseModel):
    services_done: int
    active_employees: int
    open_occurrences: int
    absences: int
    photos_uploaded: int


class ProductivityItem(BaseModel):
    employee_id: int
    employee_name: str
    completed_services: int


class OccurrencesByLocation(BaseModel):
    location_id: int
    location_name: str
    total: int


class ReportCreate(BaseModel):
    report_type: ReportType = ReportType.productivity
    title: str = "Relatorio operacional"


class ReportRead(ORMModel):
    id: int
    title: str
    report_type: ReportType
    file_url: str
    created_at: datetime
