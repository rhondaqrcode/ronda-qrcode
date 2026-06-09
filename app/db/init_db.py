from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import Base, SessionLocal, engine
from app.models import Checklist, ChecklistTask, Employee, Occurrence, UploadedPhoto


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing_admin = db.scalar(
            select(Employee).where(Employee.email == settings.default_admin_email)
        )
        if existing_admin:
            return

        admin = Employee(
            name="Administrador",
            email=settings.default_admin_email,
            hashed_password=get_password_hash(settings.default_admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
