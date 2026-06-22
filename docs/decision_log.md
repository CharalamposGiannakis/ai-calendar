# Decision Log

## 2026-06-19 — Relational database as primary storage

**Decision:** Use SQLite initially, with a later path to PostgreSQL.

**Reason:** Calendar event CRUD, filtering, document imports, and transactional approval workflows fit a relational model better than a knowledge-graph-first design.

**Future option:** A knowledge graph may be added as an auxiliary semantic layer.

---

## 2026-06-19 — Standalone calendar

**Decision:** AI Calendar owns its interface, data, and scheduling logic rather than using Google Calendar as its primary engine.

**Reason:** Full product control and long-term expandability.

---

## 2026-06-19 — Frontend source of truth

**Decision:** `frontend/` is the editable frontend source of truth.

**Reason:** Maintaining independent copies in `frontend/` and `backend/app/static/` creates synchronization risk.

---

## 2026-06-19 — Alembic as schema source of truth

**Decision:** Use Alembic migrations as the versioned schema source of truth for the SQLite database.

**Reason:** Runtime `create_all()` hides schema changes and cannot safely evolve existing user data. Migrations make schema changes explicit, reviewable, testable, and adoptable for the existing development database.

**Operational note:** Fresh databases are migrated with `alembic upgrade head`. The existing development database has been backed up, validated, and stamped at revision `20260619_0001`. Any legacy database with application tables but no Alembic revision must use `scripts/adopt_existing_database.ps1` before normal startup.

---

## 2026-06-23 - Explicit event time and all-day semantics

**Decision:** The application default timezone is the IANA zone `Europe/Amsterdam`; a fixed UTC offset is not used. Timed events are exact instants, normalized to UTC before persistence, while SQLite stores their UTC values as timezone-naive datetimes. Timed events retain the original IANA `timezone_name` and API responses expose UTC offsets.

**Input and DST policy:** A naive timed API value is accepted only with a valid IANA `timezone_name`. Ambiguous autumn DST times and nonexistent spring DST times are rejected for manual events rather than silently choosing an offset. There is no timezone settings table or selector yet.

**All-day policy:** All-day events are date ranges with an exclusive `end_date`; they have no timed datetime or timezone fields. Timed and all-day overlap use half-open intervals: `[start, end)`.

**Migration policy:** Existing naive timed values are interpreted as Amsterdam local wall-clock values and converted to UTC. Existing all-day `00:00:00` through `23:59:59` rows become exclusive date ranges. Migration aborts with an event ID if a legacy timed value cannot be represented safely.

---

## 2026-06-23 - Import pipeline foundation

**Decision:** Record import provenance in relational tables before implementing file uploads or parsers. Uploaded files will live on disk later while their metadata, batches, raw rows, and reviewable candidate events live in SQLite.

**Reason:** The foundation preserves raw extracted data and makes future candidate approval traceable and transactional without treating parser output as calendar events prematurely.

**Provenance:** An approved event can reference one candidate event through nullable unique `events.candidate_event_id`; provenance then follows candidate, import row, batch, and source document. Duplicate/conflict flags and confidence scores remain dynamic future behavior rather than stored fields.
