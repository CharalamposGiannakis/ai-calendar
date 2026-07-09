# AI Calendar - Schema v1

## Authority and current head

Alembic migrations are authoritative. The current schema head is `20260623_0003`:

```text
20260619_0001 -> 20260623_0002 -> 20260623_0003
```

`20260623_0002` defines explicit event time semantics. `20260623_0003` adds the import-pipeline foundation tables. The application now has initial `.xlsx` upload storage, metadata creation, raw-row extraction, candidate generation, backend candidate review/approval, and dynamic candidate warnings.

## Shared time rules

* The application default timezone is the IANA zone `Europe/Amsterdam`.
* Timed events are exact instants. They are normalized to UTC before persistence; SQLite stores UTC values as timezone-naive datetimes, and application code restores them as aware UTC values.
* Timed events retain an IANA `timezone_name`. Naive API timed values require a valid timezone name; ambiguous and nonexistent local DST times are rejected.
* All-day events are date ranges. `start_date` is inclusive and `end_date` is exclusive.
* Timed and all-day intervals both use half-open overlap semantics: `[start, end)`.

## Categories

`categories` stores the reusable event categories.

| Column | Notes |
| --- | --- |
| `id` | Integer primary key, indexed. |
| `name` | Required unique string, indexed. |
| `color`, `description` | Optional display metadata. |
| `created_at`, `updated_at` | Required timestamp fields with database defaults. |

## Events

`events` stores manual and eventually approved imported events.

| Column | Notes |
| --- | --- |
| `id` | Integer primary key, indexed. |
| `title`, `description`, `location` | User-facing event details. |
| `all_day` | Required boolean selecting one valid event shape. |
| `start_datetime`, `end_datetime` | Nullable UTC database datetimes for timed events, indexed. |
| `start_date`, `end_date` | Nullable date-only values for all-day events; `end_date` is exclusive. |
| `timezone_name` | Required IANA zone for timed events and null for all-day events. |
| `category_id` | Nullable foreign key to `categories`; category deletion sets it to null. |
| `candidate_event_id` | Nullable unique foreign key to `candidate_events`. Manual events leave it null. |
| `source_type`, `status` | Required event state fields; manual API defaults are `manual` and `active`. |
| `created_at`, `updated_at` | Required timestamp fields with database defaults. |

Named checks require exactly one shape:

* timed: UTC `start_datetime` and `end_datetime`, `timezone_name`, no date-only values, and `end_datetime > start_datetime`;
* all-day: `start_date` and exclusive `end_date`, no timed values or timezone, and `end_date > start_date`.

## Import foundation

### Source documents

`source_documents` stores metadata for uploaded files on disk. The initial Excel upload route stores accepted files under the relative `uploads/runtime/` path prefix and records one source document per upload.

* required original filename, unique relative `storage_path`, file type, non-negative byte size, and indexed SHA-256 checksum;
* optional MIME type;
* checksum is intentionally not unique, so legitimate re-uploads remain possible;
* a check rejects absolute-style storage paths.

### Import batches and rows

`import_batches` represents one import attempt for a source document. Initial uploads create a linked batch with status `pending`; raw Excel row extraction moves the batch to `processing` because candidate generation has not happened yet. Later parsing and review work can move batches through `ready_for_review`, `completed`, or `failed`. Row and candidate counters are non-negative.

`import_rows` preserves raw extracted material. For Excel extraction, each non-empty row from the first visible worksheet is stored with the real Excel row number, compact JSON row values in `raw_text` and `raw_data_json`, a compact JSON worksheet/row locator in `source_locator_json`, and parse status `parsed`. Its parse statuses are `pending`, `parsed`, `skipped`, and `failed`, and `(import_batch_id, row_index)` is unique.

### Candidate events

`candidate_events` is the reviewable interpretation of an import row. It references both its batch and raw row, uses the same timed/all-day shape and ordering checks as `events`, and has review statuses `pending`, `approved`, and `rejected`. It may reference a category with `ON DELETE SET NULL`.

Excel candidate generation treats the first extracted row as headers, maps flexible header aliases, and creates pending candidates from subsequent valid rows. Timed candidates are normalized to UTC with the supplied timezone or `Europe/Amsterdam`; all-day candidates use inclusive source dates converted to exclusive internal `end_date` values. Matching category names are resolved case-insensitively; unknown categories leave `category_id` null. Invalid data rows are marked failed while valid rows can still produce candidates. A batch with generated candidates moves to `ready_for_review`.

Pending candidates can be edited with the same timed/all-day validation rules, rejected, or approved. Approval creates one real `events` row with `source_type = import`, `status = active`, and `candidate_event_id` pointing back to the approved candidate, then marks the candidate `approved`. Rejection creates no event. If every candidate in a batch is approved or rejected, the batch moves to `completed`.

Candidate duplicate and conflict warnings are computed dynamically when candidates are fetched or listed. They are not stored in the schema. Warnings compare candidates to existing active events using the same half-open timed and all-day interval semantics, including mixed timed/all-day overlap checks.

Import provenance is restrictive by default: source documents, batches, rows, and candidates do not silently cascade away. An approved event remains traceable through:

```text
event -> candidate_event -> import_row -> import_batch -> source_document
```

## Indexes and migration workflow

Event start/end indexes support timed overlap queries. Import foreign keys are indexed where they are used for traversal; source-document checksums are indexed; event candidate provenance is unique.

Use `scripts/run_app.ps1` for ordinary startup. It upgrades the configured database to the Alembic head. New schema work requires a new migration and matching model/test/document changes. The legacy pre-Alembic adoption script remains only for databases without an Alembic revision.
