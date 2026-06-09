from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models import Attendance, Checklist, Occurrence, PhotoEntityType, UploadedPhoto, User
from backend.app.schemas.operations import PhotoRead
from backend.app.services.storage import cleanup_old_storage_files, save_upload_file

router = APIRouter()


@router.post("", response_model=PhotoRead, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    entity_type: PhotoEntityType = Form(default=PhotoEntityType.general),
    entity_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadedPhoto:
    if user.employee_id is None:
        raise HTTPException(status_code=422, detail="Usuario nao possui funcionario vinculado.")
    _validate_target(db, entity_type, entity_id)
    cleanup_old_storage_files()
    saved = await save_upload_file(file)

    photo = UploadedPhoto(
        original_filename=saved.original_filename,
        stored_filename=saved.stored_filename,
        path=str(saved.path),
        url=saved.url,
        content_type=saved.content_type,
        size_bytes=saved.size_bytes,
        entity_type=entity_type,
        entity_id=entity_id,
        uploaded_by_id=user.employee_id,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("", response_model=list[PhotoRead])
def list_photos(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[UploadedPhoto]:
    return list(db.scalars(select(UploadedPhoto).order_by(UploadedPhoto.created_at.desc())).all())


def _validate_target(db: Session, entity_type: PhotoEntityType, entity_id: int | None) -> None:
    if entity_type == PhotoEntityType.general:
        return
    if entity_id is None:
        raise HTTPException(status_code=422, detail="Informe o ID do registro vinculado.")

    model = {
        PhotoEntityType.checklist: Checklist,
        PhotoEntityType.occurrence: Occurrence,
        PhotoEntityType.attendance: Attendance,
    }[entity_type]
    if db.get(model, entity_id) is None:
        raise HTTPException(status_code=404, detail="Registro vinculado nao encontrado.")
