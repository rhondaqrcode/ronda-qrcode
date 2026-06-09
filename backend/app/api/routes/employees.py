from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import require_admin, require_supervisor
from backend.app.core.security import get_password_hash
from backend.app.db.session import get_db
from backend.app.models import Employee, User
from backend.app.schemas.employees import EmployeeCreate, EmployeeRead, EmployeeUpdate, PasswordReset

router = APIRouter()


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Employee:
    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise HTTPException(status_code=409, detail="Ja existe usuario com este email.")

    employee = Employee(
        name=payload.name,
        phone=payload.phone,
        position=payload.position,
        is_active=True,
    )
    user = User(
        email=email,
        name=payload.name,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
        employee=employee,
    )
    db.add(user)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> list[Employee]:
    statement = select(Employee).options(selectinload(Employee.user)).order_by(Employee.name)
    if not include_inactive:
        statement = statement.where(Employee.is_active.is_(True))
    return list(
        db.scalars(statement).all()
    )


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Employee:
    employee = db.scalar(select(Employee).where(Employee.id == employee_id).options(selectinload(Employee.user)))
    if employee is None or employee.user is None:
        raise HTTPException(status_code=404, detail="Funcionario nao encontrado.")
    if current_user.employee_id == employee_id and not payload.is_active:
        raise HTTPException(status_code=422, detail="Voce nao pode desativar seu proprio usuario.")

    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(func.lower(User.email) == email, User.id != employee.user.id))
    if existing:
        raise HTTPException(status_code=409, detail="Ja existe usuario com este email.")

    employee.name = payload.name
    employee.phone = payload.phone
    employee.position = payload.position
    employee.is_active = payload.is_active
    employee.user.name = payload.name
    employee.user.email = email
    employee.user.role = payload.role
    employee.user.is_active = payload.is_active
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}/status", response_model=EmployeeRead)
def set_employee_status(
    employee_id: int,
    active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Employee:
    employee = db.scalar(select(Employee).where(Employee.id == employee_id).options(selectinload(Employee.user)))
    if employee is None:
        raise HTTPException(status_code=404, detail="Funcionario nao encontrado.")
    if current_user.employee_id == employee_id and not active:
        raise HTTPException(status_code=422, detail="Voce nao pode desativar seu proprio usuario.")
    employee.is_active = active
    if employee.user:
        employee.user.is_active = active
    db.commit()
    db.refresh(employee)
    return employee


@router.post("/{employee_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_employee_password(
    employee_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    employee = db.scalar(select(Employee).where(Employee.id == employee_id).options(selectinload(Employee.user)))
    if employee is None or employee.user is None:
        raise HTTPException(status_code=404, detail="Funcionario nao encontrado.")
    employee.user.hashed_password = get_password_hash(payload.password)
    db.commit()


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Funcionario nao encontrado.")
    if current_user.employee_id == employee_id:
        raise HTTPException(status_code=422, detail="Voce nao pode desativar seu proprio usuario.")

    employee.is_active = False
    users = db.scalars(select(User).where(User.employee_id == employee_id)).all()
    for user in users:
        user.is_active = False
    db.commit()
