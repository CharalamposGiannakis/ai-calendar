# AI Calendar

AI Calendar is a standalone personal calendar for laptop and phone. It keeps manual scheduling in a local relational database today, then grows toward a review-first pipeline for turning structured Excel and PDF schedules into calendar events.

## Current capabilities

* FastAPI API for category and event CRUD
* SQLite storage managed by Alembic migrations
* Explicit Europe/Amsterdam and UTC semantics for timed events
* Date-only all-day ranges with exclusive end dates
* Seeded `Uni`, `Work`, and `Other` categories
* DST-safe event validation, date-window filtering, and an optional result limit
* Import-pipeline foundation tables for source documents, batches, rows, and candidates
* Safe `.xlsx` upload storage with source-document metadata and pending import batches
* Raw Excel row extraction into `import_rows`
* Deterministic Excel candidate generation into pending `candidate_events`
* Backend candidate editing, rejection, and approval into real import events
* Responsive, same-origin web interface for creating, editing, deleting, and viewing events
* One-server startup that works locally and on a phone connected to the same network
* Isolated pytest coverage for API time semantics and migration workflows

The current interface is a selected-day and upcoming-events view. A full day, week, and month calendar view is still planned.

## Planned MVP

* PDF table import
* Frontend candidate review workflow
* Duplicate and conflict warnings for imported candidates

## Technology

* Python, FastAPI, SQLAlchemy, and Pydantic
* SQLite with Alembic migrations
* HTML, CSS, and vanilla JavaScript frontend
* Pytest and HTTPX for automated API tests

## Project structure

```text
frontend/                 Editable frontend source served by FastAPI
backend/app/              FastAPI application, models, routers, and seed data
backend/alembic/          Versioned database migrations
scripts/                  Startup, database adoption, verification, and export scripts
tests/integration/        Isolated API and migration tests
docs/                     Product, schema, status, and decision documentation
```

## Setup and run

From the repository root in PowerShell:

```powershell
py -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
.\scripts\run_app.ps1
```

The startup script applies migrations before it launches Uvicorn. A fresh database is created automatically. A legacy database that already has `categories` and `events` but no Alembic revision must be adopted once before starting the app:

```powershell
.\scripts\adopt_existing_database.ps1
.\scripts\run_app.ps1
```

Open `http://127.0.0.1:8000` on the laptop. The same server listens on the local network, so a phone on the same Wi-Fi can use `http://<laptop-lan-ip>:8000`.

## Testing

Run the isolated integration suite:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest tests\integration
```

Run the Python compilation sanity check:

```powershell
.\backend\.venv\Scripts\python.exe -m compileall backend\app
```

The tests create temporary SQLite databases and do not use the local development database.

## Roadmap

The next engineering work is a minimal frontend review workflow for generated candidates. PDF parsing, conflict checks, and later AI-assisted features follow from that foundation.

## Documentation

* [Project overview](docs/project_overview.md)
* [MVP blueprint](docs/mvp_v1_blueprint.md)
* [Current project status](docs/project_status.md)
* [Decision log](docs/decision_log.md)
* [Schema reference](docs/schema_v1.md)
* [Contributor instructions](AGENTS.md)
