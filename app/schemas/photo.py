from datetime import datetime

from app.models.photo import PhotoEntityType
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeRead


class PhotoRead(ORMModel):
    id: int
    original_filename: str
    stored_filename: str
    url: str
    content_type: str
    size_bytes: int
    entity_type: PhotoEntityType
    entity_id: int | None
    uploaded_by_id: int
    created_at: datetime


class PhotoDetail(PhotoRead):
    uploader: EmployeeRead
