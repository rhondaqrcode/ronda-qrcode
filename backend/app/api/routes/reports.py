from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import require_supervisor
from backend.app.db.session import get_db
from backend.app.models import GeneratedReport, ReportType, User
from backend.app.schemas.reports import ReportCreate, ReportRead
from backend.app.services.report_generator import generate_productivity_pdf

router = APIRouter()


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> GeneratedReport:
    if payload.report_type != ReportType.productivity:
        raise HTTPException(status_code=422, detail="MVP gera PDF de produtividade nesta versao.")
    return generate_productivity_pdf(db, payload.title)


@router.get("", response_model=list[ReportRead])
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> list[GeneratedReport]:
    return list(db.scalars(select(GeneratedReport).order_by(GeneratedReport.created_at.desc())).all())
