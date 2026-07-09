# AI Calendar

[![CI](https://github.com/CharalamposGiannakis/ai-calendar/actions/workflows/ci.yml/badge.svg)](https://github.com/CharalamposGiannakis/ai-calendar/actions/workflows/ci.yml)

AI Calendar is a standalone personal calendar and schedule-import project for laptop and phone. The current implementation focuses on reliable manual scheduling, local relational storage, and a review-first Excel import workflow that turns spreadsheet rows into candidate events before they become real calendar entries.

The project is called AI Calendar because the long-term product direction is an AI-assisted calendar: a dependable calendar foundation with a future natural-language and agent layer for interpreting schedules, suggesting changes, and helping with planning. That AI/NLP layer is not implemented yet. Today, the application uses deterministic backend logic rather than an AI agent or LLM parser.

As a public portfolio project, the emphasis is on building the careful foundation an AI calendar would need: explicit time semantics, traceable imports, human approval, conflict awareness, and a clean local web interface.

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
* Dynamic backend duplicate and conflict warnings for import candidates
* Minimal frontend Excel import-review workflow from upload through approval, including candidate warning display
* Responsive, same-origin web interface for creating, editing, deleting, and viewing events
* One-server startup that works locally and on a phone connected to the same network
* GitHub Actions CI for integration tests and backend compilation
* Isolated pytest coverage for API time semantics and migration workflows

The current interface is a selected-day and upcoming-events view. A full day, week, and month calendar view is still planned.

## Screenshots

Screenshots are planned under [docs/screenshots](docs/screenshots/). Only synthetic calendar data should be used. Suggested future files:

* `manual-calendar-view.png`
* `excel-import-review-warnings.png`

## Planned MVP

* PDF table import

## Future AI Direction

Planned AI/NLP capabilities include natural-language event creation, conversational schedule review, agent-assisted import cleanup, semantic duplicate detection, conflict-aware suggestions, and optional voice interaction. These features are intended to build on the existing review-first pipeline rather than bypassing it: imported or inferred events should remain inspectable and user-approved before they affect the calendar.

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
.github/workflows/        Continuous integration workflow
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

The next engineering work is PDF table import on the existing review-first pipeline. AI/NLP agent features come later, after the calendar and import foundation is dependable enough to support them.

## Documentation

* [Architecture](docs/architecture.md)
* [Project overview](docs/project_overview.md)
* [MVP blueprint](docs/mvp_v1_blueprint.md)
* [Current project status](docs/project_status.md)
* [Decision log](docs/decision_log.md)
* [Schema reference](docs/schema_v1.md)
* [Contributor instructions](AGENTS.md)

## License

This project is licensed under the [MIT License](LICENSE).
