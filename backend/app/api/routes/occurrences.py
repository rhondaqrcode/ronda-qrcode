from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models import Location, Occurrence, OccurrenceStatus, User
from backend.app.schemas.operations import OccurrenceCreate, OccurrenceRead, OccurrenceUpdate

router = APIRouter()


@router.post("", response_model=OccurrenceRead, status_code=status.HTTP_201_CREATED)
def create_occurrence(
    payload: OccurrenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Occurrence:
    if user.employee_id is None:
        raise HTTPException(status_code=422, detail="Usuario nao possui funcionario vinculado.")
    if db.get(Location, payload.location_id) is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado.")

    occurrence = Occurrence(
        title=payload.title,
        description=payload.description,
        location_id=payload.location_id,
        reported_by_id=user.employee_id,
        severity=payload.severity,
    )
    db.add(occurrence)
    db.commit()
    return _get_occurrence_or_404(db, occurrence.id)


@router.get("", response_model=list[OccurrenceRead])
def list_occurrences(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Occurrence]:
    return list(
        db.scalars(
            select(Occurrence)
            .options(selectinload(Occurrence.location), selectinload(Occurrence.reported_by))
            .order_by(Occurrence.created_at.desc())
        ).all()
    )


@router.patch("/{occurrence_id}", response_model=OccurrenceRead)
def update_occurrence(
    occurrence_id: int,
    payload: OccurrenceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Occurrence:
    occurrence = _get_occurrence_or_404(db, occurrence_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(occurrence, field, value)
    occurrence.resolved_at = datetime.now(timezone.utc) if occurrence.status == OccurrenceStatus.resolved else None
    db.commit()
    return _get_occurrence_or_404(db, occurrence_id)


def _get_occurrence_or_404(db: Session, occurrence_id: int) -> Occurrence:
    occurrence = db.scalar(
        select(Occurrence)
        .where(Occurrence.id == occurrence_id)
        .options(selectinload(Occurrence.location), selectinload(Occurrence.reported_by))
    )
    if occurrence is None:
        raise HTTPException(status_code=404, detail="Ocorrencia nao encontrada.")
    return occurrence
