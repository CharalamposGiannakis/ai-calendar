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


def workbook_bytes(rows=None) -> bytes:
    if rows is None:
        rows = [
            [
                "Summary",
                "Date",
                "Start",
                "End",
                "Category",
                "Location",
                "Notes",
                "All Day",
                "Last Day",
                "Timezone",
            ],
            [
                "Synthetic lecture",
                "2026-09-03",
                "09:00",
                "10:30",
                "uni",
                "Room A",
                "Timed candidate",
                None,
                None,
                "Europe/Amsterdam",
            ],
            [
                "Synthetic study day",
                "2026-09-04",
                None,
                None,
                "Mystery",
                "Library",
                "One-day all-day candidate",
                None,
                None,
                None,
            ],
            [
                "Synthetic conference",
                "2026-09-05",
                None,
                None,
                "Work",
                "Hall",
                "Multi-day all-day candidate",
                True,
                "2026-09-07",
                None,
            ],
            [
                None,
                "2026-09-08",
                "09:00",
                "10:00",
                "Other",
                "Nowhere",
                "Missing title should fail",
                None,
                None,
                None,
            ],
        ]

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Candidates"
    for row in rows:
        worksheet.append(row)

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def upload_xlsx(client, content=None):
    if content is None:
        content = workbook_bytes()
    response = client.post(
        "/imports/excel/upload",
        files={"file": ("candidates.xlsx", content, XLSX_MIME_TYPE)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def extract_rows(client, batch_id):
    response = client.post(f"/imports/excel/batches/{batch_id}/extract-rows")
    assert response.status_code == 200, response.text
    return response.json()


def generate_candidates(client, batch_id):
    return client.post(f"/imports/excel/batches/{batch_id}/generate-candidates")


def upload_extract_and_generate(client):
    uploaded = upload_xlsx(client)
    batch_id = uploaded["import_batch"]["id"]
    extract_rows(client, batch_id)
    response = generate_candidates(client, batch_id)
    assert response.status_code == 200, response.text
    return uploaded, response.json()


def database_connection(tmp_path):
    return sqlite3.connect(tmp_path / "test_ai_calendar.db")


def category_id_by_name(client, name):
    response = client.get("/categories/")
    assert response.status_code == 200
    for category in response.json():
        if category["name"] == name:
            return category["id"]
    raise AssertionError(f"Category not found: {name}")


def saved_upload_path(storage_dir, storage_path):
    relative_path = PurePosixPath(storage_path)
    return storage_dir.joinpath(*relative_path.parts)


def test_successful_candidate_generation_from_extracted_rows(
    client, upload_storage, tmp_path
):
    uploaded, body = upload_extract_and_generate(client)

    assert body["batch_id"] == uploaded["import_batch"]["id"]
    assert body["rows_inspected"] == 4
    assert body["candidates_created"] == 3
    assert body["rows_skipped"] == 0
    assert body["rows_failed"] == 1
    assert [candidate["title"] for candidate in body["candidate_preview"]] == [
        "Synthetic lecture",
        "Synthetic study day",
        "Synthetic conference",
    ]

    with database_connection(tmp_path) as connection:
        event_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        candidate_count = connection.execute(
            "SELECT COUNT(*) FROM candidate_events"
        ).fetchone()[0]

    assert event_count == 0
    assert candidate_count == 3


def test_generated_timed_candidate_has_expected_shape_and_metadata(
    client, upload_storage
):
    uni_id = category_id_by_name(client, "Uni")
    uploaded, _ = upload_extract_and_generate(client)
    batch_id = uploaded["import_batch"]["id"]

    response = client.get(f"/imports/batches/{batch_id}/candidates")

    assert response.status_code == 200
    timed = response.json()[0]
    assert timed["title"] == "Synthetic lecture"
    assert timed["all_day"] is False
    assert timed["start_datetime"] == "2026-09-03T07:00:00Z"
    assert timed["end_datetime"] == "2026-09-03T08:30:00Z"
    assert timed["start_date"] is None
    assert timed["end_date"] is None
    assert timed["timezone_name"] == "Europe/Amsterdam"
    assert timed["category_id"] == uni_id
    assert timed["location"] == "Room A"
    assert timed["description"] == "Timed candidate"
    assert timed["review_status"] == "pending"


def test_generated_all_day_candidates_use_exclusive_end_dates(client, upload_storage):
    work_id = category_id_by_name(client, "Work")
    uploaded, _ = upload_extract_and_generate(client)
    batch_id = uploaded["import_batch"]["id"]

    response = client.get(f"/imports/batches/{batch_id}/candidates")

    assert response.status_code == 200
    one_day = response.json()[1]
    multi_day = response.json()[2]
    assert one_day["title"] == "Synthetic study day"
    assert one_day["all_day"] is True
    assert one_day["start_date"] == "2026-09-04"
    assert one_day["end_date"] == "2026-09-05"
    assert one_day["timezone_name"] is None
    assert one_day["category_id"] is None

    assert multi_day["title"] == "Synthetic conference"
    assert multi_day["all_day"] is True
    assert multi_day["start_date"] == "2026-09-05"
    assert multi_day["end_date"] == "2026-09-08"
    assert multi_day["category_id"] == work_id


def test_batch_status_and_candidate_count_update(client, upload_storage, tmp_path):
    uploaded, _ = upload_extract_and_generate(client)
    batch_id = uploaded["import_batch"]["id"]

    with database_connection(tmp_path) as connection:
        batch = connection.execute(
            """
            SELECT status, total_rows_detected, total_candidate_events, error_message
            FROM import_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        row_states = connection.execute(
            """
            SELECT row_index, parse_status, error_message
            FROM import_rows
            WHERE import_batch_id = ?
            ORDER BY row_index
            """,
            (batch_id,),
        ).fetchall()

    assert batch == ("ready_for_review", 5, 3, None)
    assert row_states[0] == (
        1,
        "skipped",
        "Header row skipped during candidate generation.",
    )
    assert row_states[-1][0] == 5
    assert row_states[-1][1] == "failed"
    assert "title is required" in row_states[-1][2]


def test_get_candidates_endpoint_returns_generated_candidates_ordered_by_row(
    client, upload_storage
):
    uploaded, _ = upload_extract_and_generate(client)
    batch_id = uploaded["import_batch"]["id"]

    response = client.get(f"/imports/batches/{batch_id}/candidates")

    assert response.status_code == 200
    candidates = response.json()
    assert [candidate["source_row_index"] for candidate in candidates] == [2, 3, 4]
    assert [candidate["import_batch_id"] for candidate in candidates] == [batch_id] * 3
    assert all(candidate["import_row_id"] for candidate in candidates)


def test_duplicate_candidate_generation_is_rejected(client, upload_storage):
    uploaded, _ = upload_extract_and_generate(client)
    batch_id = uploaded["import_batch"]["id"]

    response = generate_candidates(client, batch_id)

    assert response.status_code == 409
    assert "already been generated" in response.text


def test_nonexistent_batch_returns_404(client, upload_storage):
    generate_response = generate_candidates(client, 9999)
    list_response = client.get("/imports/batches/9999/candidates")

    assert generate_response.status_code == 404
    assert list_response.status_code == 404


def test_batch_without_extracted_rows_is_rejected(client, upload_storage):
    uploaded = upload_xlsx(client)

    response = generate_candidates(client, uploaded["import_batch"]["id"])

    assert response.status_code == 400
    assert "no extracted rows" in response.text


def test_invalid_only_rows_fail_batch_without_creating_candidates(
    client, upload_storage, tmp_path
):
    uploaded = upload_xlsx(
        client,
        content=workbook_bytes(
            rows=[
                ["Title", "Date", "Start", "End"],
                [None, "2026-09-03", "09:00", "10:00"],
            ]
        ),
    )
    batch_id = uploaded["import_batch"]["id"]
    extract_rows(client, batch_id)

    response = generate_candidates(client, batch_id)

    assert response.status_code == 400
    assert "No candidate events could be generated" in response.text
    with database_connection(tmp_path) as connection:
        batch = connection.execute(
            """
            SELECT status, total_candidate_events, error_message
            FROM import_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        candidate_count = connection.execute(
            "SELECT COUNT(*) FROM candidate_events"
        ).fetchone()[0]

    assert batch == (
        "failed",
        0,
        "No candidate events could be generated from extracted rows.",
    )
    assert candidate_count == 0


def test_temp_database_and_upload_storage_are_used(client, upload_storage, tmp_path):
    uploaded, _ = upload_extract_and_generate(client)
    storage_path = uploaded["source_document"]["storage_path"]
    saved_path = saved_upload_path(upload_storage, storage_path)

    assert saved_path.exists()
    assert str(upload_storage) in str(saved_path)
    assert (tmp_path / "test_ai_calendar.db").exists()
