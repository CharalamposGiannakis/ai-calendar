# Project Status — AI Calendar

## 1. Project identity
**Project name:** AI Calendar  
**GitHub repo:** `ai-calendar`  
**Local folder:** `C:\Projects\ai_calendar`

AI Calendar is a standalone personal calendar application for laptop and phone.  
It is designed to combine manual scheduling with structured document import, especially from PDF and Excel tables.

---

## 2. Current project goal
Build a first working MVP that covers real daily needs before advanced AI features.

### MVP priorities
- manual event creation
- event editing and deletion
- categories such as Uni, Work, Other
- Excel table import into candidate events
- PDF table import into candidate events
- review/approve flow before saving imported events

---

## 3. Main product principles
- Standalone first
- Relational database as source of truth
- Expandable architecture from day one
- Imported rows must be reviewed before becoming real events
- Solve personal real use cases first, then add advanced AI features later

---

## 4. Agreed system flow
`input source -> normalized row -> candidate event -> review -> approved event`

This flow should remain central even when future inputs are added, such as:
- voice
- natural language text
- email
- screenshots/images

---

## 5. Current database direction
### Core tables
- `events`
- `categories`
- `source_documents`
- `import_batches`
- `candidate_events`

### Strong optional table
- `import_rows`

### Table roles
- `events`: approved real calendar events
- `categories`: event grouping such as Uni, Work, Other
- `source_documents`: uploaded file metadata
- `import_batches`: one import/parsing attempt for one document
- `candidate_events`: extracted events waiting for approval
- `import_rows`: raw extracted rows before interpretation

---

## 6. Current folder structure
```text
ai_calendar/
├── README.md
├── .gitignore
├── docs/
│   ├── mvp_v1_blueprint.md
│   ├── architecture.md
│   ├── schema_v1.md
│   ├── roadmap.md
│   └── project_status.md
├── backend/
├── frontend/
├── storage/
│   ├── db/
│   ├── uploads/
│   │   ├── sample/
│   │   └── runtime/
│   ├── parsed/
│   └── exports/
├── tests/
│   ├── fixtures/
│   │   ├── sample_excel/
│   │   └── sample_pdf/
│   └── integration/
└── scripts/
````

---

## 7. Storage policy

### Stored in Git

* code
* documentation
* schema files
* small sample files
* test fixtures

### Not stored in Git

* runtime uploads
* local SQLite database
* logs
* cache
* real personal documents

---

## 8. What is already done

* project idea clarified
* standalone approach chosen
* database chosen over KG for MVP
* expandable architecture agreed
* MVP scope defined
* blueprint created
* local project moved outside OneDrive
* local Git repository reinitialized cleanly
* GitHub repo naming settled as `ai-calendar`

---

## 9. Current open decisions

* exact backend package structure inside `backend/`
* exact schema fields for version 1
* which calendar UI library to use later, if any
* whether `import_rows` should be included from the start

---

## 10. Current next step

**Next coding step:** FastAPI + SQLite backend starter

### First backend target

* create FastAPI app
* connect SQLite
* define initial models
* create `events` and `categories` CRUD
* make the first working demo:

  * create one manual event
  * save it
  * fetch it by date range

---

## 11. Near-term roadmap

### Step 1

FastAPI + SQLite starter

### Step 2

Manual event CRUD

### Step 3

Minimal responsive UI

### Step 4

Excel import pipeline

### Step 5

PDF table import pipeline

### Step 6

Candidate review and approval flow

---

## 12. Later features

Not part of MVP, but planned as future extensions:

* voice input
* voice output
* natural language commands
* AI scheduling assistant
* reminders
* recurrence
* semantic/KG layer
* external calendar sync

---

## 13. Development rule

The project should always prioritize:

1. correctness of the core calendar system
2. clean data flow
3. expandability
4. real usefulness for personal workflow

Advanced AI features should be added only after the manual event and import backbone is stable.

```

A small improvement: after this, update `README.md` so it matches the same wording and current state.
```
