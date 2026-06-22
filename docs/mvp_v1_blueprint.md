# AI Calendar - MVP v1 Blueprint

## Purpose

AI Calendar is a standalone personal calendar for laptop and phone. It combines reliable manual scheduling with a review-first workflow for bringing structured Excel and PDF schedules into one owned calendar.

## Product principles

* Standalone first: the application owns its data, interface, and scheduling behavior.
* Relational source of truth: events and import provenance live in the database.
* Human review: imported rows remain candidates before they become real calendar events.
* Correct calendar semantics: timed events are UTC-backed instants, and all-day events are exclusive date ranges.
* Incremental expansion: complete the import flow before advanced AI assistance.

## Current starting slice

The implemented foundation includes categories, manual event CRUD, explicit Amsterdam/UTC time handling, date-only all-day events, DST validation, half-open filtering, and a responsive selected-day or upcoming-events interface.

The database now includes the import foundation: source documents, import batches, raw import rows, candidate events, and event-to-candidate provenance. No upload, parser, candidate-review, or approval workflow exists yet.

## MVP target

### Manual calendar

* create, edit, delete, and filter timed and all-day events
* assign categories
* use the interface from laptop or phone
* provide day, week, and month calendar views

### Structured import

* safely store uploaded Excel tables and table-like PDFs
* create a source document and import batch
* preserve raw rows and normalize them into candidate events
* review, correct, approve, or reject candidates before creating real events
* warn dynamically about likely duplicates and conflicts

## Shared import pipeline

```text
source document -> import batch -> raw row -> candidate event -> review -> calendar event
```

## Not in MVP

* external calendar synchronization
* collaboration or multi-user features
* advanced recurrence
* voice input/output
* conversational scheduling assistant
* automatic schedule optimization
* knowledge graph as primary storage

## Near-term implementation order

1. Implement safe Excel upload storage and source-document creation.
2. Create import batches, preserve raw rows, and generate reviewable candidates.
3. Add candidate review and transactional approval into events.
4. Add PDF table import.
5. Add duplicate and conflict warnings.
