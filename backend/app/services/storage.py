from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_IMAGE_SIZE = (800, 800)
JPEG_QUALITY = 70
TARGET_IMAGE_BYTES = 200 * 1024
CLEANUP_DAYS = 30


@dataclass(frozen=True)
class SavedUpload:
    original_filename: str
    stored_filename: str
    path: Path
    url: str
    content_type: str
    size_bytes: int


async def save_upload_file(file: UploadFile) -> SavedUpload:
    original_filename = file.filename or "upload"
    size = 0
    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Arquivo maior que 8 MB.")
        content.extend(chunk)

    destination = save_compressed_image_bytes(bytes(content), "photos")
    stored_filename = destination.name

    return SavedUpload(
        original_filename=original_filename,
        stored_filename=stored_filename,
        path=destination,
        url=f"/uploads/photos/{stored_filename}",
        content_type="image/jpeg",
        size_bytes=destination.stat().st_size,
    )


def save_compressed_upload_file(file: UploadFile, folder: str) -> str:
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo maior que 8 MB.")

    destination = save_compressed_image_bytes(content, folder)
    file.file.seek(0)
    return f"{folder}/{destination.name}".replace("\\", "/")


def save_compressed_image_bytes(content: bytes, folder: str) -> Path:
    destination_dir = settings.uploads_dir / folder
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{uuid4().hex}.jpg"

    try:
        image = Image.open(BytesIO(content))
        image = ImageOps.exif_transpose(image)
        image.thumbnail(MAX_IMAGE_SIZE)
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Envie uma imagem valida em JPG, PNG ou WEBP.",
        ) from exc

    # Salva em JPEG otimizado. Se ainda passar de 200 KB, reduz qualidade e dimensoes.
    quality = JPEG_QUALITY
    while True:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        if buffer.tell() <= TARGET_IMAGE_BYTES or quality <= 45:
            destination.write_bytes(buffer.getvalue())
            return destination
        quality -= 5


def cleanup_old_storage_files(days: int = CLEANUP_DAYS) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    removed = 0
    for root in (settings.uploads_dir, settings.reports_dir):
        removed += _cleanup_old_files(root, cutoff)
    return removed


def _cleanup_old_files(root: Path, cutoff: datetime) -> int:
    if not root.exists():
        return 0

    removed = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified_at <= cutoff:
            os.remove(path)
            removed += 1
    return removed
