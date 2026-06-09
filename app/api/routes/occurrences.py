from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.employee import Employee
from app.models.occurrence import Occurrence, OccurrenceStatus
from app.schemas.occurrence import OccurrenceCreate, OccurrenceRead, OccurrenceUpdate

router = APIRouter()


@router.post("", response_model=OccurrenceRead, status_code=status.HTTP_201_CREATED)
def create_occurrence(
    payload: OccurrenceCreate,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(get_current_employee),
) -> Occurrence:
    occurrence = Occurrence(
        title=payload.title,
        description=payload.description,
        location=payload.location,
        severity=payload.severity,
        reporter_id=current_employee.id,
    )
    db.add(occurrence)
    db.commit()
    return _get_occurrence_or_404(db, occurrence.id)


@router.get("", response_model=list[OccurrenceRead])
def list_occurrences(
    status_filter: OccurrenceStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[Occurrence]:
    statement = (
        select(Occurrence)
        .options(selectinload(Occurrence.reporter))
        .order_by(Occurrence.created_at.desc())
    )
    if status_filter is not None:
        statement = statement.where(Occurrence.status == status_filter)
    return list(db.scalars(statement).all())


@router.get("/{occurrence_id}", response_model=OccurrenceRead)
def read_occurrence(
    occurrence_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> Occurrence:
    return _get_occurrence_or_404(db, occurrence_id)


@router.patch("/{occurrence_id}", response_model=OccurrenceRead)
def update_occurrence(
    occurrence_id: int,
    payload: OccurrenceUpdate,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> Occurrence:
    occurrence = _get_occurrence_or_404(db, occurrence_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(occurrence, field, value)

    if occurrence.status == OccurrenceStatus.resolved and occurrence.resolved_at is None:
        occurrence.resolved_at = datetime.now(timezone.utc)
    elif occurrence.status != OccurrenceStatus.resolved:
        occurrence.resolved_at = None

    db.commit()
    return _get_occurrence_or_404(db, occurrence_id)


def _get_occurrence_or_404(db: Session, occurrence_id: int) -> Occurrence:
    occurrence = db.scalar(
        select(Occurrence)
        .where(Occurrence.id == occurrence_id)
        .options(selectinload(Occurrence.reporter))
    )
    if occurrence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ocorrencia nao encontrada.")
    return occurrence
