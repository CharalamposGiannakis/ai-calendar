from io import BytesIO
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


def workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Candidates"
    for row in [
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
            "Uni",
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
            "Other",
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
    ]:
        worksheet.append(row)

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def upload_xlsx(client):
    response = client.post(
        "/imports/excel/upload",
        files={"file": ("review.xlsx", workbook_bytes(), XLSX_MIME_TYPE)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload_extract_generate(client):
    uploaded = upload_xlsx(client)
    batch_id = uploaded["import_batch"]["id"]
    extract_response = client.post(f"/imports/excel/batches/{batch_id}/extract-rows")
    assert extract_response.status_code == 200, extract_response.text
    generate_response = client.post(
        f"/imports/excel/batches/{batch_id}/generate-candidates"
    )
    assert generate_response.status_code == 200, generate_response.text
    candidates_response = client.get(f"/imports/batches/{batch_id}/candidates")
    assert candidates_response.status_code == 200, candidates_response.text
    return uploaded, candidates_response.json()


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


def test_get_candidate_by_id(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[0]["id"]

    response = client.get(f"/imports/candidates/{candidate_id}")

    assert response.status_code == 200
    assert response.json()["id"] == candidate_id
    assert response.json()["title"] == "Synthetic lecture"


def test_edit_pending_timed_candidate(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    work_id = category_id_by_name(client, "Work")

    response = client.patch(
        f"/imports/candidates/{candidates[0]['id']}",
        json={
            "title": "Edited lecture",
            "description": "Edited timed candidate",
            "start_datetime": "2026-09-03T11:00:00",
            "end_datetime": "2026-09-03T12:00:00",
            "timezone_name": "Europe/Amsterdam",
            "location": "Edited room",
            "category_id": work_id,
            "review_notes": "Checked manually",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Edited lecture"
    assert body["start_datetime"] == "2026-09-03T09:00:00Z"
    assert body["end_datetime"] == "2026-09-03T10:00:00Z"
    assert body["category_id"] == work_id
    assert body["location"] == "Edited room"
    assert body["review_notes"] == "Checked manually"
    assert body["review_status"] == "pending"
    assert body["was_edited"] is True


def test_edit_pending_all_day_candidate(client, upload_storage):
    _, candidates = upload_extract_generate(client)

    response = client.patch(
        f"/imports/candidates/{candidates[1]['id']}",
        json={
            "title": "Edited all-day",
            "description": "Edited all-day candidate",
            "start_date": "2026-10-01",
            "end_date": "2026-10-03",
            "location": "Edited library",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["all_day"] is True
    assert body["title"] == "Edited all-day"
    assert body["start_date"] == "2026-10-01"
    assert body["end_date"] == "2026-10-03"
    assert body["timezone_name"] is None
    assert body["location"] == "Edited library"
    assert body["review_status"] == "pending"


def test_editing_unknown_category_id_is_rejected(client, upload_storage):
    _, candidates = upload_extract_generate(client)

    response = client.patch(
        f"/imports/candidates/{candidates[0]['id']}",
        json={"category_id": 9999},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "category_id does not exist."


def test_editing_approved_candidate_is_rejected(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[0]["id"]
    assert client.post(f"/imports/candidates/{candidate_id}/approve").status_code == 200

    response = client.patch(
        f"/imports/candidates/{candidate_id}",
        json={"title": "Too late"},
    )

    assert response.status_code == 409


def test_reject_pending_candidate_without_creating_event(
    client, upload_storage, tmp_path
):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[0]["id"]

    response = client.post(f"/imports/candidates/{candidate_id}/reject")

    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "rejected"
    with database_connection(tmp_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_rejecting_approved_candidate_is_rejected(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[0]["id"]
    assert client.post(f"/imports/candidates/{candidate_id}/approve").status_code == 200

    response = client.post(f"/imports/candidates/{candidate_id}/reject")

    assert response.status_code == 409


def test_approve_pending_timed_candidate_creates_real_import_event(
    client, upload_storage, tmp_path
):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[0]["id"]

    response = client.post(f"/imports/candidates/{candidate_id}/approve")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate"]["review_status"] == "approved"
    event = body["event"]
    assert event["title"] == "Synthetic lecture"
    assert event["all_day"] is False
    assert event["start_datetime"] == "2026-09-03T07:00:00Z"
    assert event["end_datetime"] == "2026-09-03T08:30:00Z"
    assert event["source_type"] == "import"
    assert event["status"] == "active"
    assert event["candidate_event_id"] == candidate_id

    with database_connection(tmp_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_approve_pending_all_day_candidate_creates_real_import_event(
    client, upload_storage
):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[1]["id"]

    response = client.post(f"/imports/candidates/{candidate_id}/approve")

    assert response.status_code == 200, response.text
    event = response.json()["event"]
    assert event["title"] == "Synthetic study day"
    assert event["all_day"] is True
    assert event["start_datetime"] is None
    assert event["end_datetime"] is None
    assert event["start_date"] == "2026-09-04"
    assert event["end_date"] == "2026-09-05"
    assert event["timezone_name"] is None
    assert event["source_type"] == "import"
    assert event["candidate_event_id"] == candidate_id


def test_approved_candidate_cannot_be_approved_again(
    client, upload_storage, tmp_path
):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[0]["id"]
    assert client.post(f"/imports/candidates/{candidate_id}/approve").status_code == 200

    response = client.post(f"/imports/candidates/{candidate_id}/approve")

    assert response.status_code == 409
    with database_connection(tmp_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_failed_approval_does_not_leave_candidate_approved(
    client, upload_storage, tmp_path
):
    _, candidates = upload_extract_generate(client)
    candidate_id = candidates[0]["id"]
    with database_connection(tmp_path) as connection:
        connection.execute(
            """
            INSERT INTO events (
                title, all_day, start_date, end_date, source_type, status,
                candidate_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Preexisting synthetic event",
                1,
                "2026-09-10",
                "2026-09-11",
                "import",
                "active",
                candidate_id,
            ),
        )

    response = client.post(f"/imports/candidates/{candidate_id}/approve")

    assert response.status_code == 409
    with database_connection(tmp_path) as connection:
        candidate_status = connection.execute(
            "SELECT review_status FROM candidate_events WHERE id = ?",
            (candidate_id,),
        ).fetchone()[0]
        event_count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    assert candidate_status == "pending"
    assert event_count == 1


def test_nonexistent_candidate_returns_404(client, upload_storage):
    assert client.get("/imports/candidates/9999").status_code == 404
    assert client.patch("/imports/candidates/9999", json={"title": "x"}).status_code == 404
    assert client.post("/imports/candidates/9999/reject").status_code == 404
    assert client.post("/imports/candidates/9999/approve").status_code == 404


def test_batch_status_becomes_completed_when_all_candidates_are_terminal(
    client, upload_storage, tmp_path
):
    uploaded, candidates = upload_extract_generate(client)
    batch_id = uploaded["import_batch"]["id"]

    assert client.post(f"/imports/candidates/{candidates[0]['id']}/approve").status_code == 200
    assert client.post(f"/imports/candidates/{candidates[1]['id']}/reject").status_code == 200
    assert client.post(f"/imports/candidates/{candidates[2]['id']}/approve").status_code == 200

    with database_connection(tmp_path) as connection:
        batch_status = connection.execute(
            "SELECT status FROM import_batches WHERE id = ?",
            (batch_id,),
        ).fetchone()[0]

    assert batch_status == "completed"


def test_temp_database_and_upload_storage_are_used(client, upload_storage, tmp_path):
    uploaded, _ = upload_extract_generate(client)
    storage_path = uploaded["source_document"]["storage_path"]
    saved_path = saved_upload_path(upload_storage, storage_path)

    assert saved_path.exists()
    assert str(upload_storage) in str(saved_path)
    assert (tmp_path / "test_ai_calendar.db").exists()
