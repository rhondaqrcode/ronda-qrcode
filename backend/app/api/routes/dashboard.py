from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import require_supervisor
from backend.app.db.session import get_db
from backend.app.models import (
    Attendance,
    AttendanceStatus,
    Checklist,
    ChecklistStatus,
    Employee,
    Location,
    Occurrence,
    OccurrenceStatus,
    UploadedPhoto,
    User,
)
from backend.app.schemas.reports import DashboardMetrics, OccurrencesByLocation, ProductivityItem

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> DashboardMetrics:
    services_done = db.scalar(select(func.count()).select_from(Checklist).where(Checklist.status.in_([ChecklistStatus.completed, ChecklistStatus.approved]))) or 0
    active_employees = db.scalar(select(func.count()).select_from(Employee).where(Employee.is_active.is_(True))) or 0
    open_occurrences = db.scalar(select(func.count()).select_from(Occurrence).where(Occurrence.status != OccurrenceStatus.resolved)) or 0
    absences = db.scalar(select(func.count()).select_from(Attendance).where(Attendance.status == AttendanceStatus.absent)) or 0
    photos_uploaded = db.scalar(select(func.count()).select_from(UploadedPhoto)) or 0
    return DashboardMetrics(
        services_done=services_done,
        active_employees=active_employees,
        open_occurrences=open_occurrences,
        absences=absences,
        photos_uploaded=photos_uploaded,
    )


@router.get("/productivity", response_model=list[ProductivityItem])
def productivity(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> list[ProductivityItem]:
    rows = db.execute(
        select(Employee.id, Employee.name, func.count(Checklist.id))
        .join(Checklist, Checklist.employee_id == Employee.id, isouter=True)
        .group_by(Employee.id)
        .order_by(func.count(Checklist.id).desc())
    ).all()
    return [
        ProductivityItem(employee_id=row[0], employee_name=row[1], completed_services=row[2])
        for row in rows
    ]


@router.get("/occurrences-by-location", response_model=list[OccurrencesByLocation])
def occurrences_by_location(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> list[OccurrencesByLocation]:
    rows = db.execute(
        select(Location.id, Location.name, func.count(Occurrence.id))
        .join(Occurrence, Occurrence.location_id == Location.id, isouter=True)
        .group_by(Location.id)
        .order_by(func.count(Occurrence.id).desc())
    ).all()
    return [
        OccurrencesByLocation(location_id=row[0], location_name=row[1], total=row[2])
        for row in rows
    ]
