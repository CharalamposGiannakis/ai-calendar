from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import UploadFile

from app.db import ROOT_DIR

MAX_XLSX_UPLOAD_BYTES = 10 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
UPLOAD_RELATIVE_DIR = PurePosixPath("uploads/runtime")


class UploadValidationError(ValueError):
    pass


class UploadTooLargeError(UploadValidationError):
    pass


@dataclass(frozen=True)
class StoredUpload:
    original_filename: str
    storage_path: str
    file_type: str
    mime_type: str | None
    size_bytes: int
    sha256_checksum: str


def default_storage_dir() -> Path:
    return ROOT_DIR / "storage"


def validate_xlsx_filename(filename: str | None) -> str:
    if filename is None or filename.strip() == "":
        raise UploadValidationError("An uploaded file with a filename is required.")

    normalized = filename.strip()
    has_path_separator = "/" in normalized or "\\" in normalized
    has_control_character = any(ord(character) < 32 for character in normalized)
    if (
        has_path_separator
        or ":" in normalized
        or has_control_character
        or normalized in {".", ".."}
        or normalized.startswith("..")
    ):
        raise UploadValidationError("Suspicious filenames are not accepted.")

    path = PurePosixPath(normalized)
    if path.suffix.lower() != ".xlsx" or path.stem == "":
        raise UploadValidationError("Only .xlsx files are accepted.")

    return normalized


def path_for_storage_path(storage_dir: Path, storage_path: str) -> Path:
    relative_path = PurePosixPath(storage_path)
    if relative_path.is_absolute() or ":" in storage_path or ".." in relative_path.parts:
        raise UploadValidationError("Storage path must be relative.")
    return storage_dir.joinpath(*relative_path.parts)


async def store_excel_upload(upload: UploadFile, storage_dir: Path) -> StoredUpload:
    original_filename = validate_xlsx_filename(upload.filename)
    storage_dir = storage_dir.resolve()
    upload_dir = storage_dir.joinpath(*UPLOAD_RELATIVE_DIR.parts)
    upload_dir.mkdir(parents=True, exist_ok=True)

    relative_path = UPLOAD_RELATIVE_DIR / f"{uuid4().hex}.xlsx"
    destination = path_for_storage_path(storage_dir, str(relative_path))

    checksum = sha256()
    size_bytes = 0

    created_file = False
    try:
        with destination.open("xb") as output:
            created_file = True
            while True:
                chunk = await upload.read(UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break

                size_bytes += len(chunk)
                if size_bytes > MAX_XLSX_UPLOAD_BYTES:
                    raise UploadTooLargeError(
                        f"Uploaded .xlsx files must be {MAX_XLSX_UPLOAD_BYTES} bytes or smaller."
                    )

                checksum.update(chunk)
                output.write(chunk)

        if size_bytes == 0:
            raise UploadValidationError("Uploaded file is empty.")

    except Exception:
        if created_file:
            destination.unlink(missing_ok=True)
        raise

    return StoredUpload(
        original_filename=original_filename,
        storage_path=str(relative_path),
        file_type="xlsx",
        mime_type=upload.content_type,
        size_bytes=size_bytes,
        sha256_checksum=checksum.hexdigest(),
    )


def remove_stored_upload(storage_dir: Path, storage_path: str) -> None:
    try:
        path_for_storage_path(storage_dir.resolve(), storage_path).unlink(missing_ok=True)
    except OSError:
        pass
