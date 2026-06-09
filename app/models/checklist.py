import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ChecklistStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    area: Mapped[str] = mapped_column(String(120), nullable=False)
    shift: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ChecklistStatus] = mapped_column(
        Enum(ChecklistStatus), default=ChecklistStatus.pending, nullable=False
    )
    responsible_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    responsible = relationship("Employee", back_populates="checklists")
    tasks = relationship(
        "ChecklistTask",
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="ChecklistTask.id",
    )


class ChecklistTask(Base):
    __tablename__ = "checklist_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    is_done: Mapped[bool] = mapped_column(default=False, nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    checklist = relationship("Checklist", back_populates="tasks")
