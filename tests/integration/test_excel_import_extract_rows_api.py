from hashlib import sha256
from io import BytesIO
import json
from pathlib import PurePosixPath
import sqlite3

import pytest
from openpyxl import Workbook

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


def workbook_bytes(rows=None, worksheet_name="Schedule") -> bytes:
    if rows is None:
        rows = [
            ["Title", "Day", "Duration"],
            ["Lecture", "2026-09-03", 90],
            [None, None, None],
            ["Workshop", None, True],
        ]

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = worksheet_name
    for row in rows:
        worksheet.append(row)

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def upload_xlsx(client, content=None, filename="schedule.xlsx"):
    if content is None:
        content = workbook_bytes()
    response = client.post(
        "/imports/excel/upload",
        files={"file": (filename, content, XLSX_MIME_TYPE)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def saved_upload_path(storage_dir, storage_path):
    relative_path = PurePosixPath(storage_path)
    return storage_dir.joinpath(*relative_path.parts)


def database_connection(tmp_path):
    return sqlite3.connect(tmp_path / "test_ai_calendar.db")


def insert_source_document_and_batch(
    tmp_path,
    *,
    storage_path="uploads/runtime/synthetic.pdf",
    file_type="pdf",
):
    with database_connection(tmp_path) as connection:
        connection.execute(
            """
            INSERT INTO source_documents (
                original_filename, storage_path, file_type, mime_type, size_bytes,
                sha256_checksum
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "synthetic.pdf",
                storage_path,
                file_type,
                "application/pdf",
                4,
                sha256(b"test").hexdigest(),
            ),
        )
        source_document_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO import_batches (source_document_id) VALUES (?)",
            (source_document_id,),
        )
        batch_id = connection.execute("SELECT last_insert_rowid()").fetchone()[0]
    return source_document_id, batch_id


def extract_rows(client, batch_id):
    return client.post(f"/imports/excel/batches/{batch_id}/extract-rows")


def test_successful_extraction_from_uploaded_xlsx(client, upload_storage, tmp_path):
    uploaded = upload_xlsx(client)
    batch_id = uploaded["import_batch"]["id"]

    response = extract_rows(client, batch_id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "batch_id": batch_id,
        "source_document_id": uploaded["source_document"]["id"],
        "worksheet_name": "Schedule",
        "rows_extracted": 3,
        "row_preview": [
            {"row_index": 1, "values": ["Title", "Day", "Duration"]},
            {"row_index": 2, "values": ["Lecture", "2026-09-03", 90]},
            {"row_index": 4, "values": ["Workshop", None, True]},
        ],
    }

    with database_connection(tmp_path) as connection:
        batch = connection.execute(
            """
            SELECT status, parser_name, total_rows_detected, total_candidate_events,
                   error_message
            FROM import_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        row_count = connection.execute(
            "SELECT COUNT(*) FROM import_rows WHERE import_batch_id = ?",
            (batch_id,),
        ).fetchone()[0]
        candidate_count = connection.execute(
            "SELECT COUNT(*) FROM candidate_events"
        ).fetchone()[0]

    assert batch == ("processing", "openpyxl", 3, 0, None)
    assert row_count == 3
    assert candidate_count == 0


def test_import_rows_use_excel_row_indexes_and_preserve_compact_json_content(
    client, upload_storage, tmp_path
):
    uploaded = upload_xlsx(client)
    batch_id = uploaded["import_batch"]["id"]

    response = extract_rows(client, batch_id)

    assert response.status_code == 200, response.text
    with database_connection(tmp_path) as connection:
        rows = connection.execute(
            """
            SELECT row_index, source_locator_json, raw_text, raw_data_json, parse_status
            FROM import_rows
            WHERE import_batch_id = ?
            ORDER BY row_index
            """,
            (batch_id,),
        ).fetchall()

    assert [row[0] for row in rows] == [1, 2, 4]
    assert [json.loads(row[2]) for row in rows] == [
        ["Title", "Day", "Duration"],
        ["Lecture", "2026-09-03", 90],
        ["Workshop", None, True],
    ]
    assert [json.loads(row[3]) for row in rows] == [
        ["Title", "Day", "Duration"],
        ["Lecture", "2026-09-03", 90],
        ["Workshop", None, True],
    ]
    assert [json.loads(row[1]) for row in rows] == [
        {"worksheet": "Schedule", "row": 1},
        {"worksheet": "Schedule", "row": 2},
        {"worksheet": "Schedule", "row": 4},
    ]
    assert {row[4] for row in rows} == {"parsed"}


def test_get_rows_endpoint_returns_rows_for_batch(client, upload_storage):
    uploaded = upload_xlsx(client)
    batch_id = uploaded["import_batch"]["id"]
    assert extract_rows(client, batch_id).status_code == 200

    response = client.get(f"/imports/batches/{batch_id}/rows")

    assert response.status_code == 200
    body = response.json()
    assert [row["row_index"] for row in body] == [1, 2, 4]
    assert [json.loads(row["raw_data_json"]) for row in body] == [
        ["Title", "Day", "Duration"],
        ["Lecture", "2026-09-03", 90],
        ["Workshop", None, True],
    ]


def test_duplicate_extraction_is_rejected(client, upload_storage):
    uploaded = upload_xlsx(client)
    batch_id = uploaded["import_batch"]["id"]
    assert extract_rows(client, batch_id).status_code == 200

    response = extract_rows(client, batch_id)

    assert response.status_code == 409
    assert "already been extracted" in response.text


def test_nonexistent_batch_returns_404(client, upload_storage):
    extract_response = extract_rows(client, 9999)
    rows_response = client.get("/imports/batches/9999/rows")

    assert extract_response.status_code == 404
    assert rows_response.status_code == 404


def test_unsupported_source_document_type_is_rejected(client, upload_storage, tmp_path):
    storage_path = "uploads/runtime/synthetic.pdf"
    _, batch_id = insert_source_document_and_batch(
        tmp_path,
        storage_path=storage_path,
        file_type="pdf",
    )
    saved_path = saved_upload_path(upload_storage, storage_path)
    saved_path.parent.mkdir(parents=True, exist_ok=True)
    saved_path.write_bytes(b"%PDF")

    response = extract_rows(client, batch_id)

    assert response.status_code == 400
    assert "not an .xlsx" in response.text


def test_missing_stored_file_is_rejected(client, upload_storage, tmp_path):
    uploaded = upload_xlsx(client)
    batch_id = uploaded["import_batch"]["id"]
    saved_path = saved_upload_path(
        upload_storage,
        uploaded["source_document"]["storage_path"],
    )
    saved_path.unlink()

    response = extract_rows(client, batch_id)

    assert response.status_code == 404
    assert "not found" in response.text
    with database_connection(tmp_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM import_rows").fetchone()[0] == 0


def test_corrupt_workbook_is_rejected_and_marks_batch_failed(
    client, upload_storage, tmp_path
):
    uploaded = upload_xlsx(client, content=b"not a valid workbook")
    batch_id = uploaded["import_batch"]["id"]

    response = extract_rows(client, batch_id)

    assert response.status_code == 400
    assert "Workbook extraction failed" in response.text
    with database_connection(tmp_path) as connection:
        batch = connection.execute(
            "SELECT status, total_rows_detected, error_message FROM import_batches WHERE id = ?",
            (batch_id,),
        ).fetchone()
        row_count = connection.execute("SELECT COUNT(*) FROM import_rows").fetchone()[0]

    assert batch == ("failed", 0, "Workbook extraction failed.")
    assert row_count == 0
