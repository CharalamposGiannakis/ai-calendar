from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
import sqlite3
from zipfile import ZipFile

import pytest

from app.import_storage import MAX_XLSX_UPLOAD_BYTES
from app.main import app
from app.routers.imports import get_storage_dir

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def upload_storage(client, tmp_path):
    storage_dir = tmp_path / "isolated-storage"
    app.dependency_overrides[get_storage_dir] = lambda: storage_dir
    try:
        yield storage_dir
    finally:
        app.dependency_overrides.pop(get_storage_dir, None)


def synthetic_xlsx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                "<sheets><sheet name=\"Sheet1\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
                "</workbook>"
            ),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet1.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                "<sheetData><row r=\"1\"><c r=\"A1\" t=\"inlineStr\"><is><t>Synthetic</t></is></c></row></sheetData>"
                "</worksheet>"
            ),
        )
    return buffer.getvalue()


def upload_xlsx(client, filename="synthetic.xlsx", content=None, content_type=XLSX_MIME_TYPE):
    if content is None:
        content = synthetic_xlsx_bytes()
    return client.post(
        "/imports/excel/upload",
        files={"file": (filename, content, content_type)},
    )


def saved_upload_path(storage_dir, storage_path):
    relative_path = PurePosixPath(storage_path)
    return storage_dir.joinpath(*relative_path.parts)


def runtime_files(storage_dir):
    runtime_dir = storage_dir / "uploads" / "runtime"
    if not runtime_dir.exists():
        return []
    return list(runtime_dir.iterdir())


def database_connection(tmp_path):
    return sqlite3.connect(tmp_path / "test_ai_calendar.db")


def test_successful_xlsx_upload_creates_file_on_disk(client, upload_storage):
    content = synthetic_xlsx_bytes()

    response = upload_xlsx(client, content=content)

    assert response.status_code == 201, response.text
    storage_path = response.json()["source_document"]["storage_path"]
    saved_path = saved_upload_path(upload_storage, storage_path)
    assert saved_path.exists()
    assert saved_path.read_bytes() == content


def test_successful_upload_creates_source_document_and_import_batch_rows(
    client, upload_storage, tmp_path
):
    content = synthetic_xlsx_bytes()

    response = upload_xlsx(client, filename="schedule.xlsx", content=content)

    assert response.status_code == 201, response.text
    body = response.json()
    with database_connection(tmp_path) as connection:
        source_documents = connection.execute(
            """
            SELECT id, original_filename, storage_path, file_type, mime_type, size_bytes,
                   sha256_checksum
            FROM source_documents
            """
        ).fetchall()
        import_batches = connection.execute(
            """
            SELECT source_document_id, status, parser_name, total_rows_detected,
                   total_candidate_events
            FROM import_batches
            """
        ).fetchall()
        import_row_count = connection.execute("SELECT COUNT(*) FROM import_rows").fetchone()[0]
        candidate_count = connection.execute("SELECT COUNT(*) FROM candidate_events").fetchone()[0]

    assert source_documents == [
        (
            body["source_document"]["id"],
            "schedule.xlsx",
            body["source_document"]["storage_path"],
            "xlsx",
            XLSX_MIME_TYPE,
            len(content),
            sha256(content).hexdigest(),
        )
    ]
    assert import_batches == [
        (body["source_document"]["id"], "pending", None, 0, 0)
    ]
    assert body["import_batch"]["source_document_id"] == body["source_document"]["id"]
    assert import_row_count == 0
    assert candidate_count == 0


def test_upload_response_contains_expected_metadata_without_absolute_path(
    client, upload_storage
):
    content = synthetic_xlsx_bytes()

    response = upload_xlsx(client, filename="UPPER.XLSX", content=content)

    assert response.status_code == 201, response.text
    body = response.json()
    source_document = body["source_document"]
    import_batch = body["import_batch"]
    storage_path = source_document["storage_path"]

    assert source_document["original_filename"] == "UPPER.XLSX"
    assert source_document["file_type"] == "xlsx"
    assert source_document["mime_type"] == XLSX_MIME_TYPE
    assert source_document["size_bytes"] == len(content)
    assert source_document["sha256_checksum"] == sha256(content).hexdigest()
    assert storage_path.startswith("uploads/runtime/")
    assert not PurePosixPath(storage_path).is_absolute()
    assert ":" not in storage_path
    assert str(upload_storage) not in storage_path
    assert import_batch["status"] == "pending"
    assert import_batch["total_rows_detected"] == 0
    assert import_batch["total_candidate_events"] == 0


def test_rejects_missing_file(client, upload_storage, tmp_path):
    response = client.post("/imports/excel/upload")

    assert response.status_code == 400
    assert runtime_files(upload_storage) == []
    with database_connection(tmp_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM source_documents").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM import_batches").fetchone()[0] == 0


def test_rejects_non_xlsx_file(client, upload_storage):
    response = upload_xlsx(
        client,
        filename="schedule.csv",
        content=b"start,end,title\n",
        content_type="text/csv",
    )

    assert response.status_code == 400
    assert "Only .xlsx" in response.text
    assert runtime_files(upload_storage) == []


def test_rejects_path_traversal_filename(client, upload_storage):
    response = upload_xlsx(client, filename="../bad.xlsx")

    assert response.status_code == 400
    assert "Suspicious" in response.text
    assert runtime_files(upload_storage) == []


def test_rejects_empty_file(client, upload_storage):
    response = upload_xlsx(client, content=b"")

    assert response.status_code == 400
    assert "empty" in response.text
    assert runtime_files(upload_storage) == []


def test_rejects_oversized_file(client, upload_storage):
    response = upload_xlsx(client, content=b"x" * (MAX_XLSX_UPLOAD_BYTES + 1))

    assert response.status_code == 413
    assert "bytes or smaller" in response.text
    assert runtime_files(upload_storage) == []
