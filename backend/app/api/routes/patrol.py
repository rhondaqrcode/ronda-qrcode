from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_current_user, require_admin, require_supervisor
from backend.app.db.session import get_db
from backend.app.models import Location, PatrolPoint, PatrolScan, User
from backend.app.schemas.patrol import PatrolPointCreate, PatrolPointRead, PatrolScanCreate, PatrolScanRead

router = APIRouter()


@router.post("/points", response_model=PatrolPointRead, status_code=status.HTTP_201_CREATED)
def create_patrol_point(
    payload: PatrolPointCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> PatrolPoint:
    if db.get(Location, payload.location_id) is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado.")

    qr_code = (payload.qr_code or f"RONDA-{uuid4().hex[:10]}").strip().upper()
    existing = db.scalar(select(PatrolPoint).where(PatrolPoint.qr_code == qr_code))
    if existing:
        raise HTTPException(status_code=409, detail="Ja existe ponto com este codigo QR.")

    point = PatrolPoint(
        location_id=payload.location_id,
        name=payload.name,
        qr_code=qr_code,
        instructions=payload.instructions,
        is_active=True,
    )
    db.add(point)
    db.commit()
    return _get_point_or_404(db, point.id)


@router.get("/points", response_model=list[PatrolPointRead])
def list_patrol_points(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> list[PatrolPoint]:
    return list(
        db.scalars(
            select(PatrolPoint)
            .where(PatrolPoint.is_active.is_(True))
            .options(selectinload(PatrolPoint.location))
            .order_by(PatrolPoint.name)
        ).all()
    )


@router.delete("/points/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_patrol_point(
    point_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    point = db.get(PatrolPoint, point_id)
    if point is None:
        raise HTTPException(status_code=404, detail="Ponto de ronda nao encontrado.")
    point.is_active = False
    db.commit()


@router.post("/scans", response_model=PatrolScanRead, status_code=status.HTTP_201_CREATED)
def create_patrol_scan(
    payload: PatrolScanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PatrolScan:
    if user.employee_id is None:
        raise HTTPException(status_code=422, detail="Usuario nao possui funcionario vinculado.")

    qr_code = payload.qr_code.strip().upper()
    point = db.scalar(
        select(PatrolPoint)
        .where(PatrolPoint.qr_code == qr_code, PatrolPoint.is_active.is_(True))
        .options(selectinload(PatrolPoint.location))
    )
    if point is None:
        raise HTTPException(status_code=404, detail="QR Code de ronda nao encontrado.")

    scan = PatrolScan(
        point_id=point.id,
        employee_id=user.employee_id,
        qr_code=qr_code,
        notes=payload.notes,
    )
    db.add(scan)
    db.commit()
    return _get_scan_or_404(db, scan.id)


@router.get("/scans", response_model=list[PatrolScanRead])
def list_patrol_scans(
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> list[PatrolScan]:
    return list(
        db.scalars(
            select(PatrolScan)
            .options(
                selectinload(PatrolScan.employee),
                selectinload(PatrolScan.point).selectinload(PatrolPoint.location),
            )
            .order_by(PatrolScan.scanned_at.desc())
        ).all()
    )


def _get_point_or_404(db: Session, point_id: int) -> PatrolPoint:
    point = db.scalar(
        select(PatrolPoint)
        .where(PatrolPoint.id == point_id)
        .options(selectinload(PatrolPoint.location))
    )
    if point is None:
        raise HTTPException(status_code=404, detail="Ponto de ronda nao encontrado.")
    return point


def _get_scan_or_404(db: Session, scan_id: int) -> PatrolScan:
    scan = db.scalar(
        select(PatrolScan)
        .where(PatrolScan.id == scan_id)
        .options(
            selectinload(PatrolScan.employee),
            selectinload(PatrolScan.point).selectinload(PatrolPoint.location),
        )
    )
    if scan is None:
        raise HTTPException(status_code=404, detail="Leitura de ronda nao encontrada.")
    return scan
