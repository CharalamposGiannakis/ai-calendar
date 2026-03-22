# AI Calendar

AI Calendar is a standalone personal calendar application designed for laptop and phone.

The goal is to create a calendar that is faster and more natural to use than standard calendar apps, especially when schedules already exist inside structured documents such as PDF and Excel files.

## MVP goals
- Manual event creation, editing, and deletion
- Categories such as Uni, Work, and Other
- Import from Excel tables into candidate calendar events
- Import from PDF tables into candidate calendar events
- Review and approve imported candidate events before saving

## Core design principles
- Standalone first
- Expandable architecture
- Relational database as source of truth
- Human review before imported events are saved

## Planned stack
- Backend: FastAPI
- Database: SQLite first, PostgreSQL later if needed
- Frontend: responsive web UI
- Future features: natural language input, voice input/output, AI-assisted scheduling

## Project status
Project setup and MVP blueprint completed.
Backend starter structure is the next step.