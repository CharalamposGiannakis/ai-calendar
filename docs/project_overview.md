# AI Calendar - Project Overview

## Vision

AI Calendar is a standalone personal calendar designed to work comfortably on a laptop and phone. It aims to turn structured schedules into reliable calendar events while keeping everyday manual scheduling fast and local.

## Problem

Schedules often arrive in Excel sheets and PDFs, where they are difficult to review alongside ordinary personal events. Copying them into a calendar manually is repetitive and error-prone. AI Calendar brings those sources into one owned calendar without depending on an external calendar provider as its primary engine.

## Core concept

Manual events are stored directly in the calendar. Imported information follows a review-first path:

```text
source document -> normalized row -> candidate event -> user review -> calendar event
```

This keeps the database authoritative and makes imported information traceable before it affects the real schedule.

## Design principles

* Standalone first, with local ownership of data and application behavior.
* Relational storage as the primary source of truth.
* Human approval before imported data becomes a calendar event.
* A small, dependable manual-calendar core before advanced automation.
* Modular growth without committing early to unnecessary platforms or AI layers.

## High-level modules

* **Calendar interface:** responsive event viewing and manual scheduling.
* **Calendar API:** categories, events, validation, filtering, and future approval workflows.
* **Persistence:** SQLite today, versioned through Alembic migrations, with a future path to another relational database if needed.
* **Import pipeline:** document storage, parsing, normalization, candidate creation, and review.
* **Future assistance:** natural-language, voice, reminders, conflict-aware suggestions, and semantic enrichment can build on the same reviewed event pipeline.

## MVP direction

The working foundation is the manual-calendar vertical slice: categories, event CRUD, a responsive browser interface, and a one-server local-network setup. The MVP grows next through Excel and PDF import, candidate review, and approval into the same calendar database.

## Future expansion

Later capabilities may include richer calendar views, recurrence, reminders, natural-language input, voice interaction, conflict resolution, travel-time support, and optional semantic reasoning. These are extensions to the calendar and import foundation, not replacements for it.
