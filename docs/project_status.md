# AI Calendar - Current Project Status

**Last updated:** 10 July 2026
**Current phase:** Manual-calendar vertical slice with frontend import warning display

## Implemented

### Events and time semantics

* FastAPI category and event CRUD API
* explicit `Europe/Amsterdam` default timezone
* UTC-normalized timed events with retained IANA timezone names
* date-only all-day events with exclusive end dates
* DST ambiguity/nonexistence rejection for manual timed input
* half-open overlap filtering for timed and all-day events
* timed-to-all-day and all-day-to-timed updates

### Data and import foundation

* SQLite persistence through SQLAlchemy and Alembic
* migrations `20260619_0001`, `20260623_0002`, and `20260623_0003`
* `categories`, `events`, `source_documents`, `import_batches`, `import_rows`, and `candidate_events` tables
* nullable unique event-to-candidate provenance link
* safe `.xlsx` upload endpoint that stores files under `storage/uploads/runtime`
* source-document metadata creation with SHA-256 checksums and relative storage paths
* pending import-batch creation for each accepted upload
* Excel raw-row extraction into `import_rows` using `openpyxl`
* compact JSON preservation of non-empty Excel rows with source worksheet/row locators
* deterministic Excel candidate generation from extracted rows using header aliases
* pending `candidate_events` creation with row-level provenance and category-name matching
* backend candidate fetch, edit, reject, and transactional approval endpoints
* approved import candidates create real `events` with `source_type = import`
* dynamic backend duplicate and conflict warnings for import candidates against active events
* seeded Uni, Work, and Other categories

### Frontend and runtime

* `frontend/` remains the single editable frontend source
* one FastAPI server serves frontend and API for laptop and phone use
* timed event forms use Amsterdam local inputs; all-day forms use an inclusive Last Day field
* minimal Excel import-review UI for upload, row extraction, candidate generation, candidate editing, rejection, and approval
* frontend duplicate and conflict warning display on import candidate cards
* `scripts/run_app.ps1` migrates the configured database before Uvicorn starts

## Verification completed

* 81 isolated integration tests pass, covering API time semantics, DST behavior, upload storage, Excel raw-row extraction, Excel candidate generation, candidate review/approval, import candidate warnings, import metadata creation, migration conversion, constraints, and import-schema downgrade
* Alembic upgrade, check, and downgrade pass on temporary SQLite databases
* a disposable copy of the development database upgraded to `20260623_0003` with 5 retained events: 3 all-day, 2 timed, and 5 valid time shapes
* Python compilation and frontend single-source checks pass

## Current limitations

* no PDF parsing
* no AI/NLP agent, LLM parsing, or conversational scheduling assistant yet
* no timezone selector or user settings table
* day, week, and month calendar views are not implemented

## Immediate next task

Add PDF table import on the existing review-first import pipeline.
