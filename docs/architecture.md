# AI Calendar - Architecture

AI Calendar is a standalone FastAPI application that serves a vanilla HTML/CSS/JavaScript frontend and a local API from one server. SQLite is the current relational source of truth, with schema changes managed through Alembic migrations.

## Runtime Shape

```text
browser on laptop/phone
        |
        v
FastAPI server
  |-- frontend/ static files
  |-- category and event API
  |-- import API
        |
        v
SQLite database + local storage/uploads/runtime files
```

## Review-First Import Pipeline

```text
source document
    -> import batch
    -> raw import row
    -> candidate event
    -> duplicate/conflict warnings
    -> user review
    -> approved calendar event
```

Imported data does not become a real calendar event until the user approves a candidate. This preserves traceability from an approved event back through its candidate, raw row, import batch, and source document.

## Current Boundaries

* `frontend/` is the single editable frontend source.
* `backend/app/` contains the FastAPI application, SQLAlchemy models, routers, import services, and time utilities.
* `backend/alembic/` contains versioned schema migrations.
* `tests/integration/` uses temporary SQLite databases and synthetic files.
* `storage/` is runtime data and should not contain committed personal documents.
