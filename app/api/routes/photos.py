from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_employee
from app.db.session import get_db
from app.models.checklist import Checklist
from app.models.employee import Employee
from app.models.occurrence import Occurrence
from app.models.photo import PhotoEntityType, UploadedPhoto
from app.schemas.photo import PhotoDetail, PhotoRead
from app.services.storage import save_upload_file

router = APIRouter()


@router.post("", response_model=PhotoRead, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    entity_type: PhotoEntityType = Form(default=PhotoEntityType.general),
    entity_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(get_current_employee),
) -> UploadedPhoto:
    _validate_photo_target(db, entity_type, entity_id)
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
        uploaded_by_id=current_employee.id,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("", response_model=list[PhotoRead])
def list_photos(
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[UploadedPhoto]:
    return list(db.scalars(select(UploadedPhoto).order_by(UploadedPhoto.created_at.desc())).all())


@router.get("/{photo_id}", response_model=PhotoDetail)
def read_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> UploadedPhoto:
    photo = db.scalar(
        select(UploadedPhoto)
        .where(UploadedPhoto.id == photo_id)
        .options(selectinload(UploadedPhoto.uploader))
    )
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto nao encontrada.")
    return photo


def _validate_photo_target(
    db: Session, entity_type: PhotoEntityType, entity_id: int | None
) -> None:
    if entity_type == PhotoEntityType.general:
        return
    if entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="entity_id e obrigatorio para fotos vinculadas.",
        )

    if entity_type == PhotoEntityType.checklist and db.get(Checklist, entity_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist nao encontrado.")
    if entity_type == PhotoEntityType.occurrence and db.get(Occurrence, entity_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ocorrencia nao encontrada.")
