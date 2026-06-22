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
