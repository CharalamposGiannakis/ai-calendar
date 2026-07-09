# AI Calendar - Contributor and Agent Instructions

## Project Principles

AI Calendar is a standalone personal calendar with a review-first import pipeline. Keep the implementation dependable, local-first, and explicit about what is implemented today versus planned for later.

When working in this repository:

* prefer the smallest change that correctly completes the task;
* preserve the standalone architecture;
* keep the relational database as the application source of truth;
* keep imported records reviewable before they become calendar events;
* avoid product, architecture, schema, or dependency changes unless the task calls for them;
* use synthetic data in tests and examples;
* never add real personal documents, runtime uploads, or local databases to the repository.

## Documentation Authority

The repository is the canonical source for project documentation. When documentation and implementation disagree, inspect the implementation and migrations first, then update the affected document as part of the same task.

Use this authority order when resolving conflicts:

1. Current implementation and Alembic migrations
2. `docs/decision_log.md`
3. `docs/project_status.md`
4. `docs/schema_v1.md`
5. `docs/mvp_v1_blueprint.md`
6. `docs/project_overview.md`
7. `README.md`

Update `docs/decision_log.md` only for genuine product or architecture decisions.

## Required Context Before Editing

Before modifying the repository:

1. Read `docs/project_status.md`.
2. Read `docs/mvp_v1_blueprint.md` when the task affects scope or product behavior.
3. Read `docs/schema_v1.md` when the task affects persistence or imports.
4. Run `git status`.
5. Inspect the relevant existing implementation before proposing or making changes.

## Frontend

`frontend/` is the single editable frontend source. FastAPI serves these files directly. Do not create or maintain a second manually edited frontend copy under `backend/app/static`.

After changing frontend behavior, verify the affected interaction manually when practical.

## Backend and Tests

After changing Python code, run the relevant tests and at minimum:

```powershell
python -m compileall backend\app
```

Prefer the isolated integration tests for API behavior:

```powershell
python -m pytest tests\integration
```

Tests should use temporary SQLite databases and synthetic files. They must not depend on the development database or real runtime uploads.

## Documentation Updates

After a meaningful implementation or repository-hygiene task:

* update `docs/project_status.md` when current status changes;
* update README or other docs when public usage, setup, architecture, or scope changes;
* keep status notes concise rather than using them as a detailed changelog;
* avoid refreshing dates or rewriting unrelated sections.

## Git Safety

Do not commit or push unless explicitly asked. Before handing work back, report:

* files changed;
* behavior or documentation updated;
* checks performed;
* unresolved issues;
* whether the work is ready to commit;
* a suggested conventional commit message.
