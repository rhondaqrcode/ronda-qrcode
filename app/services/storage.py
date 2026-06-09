from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class SavedUpload:
    original_filename: str
    stored_filename: str
    path: Path
    url: str
    content_type: str
    size_bytes: int


async def save_upload_file(file: UploadFile) -> SavedUpload:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato invalido. Envie JPG, PNG ou WEBP.",
        )

    original_filename = file.filename or "upload"
    suffix = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid4().hex}{suffix}"
    upload_dir = settings.media_root / "photos"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / stored_filename

    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Arquivo excede o limite de 8 MB.",
                )
            output.write(chunk)

    return SavedUpload(
        original_filename=original_filename,
        stored_filename=stored_filename,
        path=destination,
        url=f"/media/photos/{stored_filename}",
        content_type=file.content_type,
        size_bytes=size,
    )
