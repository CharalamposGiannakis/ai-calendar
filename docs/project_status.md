# AI Calendar — Current Project Status

**Last updated:** 19 June 2026
**Current phase:** Working manual-calendar vertical slice

## Project goal

Build a standalone personal calendar application for laptop and phone.

The initial product must support:

* manual event management
* Excel table import
* PDF table import
* review of imported candidate events before approval

The system should remain expandable for later natural-language, voice, agent, reminder, and semantic features.

## Source of truth

* Repository and Git commits: exact implementation history
* `AGENTS.md`: permanent Codex working rules
* `docs/project_status.md`: current operational state
* `docs/decision_log.md`: important product and architecture decisions
* `docs/mvp_v1_blueprint.md`: MVP boundaries and product direction

## Implemented

### Backend

* FastAPI application
* SQLite persistence
* SQLAlchemy models
* Pydantic request and response schemas
* category CRUD
* event CRUD
* event time validation
* category existence validation
* date-window event filtering
* upcoming-event limit
* automated pytest API tests for category and event behavior
* default categories:

  * Uni
  * Work
  * Other
* health endpoint
* API documentation through FastAPI
* CORS configuration
* frontend served through FastAPI

### Frontend

* `frontend/` is the single editable source of truth
* FastAPI serves `frontend/index.html` and `frontend/` assets directly
* responsive manual scheduling interface
* event creation
* event editing
* event deletion
* compact deletion confirmation
* category selection
* selected-date event view
* upcoming-events view when no date is selected
* start/end date synchronization
* all-day event behavior
* event cards with edit and delete controls

### Runtime and access

* one FastAPI server serves both API and frontend
* frontend uses same-origin API calls for laptop and phone access
* application works locally at `http://127.0.0.1:8000`
* application works on a phone connected to the same Wi-Fi
* PowerShell startup script exists at `scripts/run_app.ps1`

## Implemented database tables

* `categories`
* `events`

## Planned import tables

* `source_documents`
* `import_batches`
* `import_rows`
* `candidate_events`

## Current storage policy

Stored in Git:

* source code
* documentation
* scripts
* synthetic fixtures
* small sample input files

Excluded from Git:

* SQLite runtime database
* real personal documents
* runtime uploads
* generated parsing output
* logs and caches
* virtual environments

## Frontend serving decision

`frontend/` is the only editable frontend location.

FastAPI serves:

* `/` from `frontend/index.html`
* `/static/*` from files in `frontend/`

The old manually maintained `backend/app/static/` frontend copy has been removed.

## Verification completed

* FastAPI starts successfully
* API documentation loads
* categories can be created and listed
* events can be created and listed
* events can be edited and deleted
* SQLite persistence works
* frontend can communicate with the API
* application is accessible from laptop and phone
* Python compilation sanity check passed
* frontend single-source verification passes through `scripts/verify_frontend_single_source.ps1`
* automated API test suite passes: 12 tests

## Engineering gaps

* no database migrations yet
* import tables are not implemented
* Excel upload is not implemented
* PDF upload is not implemented
* architecture, schema, and roadmap documents need completion
* timezone and all-day storage semantics need an explicit decision

## Recommended next engineering batch

Before implementing Excel import:

1. introduce Alembic database migrations
2. complete `docs/schema_v1.md`
3. define timezone and all-day semantics
4. implement import tables

## Next product milestone

Excel import v1:

```text
upload Excel
-> store source document
-> create import batch
-> preserve raw rows
-> normalize rows
-> create candidate events
-> review candidates
-> approve selected candidates into events
```

## Immediate next task

Introduce Alembic database migrations for the existing `categories` and `events` tables.
