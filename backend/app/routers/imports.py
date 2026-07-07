from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.import_storage import (
    UploadTooLargeError,
    UploadValidationError,
    default_storage_dir,
    remove_stored_upload,
    store_excel_upload,
)
from app.models import ImportBatch, SourceDocument
from app.schemas import ExcelUploadResponse

router = APIRouter(prefix="/imports", tags=["imports"])


def get_storage_dir() -> Path:
    return default_storage_dir()


@router.post(
    "/excel/upload",
    response_model=ExcelUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_excel(
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    storage_dir: Path = Depends(get_storage_dir),
):
    if file is None:
        raise HTTPException(status_code=400, detail="An uploaded .xlsx file is required.")

    try:
        stored_upload = await store_excel_upload(file, storage_dir)
    except UploadTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except UploadValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    source_document = SourceDocument(
        original_filename=stored_upload.original_filename,
        storage_path=stored_upload.storage_path,
        file_type=stored_upload.file_type,
        mime_type=stored_upload.mime_type,
        size_bytes=stored_upload.size_bytes,
        sha256_checksum=stored_upload.sha256_checksum,
    )
    import_batch = ImportBatch(source_document=source_document, status="pending")

    db.add(source_document)
    db.add(import_batch)

    try:
        db.commit()
        db.refresh(source_document)
        db.refresh(import_batch)
    except SQLAlchemyError as error:
        db.rollback()
        remove_stored_upload(storage_dir, stored_upload.storage_path)
        raise HTTPException(
            status_code=500,
            detail="Uploaded file was saved, but metadata could not be recorded.",
        ) from error

    return {"source_document": source_document, "import_batch": import_batch}
