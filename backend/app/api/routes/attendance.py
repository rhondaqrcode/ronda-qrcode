from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, require_supervisor
from backend.app.db.session import get_db
from backend.app.models import Attendance, AttendanceStatus, Location, User
from backend.app.schemas.operations import AttendanceRead, CheckInCreate

router = APIRouter()


@router.post("/check-in", response_model=AttendanceRead, status_code=status.HTTP_201_CREATED)
def check_in(
    payload: CheckInCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Attendance:
    if user.employee_id is None:
        raise HTTPException(status_code=422, detail="Usuario nao possui funcionario vinculado.")
    if db.get(Location, payload.location_id) is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado.")

    attendance = Attendance(
        employee_id=user.employee_id,
        location_id=payload.location_id,
        check_in_latitude=payload.latitude,
        check_in_longitude=payload.longitude,
        notes=payload.notes,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.patch("/{attendance_id}/check-out", response_model=AttendanceRead)
def check_out(
    attendance_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Attendance:
    attendance = db.get(Attendance, attendance_id)
    if attendance is None:
        raise HTTPException(status_code=404, detail="Registro de presenca nao encontrado.")
    if user.role.value == "employee" and attendance.employee_id != user.employee_id:
        raise HTTPException(status_code=403, detail="Registro pertence a outro funcionario.")

    check_out_at = datetime.now(timezone.utc)
    open_records = db.scalars(
        select(Attendance).where(
            Attendance.employee_id == attendance.employee_id,
            Attendance.status == AttendanceStatus.checked_in,
        )
    ).all()
    for record in open_records:
        record.status = AttendanceStatus.checked_out
        record.check_out_at = check_out_at

    db.commit()
    db.refresh(attendance)
    return attendance


@router.get("/current", response_model=AttendanceRead | None)
def current_attendance(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Attendance | None:
    if user.employee_id is None:
        raise HTTPException(status_code=422, detail="Usuario nao possui funcionario vinculado.")

    return db.scalar(
        select(Attendance)
        .where(
            Attendance.employee_id == user.employee_id,
            Attendance.status == AttendanceStatus.checked_in,
        )
        .order_by(Attendance.check_in_at.desc())
    )


@router.get("", response_model=list[AttendanceRead])
def list_attendance(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> list[Attendance]:
    return list(db.scalars(select(Attendance).order_by(Attendance.check_in_at.desc())).all())
