from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_employee, require_admin
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate

router = APIRouter()


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: Employee = Depends(require_admin),
) -> Employee:
    existing = db.scalar(select(Employee).where(Employee.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe funcionario com este email.",
        )

    employee = Employee(
        name=payload.name,
        email=str(payload.email),
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    db: Session = Depends(get_db),
    _: Employee = Depends(require_admin),
) -> list[Employee]:
    return list(db.scalars(select(Employee).order_by(Employee.name)).all())


@router.get("/me", response_model=EmployeeRead)
def read_me(current_employee: Employee = Depends(get_current_employee)) -> Employee:
    return current_employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _: Employee = Depends(require_admin),
) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionario nao encontrado.")

    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    for field, value in data.items():
        setattr(employee, field, value)
    if password:
        employee.hashed_password = get_password_hash(password)

    db.commit()
    db.refresh(employee)
    return employee
