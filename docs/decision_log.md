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