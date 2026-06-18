def event_payload(
    title="Synthetic event",
    start="2026-01-15T09:00:00",
    end="2026-01-15T10:00:00",
    category_id=None,
):
    return {
        "title": title,
        "description": "Synthetic test data",
        "start_datetime": start,
        "end_datetime": end,
        "all_day": False,
        "location": "Test room",
        "category_id": category_id,
        "source_type": "manual",
        "status": "active",
    }


def create_event(client, **overrides):
    payload = event_payload(**overrides)
    response = client.post("/events/", json=payload)
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
    names = {category["name"] for category in response.json()}
    assert names == {"Uni", "Work", "Other"}


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
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "Fitness"
    assert body["color"] == "#ef4444"
    assert body["description"] == "Synthetic fitness category"


def test_reject_duplicate_category_name(client):
    first_response = client.post("/categories/", json={"name": "Study"})
    assert first_response.status_code == 201

    duplicate_response = client.post("/categories/", json={"name": "Study"})

    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "Category with this name already exists."


def test_create_event(client):
    category_id = category_id_by_name(client, "Uni")

    response = client.post(
        "/events/",
        json=event_payload(title="Synthetic lecture", category_id=category_id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == "Synthetic lecture"
    assert body["category_id"] == category_id
    assert body["start_datetime"] == "2026-01-15T09:00:00"
    assert body["end_datetime"] == "2026-01-15T10:00:00"


def test_retrieve_event(client):
    created = create_event(client, title="Synthetic appointment")

    response = client.get(f"/events/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Synthetic appointment"


def test_update_event(client):
    created = create_event(client, title="Original title")

    response = client.put(
        f"/events/{created['id']}",
        json={
            "title": "Updated title",
            "end_datetime": "2026-01-15T11:30:00",
            "location": "Updated room",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Updated title"
    assert body["end_datetime"] == "2026-01-15T11:30:00"
    assert body["location"] == "Updated room"


def test_delete_event(client):
    created = create_event(client, title="Event to delete")

    delete_response = client.delete(f"/events/{created['id']}")
    get_response = client.get(f"/events/{created['id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_reject_event_whose_end_is_not_later_than_start(client):
    response = client.post(
        "/events/",
        json=event_payload(
            start="2026-01-15T09:00:00",
            end="2026-01-15T09:00:00",
        ),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "end_datetime must be later than start_datetime."


def test_reject_nonexistent_category_id(client):
    response = client.post(
        "/events/",
        json=event_payload(category_id=9999),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "category_id does not exist."


def test_date_window_overlap_filtering(client):
    create_event(
        client,
        title="Before window",
        start="2026-03-10T08:00:00",
        end="2026-03-10T09:59:59",
    )
    create_event(
        client,
        title="Overlaps start",
        start="2026-03-10T09:30:00",
        end="2026-03-10T10:30:00",
    )
    create_event(
        client,
        title="Inside window",
        start="2026-03-10T10:15:00",
        end="2026-03-10T10:45:00",
    )
    create_event(
        client,
        title="Overlaps end",
        start="2026-03-10T10:50:00",
        end="2026-03-10T12:00:00",
    )
    create_event(
        client,
        title="After window",
        start="2026-03-10T11:00:01",
        end="2026-03-10T12:00:00",
    )

    response = client.get(
        "/events/",
        params={
            "start_from": "2026-03-10T10:00:00",
            "end_to": "2026-03-10T11:00:00",
        },
    )

    assert response.status_code == 200
    titles = [event["title"] for event in response.json()]
    assert titles == ["Overlaps start", "Inside window", "Overlaps end"]


def test_upcoming_event_limit(client):
    create_event(
        client,
        title="First upcoming",
        start="2026-04-01T09:00:00",
        end="2026-04-01T10:00:00",
    )
    create_event(
        client,
        title="Second upcoming",
        start="2026-04-01T11:00:00",
        end="2026-04-01T12:00:00",
    )
    create_event(
        client,
        title="Third upcoming",
        start="2026-04-01T13:00:00",
        end="2026-04-01T14:00:00",
    )

    response = client.get(
        "/events/",
        params={
            "start_from": "2026-04-01T00:00:00",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    titles = [event["title"] for event in response.json()]
    assert titles == ["First upcoming", "Second upcoming"]
