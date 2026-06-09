from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.employee import Employee

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_employee(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Employee:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_error

    employee = db.scalar(select(Employee).where(Employee.email == subject))
    if employee is None or not employee.is_active:
        raise credentials_error
    return employee


def require_admin(current_employee: Employee = Depends(get_current_employee)) -> Employee:
    if current_employee.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta acao.",
        )
    return current_employee
