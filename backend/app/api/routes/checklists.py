from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_current_user, require_supervisor
from backend.app.db.session import get_db
from backend.app.models import Checklist, ChecklistStatus, ChecklistTask, Location, User
from backend.app.schemas.operations import ChecklistCreate, ChecklistRead, ChecklistTaskUpdate

router = APIRouter()


@router.post("", response_model=ChecklistRead, status_code=status.HTTP_201_CREATED)
def create_checklist(
    payload: ChecklistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Checklist:
    if user.employee_id is None:
        raise HTTPException(status_code=422, detail="Usuario nao possui funcionario vinculado.")
    if db.get(Location, payload.location_id) is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado.")

    checklist = Checklist(
        employee_id=user.employee_id,
        location_id=payload.location_id,
        title=payload.title,
        shift=payload.shift,
        observations=payload.observations,
        tasks=[ChecklistTask(description=task.description) for task in payload.tasks],
    )
    db.add(checklist)
    db.commit()
    return _get_checklist_or_404(db, checklist.id)


@router.get("", response_model=list[ChecklistRead])
def list_checklists(
    status_filter: ChecklistStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Checklist]:
    statement = (
        select(Checklist)
        .options(
            selectinload(Checklist.tasks),
            selectinload(Checklist.employee),
            selectinload(Checklist.location),
        )
        .order_by(Checklist.created_at.desc())
    )
    if status_filter:
        statement = statement.where(Checklist.status == status_filter)
    return list(db.scalars(statement).all())


@router.patch("/{checklist_id}/tasks/{task_id}", response_model=ChecklistRead)
def update_task(
    checklist_id: int,
    task_id: int,
    payload: ChecklistTaskUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Checklist:
    checklist = _get_checklist_or_404(db, checklist_id)
    task = next((item for item in checklist.tasks if item.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa nao encontrada.")

    task.is_done = payload.is_done
    task.observation = payload.observation
    task.completed_at = datetime.now(timezone.utc) if payload.is_done else None
    checklist.status = ChecklistStatus.completed if all(item.is_done for item in checklist.tasks) else ChecklistStatus.in_progress
    checklist.completed_at = datetime.now(timezone.utc) if checklist.status == ChecklistStatus.completed else None
    db.commit()
    return _get_checklist_or_404(db, checklist_id)


@router.patch("/{checklist_id}/approve", response_model=ChecklistRead)
def approve_checklist(
    checklist_id: int,
    approved: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_supervisor),
) -> Checklist:
    checklist = _get_checklist_or_404(db, checklist_id)
    checklist.status = ChecklistStatus.approved if approved else ChecklistStatus.rejected
    checklist.approved_by_id = user.id
    checklist.approved_at = datetime.now(timezone.utc)
    db.commit()
    return _get_checklist_or_404(db, checklist_id)


def _get_checklist_or_404(db: Session, checklist_id: int) -> Checklist:
    checklist = db.scalar(
        select(Checklist)
        .where(Checklist.id == checklist_id)
        .options(
            selectinload(Checklist.tasks),
            selectinload(Checklist.employee),
            selectinload(Checklist.location),
        )
    )
    if checklist is None:
        raise HTTPException(status_code=404, detail="Checklist nao encontrado.")
    return checklist
