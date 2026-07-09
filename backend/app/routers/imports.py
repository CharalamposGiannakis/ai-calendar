from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from openpyxl import __version__ as openpyxl_version
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.excel_candidates import (
    CandidateGenerationError,
    ImportRowInput,
    generate_candidate_drafts,
)
from app.excel_import import ExcelExtractionError, extract_first_visible_worksheet_rows
from app.import_storage import (
    UploadTooLargeError,
    UploadValidationError,
    default_storage_dir,
    path_for_storage_path,
    remove_stored_upload,
    store_excel_upload,
)
from app.models import CandidateEvent, Category, ImportBatch, ImportRow, SourceDocument
from app.schemas import (
    CandidateEventRead,
    ExcelCandidateGenerationResponse,
    ExcelRowExtractionResponse,
    ExcelUploadResponse,
    ImportRowRead,
)

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


def _candidate_payload(candidate: CandidateEvent) -> dict:
    return {
        "id": candidate.id,
        "import_batch_id": candidate.import_batch_id,
        "import_row_id": candidate.import_row_id,
        "source_row_index": candidate.import_row.row_index,
        "title": candidate.title,
        "description": candidate.description,
        "all_day": candidate.all_day,
        "start_datetime": candidate.start_datetime,
        "end_datetime": candidate.end_datetime,
        "start_date": candidate.start_date,
        "end_date": candidate.end_date,
        "timezone_name": candidate.timezone_name,
        "location": candidate.location,
        "category_id": candidate.category_id,
        "review_status": candidate.review_status,
        "was_edited": candidate.was_edited,
        "review_notes": candidate.review_notes,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
    }


def _candidate_preview(candidate: CandidateEvent) -> dict:
    return {
        "import_row_id": candidate.import_row_id,
        "source_row_index": candidate.import_row.row_index,
        "title": candidate.title,
        "all_day": candidate.all_day,
        "start_datetime": candidate.start_datetime,
        "end_datetime": candidate.end_datetime,
        "start_date": candidate.start_date,
        "end_date": candidate.end_date,
        "timezone_name": candidate.timezone_name,
        "category_id": candidate.category_id,
    }


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


@router.post(
    "/excel/batches/{batch_id}/generate-candidates",
    response_model=ExcelCandidateGenerationResponse,
)
def generate_excel_candidates(batch_id: int, db: Session = Depends(get_db)):
    batch = _get_batch_or_404(batch_id, db)

    existing_candidate = (
        db.query(CandidateEvent.id)
        .filter(CandidateEvent.import_batch_id == batch.id)
        .first()
    )
    if existing_candidate is not None:
        raise HTTPException(
            status_code=409,
            detail="Candidate events have already been generated for this import batch.",
        )

    import_rows = (
        db.query(ImportRow)
        .filter(ImportRow.import_batch_id == batch.id)
        .order_by(ImportRow.row_index.asc(), ImportRow.id.asc())
        .all()
    )
    if not import_rows:
        raise HTTPException(
            status_code=400,
            detail="Import batch has no extracted rows.",
        )

    categories_by_name = {
        category.name.casefold(): category.id for category in db.query(Category).all()
    }
    try:
        result = generate_candidate_drafts(
            [
                ImportRowInput(
                    id=row.id,
                    row_index=row.row_index,
                    raw_data_json=row.raw_data_json,
                    raw_text=row.raw_text,
                )
                for row in import_rows
            ],
            categories_by_name,
        )
    except CandidateGenerationError as error:
        batch.status = "failed"
        batch.error_message = str(error)
        db.commit()
        raise HTTPException(status_code=400, detail=str(error)) from error

    rows_by_id = {row.id: row for row in import_rows}
    for issue in result.row_issues:
        row = rows_by_id[issue.import_row_id]
        row.parse_status = issue.status
        row.error_message = issue.message

    candidates = [
        CandidateEvent(
            import_batch_id=batch.id,
            import_row_id=draft.import_row_id,
            title=draft.title,
            description=draft.description,
            all_day=draft.all_day,
            start_datetime=draft.start_datetime,
            end_datetime=draft.end_datetime,
            start_date=draft.start_date,
            end_date=draft.end_date,
            timezone_name=draft.timezone_name,
            location=draft.location,
            category_id=draft.category_id,
            review_status="pending",
        )
        for draft in result.candidates
    ]
    db.add_all(candidates)

    batch.total_candidate_events = len(candidates)
    if candidates:
        batch.status = "ready_for_review"
        batch.error_message = None
    else:
        batch.status = "failed"
        batch.error_message = "No candidate events could be generated from extracted rows."

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Candidate events could not be recorded.",
        ) from error

    if not candidates:
        raise HTTPException(status_code=400, detail=batch.error_message)

    for candidate in candidates:
        db.refresh(candidate)

    skipped_count = sum(
        1
        for issue in result.row_issues
        if issue.status == "skipped" and issue.import_row_id != result.header_row_id
    )
    failed_count = sum(1 for issue in result.row_issues if issue.status == "failed")

    return {
        "batch_id": batch.id,
        "rows_inspected": result.rows_inspected,
        "candidates_created": len(candidates),
        "rows_skipped": skipped_count,
        "rows_failed": failed_count,
        "candidate_preview": [_candidate_preview(candidate) for candidate in candidates[:5]],
    }


@router.get("/batches/{batch_id}/candidates", response_model=list[CandidateEventRead])
def list_import_candidates(batch_id: int, db: Session = Depends(get_db)):
    _get_batch_or_404(batch_id, db)
    candidates = (
        db.query(CandidateEvent)
        .join(ImportRow, CandidateEvent.import_row_id == ImportRow.id)
        .filter(CandidateEvent.import_batch_id == batch_id)
        .order_by(ImportRow.row_index.asc(), CandidateEvent.id.asc())
        .all()
    )
    return [_candidate_payload(candidate) for candidate in candidates]
