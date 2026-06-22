# AI Calendar - Schema v1

## Authority and scope

The current persisted schema is defined by Alembic revision `20260619_0001` in `backend/alembic/versions/20260619_0001_initial_categories_events.py`. This document describes that implemented schema; migrations remain authoritative.

The current database contains only `categories` and `events`. Import tables are planned but intentionally do not exist yet.

## Categories

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes | Primary key. |
| `name` | string (100) | yes | Unique, indexed category name. |
| `color` | string (20) | no | Display color. |
| `description` | text | no | Optional category description. |
| `created_at` | datetime | yes | Database default: `CURRENT_TIMESTAMP`. |
| `updated_at` | datetime | yes | Database default: `CURRENT_TIMESTAMP`. |

The application seeds `Uni`, `Work`, and `Other` when it starts against a migrated database.

## Events

| Column | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes | Primary key. |
| `title` | string (200) | yes | Event title. |
| `description` | text | no | Optional event description. |
| `start_datetime` | datetime | yes | Indexed event start. |
| `end_datetime` | datetime | yes | Indexed event end. |
| `all_day` | boolean | yes | Marks an all-day event. |
| `location` | string (200) | no | Optional location. |
| `category_id` | integer | no | References `categories.id`; deletion sets this value to null. |
| `source_type` | string (50) | yes | API default is `manual`. |
| `status` | string (50) | yes | API default is `active`. |
| `created_at` | datetime | yes | Database default: `CURRENT_TIMESTAMP`. |
| `updated_at` | datetime | yes | Database default: `CURRENT_TIMESTAMP`. |

The API requires `end_datetime` to be later than `start_datetime` and rejects a non-existent `category_id`. These are application-level validations; the initial SQLite migration does not add a database check constraint for event duration.

## Relationships and indexes

* One category can have many events.
* `events.category_id` is a nullable foreign key to `categories.id` with `ON DELETE SET NULL`.
* `categories.name` has a unique index.
* Event indexes support event identity and start/end date-window filtering.

## Time semantics

`start_datetime` and `end_datetime` are stored as timezone-naive SQLite datetime values in the initial migration. The intended user timezone and the exact semantics of all-day events have not yet been decided. Do not infer UTC conversion or cross-timezone behavior from the current implementation.

## Migration workflow

Use `scripts/run_app.ps1` for ordinary startup; it runs `alembic upgrade head` before Uvicorn. New schema changes require an Alembic migration and matching model updates. A pre-Alembic database containing existing application tables must first be backed up, validated, and stamped with `scripts/adopt_existing_database.ps1`.

## Planned import entities

The next schema batch will introduce `source_documents`, `import_batches`, `import_rows`, and `candidate_events`. These will support the review-first import pipeline defined in the MVP blueprint. Their fields and relationships should be decided when the import workflow is designed, then recorded in a migration and this document.
