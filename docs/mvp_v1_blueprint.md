# AI Calendar - MVP v1 Blueprint

## Purpose

AI Calendar is a standalone personal calendar for laptop and phone. It brings structured schedules from Excel and PDF files into one calendar while keeping manual event entry quick and dependable.

## Product principles

* Standalone first: the application owns its data, interface, and scheduling logic.
* Relational source of truth: the calendar database is authoritative.
* Human review: imported data stays reviewable before it becomes a real event.
* Incremental expansion: solve manual scheduling and structured import before AI assistance.

## Current starting slice

The implemented baseline supports categories, manual event CRUD, date-window queries, and a responsive selected-day or upcoming-events interface. It is intentionally not yet a full day, week, or month calendar.

## MVP target

### Manual calendar

* create, edit, delete, and filter events
* assign categories
* use the interface from laptop or phone
* provide day, week, and month calendar views

### Structured import

* upload Excel tables and table-like PDFs
* store source-document metadata and each import attempt
* preserve raw import rows where useful for traceability
* normalize rows into candidate events
* review, correct, approve, or reject candidates before creating real events
* warn about likely duplicates and conflicts

## Shared import pipeline

```text
input source -> normalized row -> candidate event -> review -> approved event
```

The pipeline is designed so later input types, including natural-language text, voice, email, or images, can enter through the same reviewable path without changing the calendar's source of truth.

## Data direction

The current schema contains `categories` and `events`. Import work will add `source_documents`, `import_batches`, `import_rows`, and `candidate_events` through migrations when that workflow begins. Detailed current fields and constraints belong in `docs/schema_v1.md` and Alembic migrations.

## Not in MVP

* external calendar synchronization
* collaboration or multi-user features
* advanced recurrence
* voice input/output
* conversational scheduling assistant
* automatic schedule optimization
* knowledge graph as primary storage

## Near-term implementation order

1. Define timezone and all-day semantics.
2. Add the import pipeline tables through Alembic.
3. Implement Excel import and candidate review.
4. Add PDF table import.
5. Add duplicate and conflict warnings.
