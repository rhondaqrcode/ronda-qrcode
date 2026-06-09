from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.checklist import Checklist, ChecklistStatus, ChecklistTask
from app.models.employee import Employee
from app.schemas.checklist import ChecklistCreate, ChecklistRead, ChecklistTaskUpdate

router = APIRouter()


@router.post("", response_model=ChecklistRead, status_code=status.HTTP_201_CREATED)
def create_checklist(
    payload: ChecklistCreate,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(get_current_employee),
) -> Checklist:
    checklist = Checklist(
        area=payload.area,
        shift=payload.shift,
        notes=payload.notes,
        responsible_id=current_employee.id,
        tasks=[ChecklistTask(title=task.title) for task in payload.tasks],
    )
    db.add(checklist)
    db.commit()
    return _get_checklist_or_404(db, checklist.id)


@router.get("", response_model=list[ChecklistRead])
def list_checklists(
    status_filter: ChecklistStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[Checklist]:
    statement = (
        select(Checklist)
        .options(selectinload(Checklist.tasks), selectinload(Checklist.responsible))
        .order_by(Checklist.created_at.desc())
    )
    if status_filter is not None:
        statement = statement.where(Checklist.status == status_filter)
    return list(db.scalars(statement).all())


@router.get("/{checklist_id}", response_model=ChecklistRead)
def read_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> Checklist:
    return _get_checklist_or_404(db, checklist_id)


@router.patch("/{checklist_id}/tasks/{task_id}", response_model=ChecklistRead)
def update_task(
    checklist_id: int,
    task_id: int,
    payload: ChecklistTaskUpdate,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> Checklist:
    checklist = _get_checklist_or_404(db, checklist_id)
    task = next((item for item in checklist.tasks if item.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa nao encontrada.")

    task.is_done = payload.is_done
    task.observation = payload.observation
    task.completed_at = datetime.now(timezone.utc) if payload.is_done else None
    checklist.status = ChecklistStatus.in_progress
    if checklist.started_at is None:
        checklist.started_at = datetime.now(timezone.utc)
    if all(item.is_done for item in checklist.tasks):
        checklist.status = ChecklistStatus.completed
        checklist.finished_at = datetime.now(timezone.utc)
    else:
        checklist.finished_at = None

    db.commit()
    return _get_checklist_or_404(db, checklist_id)


@router.patch("/{checklist_id}/complete", response_model=ChecklistRead)
def complete_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> Checklist:
    checklist = _get_checklist_or_404(db, checklist_id)
    now = datetime.now(timezone.utc)
    for task in checklist.tasks:
        task.is_done = True
        task.completed_at = task.completed_at or now
    checklist.status = ChecklistStatus.completed
    checklist.started_at = checklist.started_at or now
    checklist.finished_at = now
    db.commit()
    return _get_checklist_or_404(db, checklist_id)


def _get_checklist_or_404(db: Session, checklist_id: int) -> Checklist:
    checklist = db.scalar(
        select(Checklist)
        .where(Checklist.id == checklist_id)
        .options(selectinload(Checklist.tasks), selectinload(Checklist.responsible))
    )
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist nao encontrado.")
    return checklist
