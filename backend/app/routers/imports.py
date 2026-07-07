from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from openpyxl import __version__ as openpyxl_version
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.excel_import import ExcelExtractionError, extract_first_visible_worksheet_rows
from app.import_storage import (
    UploadTooLargeError,
    UploadValidationError,
    default_storage_dir,
    path_for_storage_path,
    remove_stored_upload,
    store_excel_upload,
)
from app.models import ImportBatch, ImportRow, SourceDocument
from app.schemas import ExcelRowExtractionResponse, ExcelUploadResponse, ImportRowRead

router = APIRouter(prefix="/imports", tags=["imports"])


def get_storage_dir() -> Path:
    return default_storage_dir()


def _get_batch_or_404(batch_id: int, db: Session) -> ImportBatch:
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found.")
    if batch.source_document is None:
        raise HTTPException(status_code=404, detail="Source document not found.")
    return batch


def _source_document_path(batch: ImportBatch, storage_dir: Path) -> Path:
    source_document = batch.source_document
    if source_document.file_type.lower() != "xlsx":
        raise HTTPException(
            status_code=400,
            detail="Import batch source document is not an .xlsx file.",
        )

    try:
        workbook_path = path_for_storage_path(storage_dir, source_document.storage_path)
    except UploadValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not workbook_path.is_file():
        raise HTTPException(status_code=404, detail="Stored source document file not found.")

    return workbook_path


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


@router.post(
    "/excel/batches/{batch_id}/extract-rows",
    response_model=ExcelRowExtractionResponse,
)
def extract_excel_rows(
    batch_id: int,
    db: Session = Depends(get_db),
    storage_dir: Path = Depends(get_storage_dir),
):
    batch = _get_batch_or_404(batch_id, db)

    existing_row = (
        db.query(ImportRow.id).filter(ImportRow.import_batch_id == batch.id).first()
    )
    if existing_row is not None:
        raise HTTPException(
            status_code=409,
            detail="Rows have already been extracted for this import batch.",
        )

    workbook_path = _source_document_path(batch, storage_dir)

    try:
        extracted = extract_first_visible_worksheet_rows(workbook_path)
    except ExcelExtractionError as error:
        batch.status = "failed"
        batch.error_message = str(error)
        db.commit()
        raise HTTPException(status_code=400, detail=str(error)) from error

    import_rows = [
        ImportRow(
            import_batch_id=batch.id,
            row_index=row.row_index,
            source_locator_json=row.source_locator_json,
            raw_text=row.raw_text,
            raw_data_json=row.raw_data_json,
            parse_status="parsed",
        )
        for row in extracted.rows
    ]

    db.add_all(import_rows)
    batch.status = "processing"
    batch.parser_name = "openpyxl"
    batch.parser_version = openpyxl_version
    batch.total_rows_detected = len(import_rows)
    batch.error_message = None

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Rows were extracted, but could not be recorded.",
        ) from error

    return {
        "batch_id": batch.id,
        "source_document_id": batch.source_document_id,
        "worksheet_name": extracted.worksheet_name,
        "rows_extracted": len(import_rows),
        "row_preview": [
            {"row_index": row.row_index, "values": row.values}
            for row in extracted.rows[:5]
        ],
    }


@router.get("/batches/{batch_id}/rows", response_model=list[ImportRowRead])
def list_import_rows(batch_id: int, db: Session = Depends(get_db)):
    _get_batch_or_404(batch_id, db)
    return (
        db.query(ImportRow)
        .filter(ImportRow.import_batch_id == batch_id)
        .order_by(ImportRow.row_index.asc(), ImportRow.id.asc())
        .all()
    )
