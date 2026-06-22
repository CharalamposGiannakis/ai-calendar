def timed_payload(
    title="Synthetic timed event",
    start="2026-01-15T09:00:00",
    end="2026-01-15T10:00:00",
    timezone_name="Europe/Amsterdam",
    category_id=None,
):
    return {
        "title": title,
        "description": "Synthetic test data",
        "all_day": False,
        "start_datetime": start,
        "end_datetime": end,
        "start_date": None,
        "end_date": None,
        "timezone_name": timezone_name,
        "location": "Test room",
        "category_id": category_id,
        "source_type": "manual",
        "status": "active",
    }


def all_day_payload(
    title="Synthetic all-day event",
    start_date="2026-09-03",
    end_date="2026-09-04",
    category_id=None,
):
    return {
        "title": title,
        "description": "Synthetic test data",
        "all_day": True,
        "start_datetime": None,
        "end_datetime": None,
        "start_date": start_date,
        "end_date": end_date,
        "timezone_name": None,
        "location": "Test room",
        "category_id": category_id,
        "source_type": "manual",
        "status": "active",
    }


def create_timed_event(client, **overrides):
    response = client.post("/events/", json=timed_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def create_all_day_event(client, **overrides):
    response = client.post("/events/", json=all_day_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def category_id_by_name(client, name):
    response = client.get("/categories/")
    assert response.status_code == 200
    for category in response.json():
        if category["name"] == name:
            return category["id"]
    raise AssertionError(f"Category not found: {name}")


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_seeded_categories(client):
    response = client.get("/categories/")

    assert response.status_code == 200
    assert {category["name"] for category in response.json()} == {"Uni", "Work", "Other"}


def test_create_category(client):
    response = client.post(
        "/categories/",
        json={
            "name": "Fitness",
            "color": "#ef4444",
            "description": "Synthetic fitness category",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Fitness"


def test_reject_duplicate_category_name(client):
    assert client.post("/categories/", json={"name": "Study"}).status_code == 201

    response = client.post("/categories/", json={"name": "Study"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Category with this name already exists."


def test_timed_create_normalizes_naive_amsterdam_input_to_utc(client):
    category_id = category_id_by_name(client, "Uni")

    body = create_timed_event(client, category_id=category_id)

    assert body["category_id"] == category_id
    assert body["timezone_name"] == "Europe/Amsterdam"
    assert body["start_datetime"] == "2026-01-15T08:00:00Z"
    assert body["end_datetime"] == "2026-01-15T09:00:00Z"
    assert body["start_date"] is None
    assert body["end_date"] is None


def test_timed_create_accepts_offset_aware_input(client):
    body = create_timed_event(
        client,
        start="2026-07-01T10:00:00+02:00",
        end="2026-07-01T11:00:00+02:00",
    )

    assert body["start_datetime"] == "2026-07-01T08:00:00Z"
    assert body["end_datetime"] == "2026-07-01T09:00:00Z"


def test_reject_timed_naive_input_without_timezone(client):
    payload = timed_payload(timezone_name=None)

    response = client.post("/events/", json=payload)

    assert response.status_code == 422
    assert "timezone_name" in response.text


def test_reject_invalid_timezone(client):
    response = client.post("/events/", json=timed_payload(timezone_name="Invalid/Zone"))

    assert response.status_code == 422
    assert "IANA" in response.text


def test_reject_nonexistent_amsterdam_dst_time(client):
    response = client.post(
        "/events/",
        json=timed_payload(
            start="2026-03-29T02:30:00",
            end="2026-03-29T03:30:00",
        ),
    )

    assert response.status_code == 422
    assert "does not exist" in response.text


def test_reject_ambiguous_amsterdam_dst_time(client):
    response = client.post(
        "/events/",
        json=timed_payload(
            start="2026-10-25T02:30:00",
            end="2026-10-25T03:30:00",
        ),
    )

    assert response.status_code == 422
    assert "ambiguous" in response.text


def test_reject_timed_end_not_later_than_start(client):
    response = client.post(
        "/events/",
        json=timed_payload(end="2026-01-15T09:00:00"),
    )

    assert response.status_code == 422
    assert "later" in response.text


def test_reject_nonexistent_category_id(client):
    response = client.post("/events/", json=timed_payload(category_id=9999))

    assert response.status_code == 400
    assert response.json()["detail"] == "category_id does not exist."


def test_one_day_all_day_event_round_trip(client):
    body = create_all_day_event(client)

    assert body["all_day"] is True
    assert body["start_date"] == "2026-09-03"
    assert body["end_date"] == "2026-09-04"
    assert body["start_datetime"] is None
    assert body["end_datetime"] is None
    assert body["timezone_name"] is None


def test_multi_day_all_day_event_round_trip(client):
    body = create_all_day_event(client, start_date="2026-09-03", end_date="2026-09-07")

    assert body["start_date"] == "2026-09-03"
    assert body["end_date"] == "2026-09-07"


def test_reject_mixed_date_and_datetime_event_shape(client):
    payload = timed_payload()
    payload["start_date"] = "2026-01-15"
    payload["end_date"] = "2026-01-16"

    response = client.post("/events/", json=payload)

    assert response.status_code == 422
    assert "date-only" in response.text


def test_timed_to_all_day_update_clears_timed_fields(client):
    created = create_timed_event(client)

    response = client.put(
        f"/events/{created['id']}",
        json={"all_day": True, "start_date": "2026-02-01", "end_date": "2026-02-03"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["all_day"] is True
    assert body["start_datetime"] is None
    assert body["timezone_name"] is None
    assert body["end_date"] == "2026-02-03"


def test_all_day_to_timed_update_clears_date_fields(client):
    created = create_all_day_event(client)

    response = client.put(
        f"/events/{created['id']}",
        json={
            "all_day": False,
            "start_datetime": "2026-09-03T09:00:00",
            "end_datetime": "2026-09-03T10:00:00",
            "timezone_name": "Europe/Amsterdam",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["all_day"] is False
    assert body["start_date"] is None
    assert body["end_date"] is None
    assert body["start_datetime"] == "2026-09-03T07:00:00Z"


def test_half_open_timed_overlap_filtering(client):
    create_timed_event(
        client,
        title="Before window",
        start="2026-03-10T08:00:00",
        end="2026-03-10T09:00:00",
    )
    create_timed_event(
        client,
        title="Overlaps window",
        start="2026-03-10T09:30:00",
        end="2026-03-10T10:30:00",
    )
    create_timed_event(
        client,
        title="At window end",
        start="2026-03-10T11:00:00",
        end="2026-03-10T12:00:00",
    )

    response = client.get(
        "/events/",
        params={
            "start_from": "2026-03-10T08:00:00Z",
            "end_to": "2026-03-10T10:00:00Z",
        },
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Overlaps window"]


def test_half_open_all_day_overlap_filtering(client):
    create_all_day_event(
        client,
        title="One day",
        start_date="2026-09-03",
        end_date="2026-09-04",
    )

    matching = client.get(
        "/events/",
        params={"date_from": "2026-09-03", "date_to": "2026-09-04"},
    )
    outside = client.get(
        "/events/",
        params={"date_from": "2026-09-04", "date_to": "2026-09-05"},
    )

    assert [item["title"] for item in matching.json()] == ["One day"]
    assert outside.json() == []


def test_selected_day_filtering_returns_timed_and_all_day_events(client):
    create_all_day_event(client, title="All-day match")
    create_timed_event(
        client,
        title="Timed match",
        start="2026-09-03T09:00:00",
        end="2026-09-03T10:00:00",
    )

    response = client.get(
        "/events/",
        params={
            "date_from": "2026-09-03",
            "date_to": "2026-09-04",
            "timezone_name": "Europe/Amsterdam",
        },
    )

    assert response.status_code == 200
    assert {item["title"] for item in response.json()} == {"All-day match", "Timed match"}


def test_mixed_event_ordering_and_limit_are_deterministic(client):
    create_all_day_event(client, title="All-day second")
    create_timed_event(
        client,
        title="Timed first",
        start="2026-09-03T08:00:00",
        end="2026-09-03T09:00:00",
    )
    create_all_day_event(
        client,
        title="All-day third",
        start_date="2026-09-04",
        end_date="2026-09-05",
    )

    response = client.get(
        "/events/",
        params={"date_from": "2026-09-03", "date_to": "2026-09-05", "limit": 2},
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Timed first", "All-day second"]


def test_delete_event(client):
    created = create_timed_event(client)

    assert client.delete(f"/events/{created['id']}").status_code == 204
    assert client.get(f"/events/{created['id']}").status_code == 404
