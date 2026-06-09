from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, require_admin, require_supervisor
from backend.app.db.session import get_db
from backend.app.models import Location, User
from backend.app.schemas.locations import LocationCreate, LocationRead

router = APIRouter()


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_supervisor),
) -> Location:
    location = Location(name=payload.name, address=payload.address, city=payload.city, is_active=True)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.get("", response_model=list[LocationRead])
def list_locations(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Location]:
    return list(db.scalars(select(Location).where(Location.is_active.is_(True)).order_by(Location.name)).all())


def get_location_or_404(db: Session, location_id: int) -> Location:
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado.")
    return location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_location(
    location_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado.")

    location.is_active = False
    db.commit()
