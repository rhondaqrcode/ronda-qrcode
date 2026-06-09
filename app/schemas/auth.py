from pydantic import BaseModel

from app.schemas.employee import EmployeeRead


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee: EmployeeRead
