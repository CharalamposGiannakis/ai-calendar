# AI Calendar - Current Project Status

**Last updated:** 22 June 2026
**Current phase:** Working manual-calendar vertical slice

## Project goal

Build a standalone personal calendar application for laptop and phone. The MVP combines fast manual scheduling with a later review-first workflow for importing structured Excel and PDF schedules.

## Implemented

### Backend and data

* FastAPI category and event CRUD API
* SQLite persistence through SQLAlchemy
* Alembic migration `20260619_0001` for `categories` and `events`
* seeded Uni, Work, and Other categories
* event-time and category-existence validation
* date-window filtering and optional result limits
* automated pytest API and migration coverage

### Frontend

* `frontend/` is the single editable frontend source
* FastAPI serves the frontend and API from one server
* responsive manual event creation, editing, and deletion
* category selection, selected-date event list, and upcoming-event list
* same-origin API requests for laptop and phone access

### Runtime

* `scripts/run_app.ps1` migrates a fresh database before launching Uvicorn on `0.0.0.0:8000`
* the existing development database is adopted and stamped at `20260619_0001`
* a legacy database with application tables but no Alembic revision must use `scripts/adopt_existing_database.ps1` before normal startup

## Verification completed

* FastAPI application and API documentation load
* manual category and event workflows work through the API and frontend
* frontend single-source check passes through `scripts/verify_frontend_single_source.ps1`
* 13 isolated integration tests pass, including migration upgrade, check, and downgrade
* Python compilation sanity check passes

## Engineering gaps

* day, week, and month calendar views are not implemented
* Excel and PDF imports are not implemented
* import tables and candidate-event review are not implemented
* timezone and all-day storage semantics need an explicit decision
* `docs/architecture.md` and `docs/roadmap.md` remain placeholders

## Immediate next task

Define timezone and all-day semantics, record the decision, then add the first migration for import pipeline tables: `source_documents`, `import_batches`, `import_rows`, and `candidate_events`.
