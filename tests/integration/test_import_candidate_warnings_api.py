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
    ]:
        worksheet.append(row)

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def upload_extract_generate(client):
    upload_response = client.post(
        "/imports/excel/upload",
        files={"file": ("warnings.xlsx", workbook_bytes(), XLSX_MIME_TYPE)},
    )
    assert upload_response.status_code == 201, upload_response.text
    uploaded = upload_response.json()
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


def category_id_by_name(client, name):
    response = client.get("/categories/")
    assert response.status_code == 200
    for category in response.json():
        if category["name"] == name:
            return category["id"]
    raise AssertionError(f"Category not found: {name}")


def create_timed_event(
    client,
    *,
    title="Synthetic event",
    start="2026-09-03T09:15:00",
    end="2026-09-03T10:00:00",
    category_id=None,
    status="active",
):
    response = client.post(
        "/events/",
        json={
            "title": title,
            "description": "Synthetic warning fixture",
            "all_day": False,
            "start_datetime": start,
            "end_datetime": end,
            "start_date": None,
            "end_date": None,
            "timezone_name": "Europe/Amsterdam",
            "location": "Fixture room",
            "category_id": category_id,
            "source_type": "manual",
            "status": status,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_all_day_event(
    client,
    *,
    title="Synthetic event",
    start_date="2026-09-04",
    end_date="2026-09-05",
    category_id=None,
    status="active",
):
    response = client.post(
        "/events/",
        json={
            "title": title,
            "description": "Synthetic warning fixture",
            "all_day": True,
            "start_datetime": None,
            "end_datetime": None,
            "start_date": start_date,
            "end_date": end_date,
            "timezone_name": None,
            "location": "Fixture room",
            "category_id": category_id,
            "source_type": "manual",
            "status": status,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def warning_types(candidate):
    return [warning["type"] for warning in candidate["warnings"]]


def saved_upload_path(storage_dir, storage_path):
    relative_path = PurePosixPath(storage_path)
    return storage_dir.joinpath(*relative_path.parts)


def test_candidate_with_no_warning_returns_empty_list(client, upload_storage):
    _, candidates = upload_extract_generate(client)

    response = client.get(f"/imports/candidates/{candidates[0]['id']}")

    assert response.status_code == 200
    assert response.json()["warnings"] == []


def test_timed_duplicate_warning(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    uni_id = category_id_by_name(client, "Uni")
    event = create_timed_event(
        client,
        title=" synthetic lecture ",
        category_id=uni_id,
    )

    response = client.get(f"/imports/candidates/{candidates[0]['id']}")

    assert response.status_code == 200
    warning = response.json()["warnings"][0]
    assert warning["type"] == "duplicate"
    assert warning["event_id"] == event["id"]
    assert warning["event_title"] == " synthetic lecture "
    assert warning["event_start"] == "2026-09-03T07:15:00Z"
    assert warning["event_end"] == "2026-09-03T08:00:00Z"


def test_timed_conflict_warning(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    event = create_timed_event(client, title="Different overlapping event")

    response = client.get(f"/imports/candidates/{candidates[0]['id']}")

    assert response.status_code == 200
    warning = response.json()["warnings"][0]
    assert warning["type"] == "conflict"
    assert warning["event_id"] == event["id"]


def test_all_day_duplicate_warning(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    other_id = category_id_by_name(client, "Other")
    event = create_all_day_event(
        client,
        title="SYNTHETIC STUDY DAY",
        category_id=other_id,
    )

    response = client.get(f"/imports/candidates/{candidates[1]['id']}")

    assert response.status_code == 200
    warning = response.json()["warnings"][0]
    assert warning["type"] == "duplicate"
    assert warning["event_id"] == event["id"]
    assert warning["event_start"] == "2026-09-04"
    assert warning["event_end"] == "2026-09-05"


def test_all_day_conflict_warning(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    create_all_day_event(client, title="Different all-day event")

    response = client.get(f"/imports/candidates/{candidates[1]['id']}")

    assert response.status_code == 200
    assert warning_types(response.json()) == ["conflict"]


def test_mixed_timed_and_all_day_overlap_is_conflict(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    create_all_day_event(
        client,
        title="All-day blocker",
        start_date="2026-09-03",
        end_date="2026-09-04",
    )

    response = client.get(f"/imports/candidates/{candidates[0]['id']}")

    assert response.status_code == 200
    assert warning_types(response.json()) == ["conflict"]


def test_warnings_appear_in_candidate_list_endpoint(client, upload_storage):
    uploaded, candidates = upload_extract_generate(client)
    batch_id = uploaded["import_batch"]["id"]
    create_timed_event(client, title="Different overlapping event")

    response = client.get(f"/imports/batches/{batch_id}/candidates")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == candidates[0]["id"]
    assert warning_types(body[0]) == ["conflict"]
    assert body[1]["warnings"] == []


def test_warnings_appear_in_single_candidate_endpoint(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    create_all_day_event(client, title="Different all-day event")

    response = client.get(f"/imports/candidates/{candidates[1]['id']}")

    assert response.status_code == 200
    assert warning_types(response.json()) == ["conflict"]


def test_approval_still_works_when_warning_exists(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    create_timed_event(client, title="Different overlapping event")

    response = client.post(f"/imports/candidates/{candidates[0]['id']}/approve")

    assert response.status_code == 200, response.text
    assert response.json()["candidate"]["review_status"] == "approved"
    assert response.json()["event"]["candidate_event_id"] == candidates[0]["id"]


def test_non_active_events_are_ignored(client, upload_storage):
    _, candidates = upload_extract_generate(client)
    create_timed_event(
        client,
        title="Synthetic lecture",
        status="deleted",
    )

    response = client.get(f"/imports/candidates/{candidates[0]['id']}")

    assert response.status_code == 200
    assert response.json()["warnings"] == []


def test_temp_database_and_upload_storage_are_used(client, upload_storage, tmp_path):
    uploaded, _ = upload_extract_generate(client)
    storage_path = uploaded["source_document"]["storage_path"]
    saved_path = saved_upload_path(upload_storage, storage_path)

    assert saved_path.exists()
    assert str(upload_storage) in str(saved_path)
    assert (tmp_path / "test_ai_calendar.db").exists()

    with sqlite3.connect(tmp_path / "test_ai_calendar.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM candidate_events").fetchone()[0] == 2
