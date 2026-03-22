# AI Calendar — MVP v1 Blueprint

## 1. Project purpose
AI Calendar is a standalone personal calendar application for laptop and phone.
Its first goal is to solve a real personal scheduling problem:
bringing structured schedules from PDF and Excel files into one unified calendar,
while also supporting fast manual event entry.

## 2. Core product principles
- Standalone first: no dependency on Google Calendar as the main engine.
- Solve the real problem first: import schedules and add events manually.
- Expandable architecture: future features must fit without redesigning the whole system.
- Human review before save: imported rows become candidate events first.
- Relational database as source of truth.

## 3. MVP scope
### Included
- day / week / month calendar view
- manual event creation
- event editing
- event deletion
- categories: Uni, Work, Other
- Excel upload and parsing
- PDF table upload and parsing
- candidate event review page
- approve candidate events into real calendar events
- duplicate warning
- conflict warning
- source tracking

### Excluded
- voice input/output
- chat assistant
- automatic scheduling agent
- external calendar sync
- collaboration
- advanced recurrence
- knowledge graph as primary storage

## 4. Main user flows
### Flow A — Manual event
1. User opens calendar
2. User clicks a date or time slot
3. User fills event form
4. Event is saved directly into `events`
5. Event appears in the calendar

### Flow B — Excel/PDF import
1. User uploads file
2. File metadata is stored in `source_documents`
3. System creates `import_batch`
4. Parser extracts rows
5. Rows become `candidate_events`
6. User reviews and edits candidates
7. Approved candidates become `events`

## 5. Internal pipeline
input source -> normalized row -> candidate event -> review -> approved event

## 6. Database v1
### Required tables
- events
- categories
- source_documents
- import_batches
- candidate_events

### Strongly recommended optional table
- import_rows

## 7. Recommended table responsibilities
### categories
Stores event categories such as Uni, Work, Other.

### source_documents
Stores uploaded file metadata and file identity.

### import_batches
Stores one parsing/import attempt for a source document.

### candidate_events
Stores extracted event candidates before approval.

### events
Stores approved real calendar events.

### import_rows
Stores raw extracted rows before interpretation, useful for debugging and future parser upgrades.

## 8. First technical milestone
The first working demo is:
- open app
- manually create one event
- save to SQLite
- fetch events by date range
- show them in a simple calendar/list view

## 9. First implementation order
1. Define schema v1
2. Create FastAPI + SQLite starter backend
3. Implement categories and event CRUD
4. Build minimal responsive UI
5. Add Excel import
6. Add PDF table import
7. Add candidate review flow

## 10. Storage policy
### Stored in Git
- code
- docs
- schema
- sample test files
- fixtures

### Not stored in Git
- runtime uploads
- local SQLite database
- logs
- cache
- personal real documents

## 11. Success criteria for MVP
The MVP is successful if:
- manual event entry is easy on laptop and phone
- Excel/PDF schedules can be converted into reviewable candidate events
- approved items become real events reliably
- the system stays modular enough for future AI features