# AI Calendar - Codex Instructions

## Project ownership

ChatGPT is used for product decisions, architecture, implementation design, and writing new scripts.

Codex is primarily used for implementation assistance, repository inspection, testing, repetitive work, and debugging.

Do not introduce major product, architecture, database-schema, or dependency changes unless the task explicitly requests them.

## Documentation authority

The Git repository is the canonical source for shared project documents. ChatGPT Project Sources hold exact synchronized mirrors of those canonical files.

When information conflicts, use this authority order:

1. Current implementation and Alembic migrations
2. `docs/decision_log.md`
3. `docs/project_status.md`
4. `docs/schema_v1.md`
5. `docs/mvp_v1_blueprint.md`
6. `docs/project_overview.md`
7. `README.md`

Inspect the implementation when documentation conflicts with it. Correct the affected document in the same task; do not silently follow stale documentation. Do not edit unrelated documents merely to refresh dates.

`Practical-Instructions.txt` is private to ChatGPT Project Sources. It must never be added to, cited by, or exported from this repository.

## Required context

Before modifying the repository:

1. Read `docs/project_status.md`.
2. Read `docs/mvp_v1_blueprint.md` when the task affects scope or product behavior.
3. Read `docs/schema_v1.md` when the task affects persistence or imports.
4. Run `git status`.
5. Inspect the relevant existing implementation before proposing changes.

## Implementation principles

* Prefer the smallest change that correctly completes the task.
* Preserve the standalone architecture.
* Keep the relational database as the application source of truth.
* Keep imported records reviewable before they become calendar events.
* Keep the project expandable without prematurely adding unnecessary complexity.
* Do not modify or commit real personal documents or runtime databases.
* Use synthetic fixtures for tests.
* Do not add production dependencies unless they are necessary and explicitly explained.
* Update affected documentation during the same task.

## Frontend

`frontend/` is the single editable source of truth for frontend files. FastAPI serves those files directly; do not add or maintain a second manually edited frontend copy.

## Verification

After changing Python code, run the relevant tests and at minimum:

```powershell
python -m compileall backend\app
```

After changing frontend behavior, start the application and verify the affected interaction manually.

## Documentation synchronization

After completing a meaningful task:

* update `docs/project_status.md`
* update `docs/decision_log.md` only when an important decision was made
* include verification results and any unresolved issue
* keep `project_status.md` concise and current rather than using it as a detailed changelog
* refresh the Project Sources export when shared documentation changes

## Git safety

Do not commit or push unless the task explicitly requests it.

Before handing work back, report:

* files changed
* behavior implemented or fixed
* checks performed
* unresolved issues
* recommended next action
* whether the work is ready to commit
* one suggested conventional commit message
* which ChatGPT Project Source files need replacement
