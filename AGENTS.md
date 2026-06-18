# AI Calendar — Codex Instructions

## Project ownership

ChatGPT is used for product decisions, architecture, implementation design, and writing new scripts.

Codex is primarily used for implementation assistance, repository inspection, testing, repetitive work, and debugging.

Do not introduce major product, architecture, database-schema, or dependency changes unless the task explicitly requests them.

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

## Frontend

`frontend/` should become the single editable source of truth for frontend files.

Avoid maintaining two independently edited copies of the frontend.

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

## Git safety

Do not commit or push unless the task explicitly requests it.

Before handing work back, report:

* files changed
* behavior implemented or fixed
* checks performed
* unresolved issues
* recommended next action
