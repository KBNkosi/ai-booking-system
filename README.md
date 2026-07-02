# AI Voice Booking System

A **voice-driven AI appointment booking backend** built for clinics. Patients call in, an AI voice agent (Vapi) extracts their intent, and this backend handles the full booking lifecycle — patient resolution, doctor lookup, availability checking, conflict detection, and appointment creation — with production-grade safety guarantees.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Voice Agent | Vapi *(future integration)* |
| Runtime | Python 3.13+ |
| Package Manager | uv |

---

## Core Booking Flow

```
Vapi (Voice AI)
    │
    ▼
FastAPI Endpoint
    │
    ▼
Idempotency Check  ──── Already processed? → Return cached result
    │
    ▼
Patient Resolution  ──── Existing patient? → Lookup │ New patient? → Create
    │
    ▼
Doctor Resolution
    │
    ▼
Availability Check  (Schedule − Existing Appointments)
    │
    ▼
Appointment INSERT
    │
    ▼
Database Constraint Decision  ──── Conflict? → Return alternatives
    │
    ▼
Response → Vapi → Patient
```

---

## Architecture

The system is organized into strict, isolated layers. Each layer has a single responsibility and defined boundaries.

```
app/
├── core/          # Config, database engine, session factory
├── models/        # SQLAlchemy domain models (schema definitions)
├── repositories/  # Data access layer (reads and writes only)
├── schemas/       # Pydantic request/response schemas
├── docs/          # Architecture docs, design decisions, business rules
└── main.py        # FastAPI application entry point
```

### Layer Responsibilities

| Layer | Responsibility |
|---|---|
| **API Layer** | Request handling, validation, idempotency entry point |
| **Service Layer** | Booking orchestration, schedule validation, conflict resolution *(Phase 6)* |
| **Repository Layer** | Database operations only — no business logic |
| **Domain Layer** | Business rule definitions and invariants |
| **Core Layer** | Config, database setup, shared utilities |

---

## Domain Model

Six core entities model the system. No pre-generated slots. No calendar tables. Availability is computed dynamically.

### Clinic
Tenant boundary. Every doctor and patient belongs to a clinic.

### Doctor
Practitioner within a clinic. Has a specialty and one or more schedule entries.

### Patient
Identified by `phone + clinic_id`. Phone is the primary booking identifier in a voice-first system.

### Schedule
Defines a doctor's working hours as time blocks (e.g. `Mon–Fri 08:00–12:00`). A doctor may have multiple schedule entries. Availability is never pre-generated — it is always derived as:

```
Available = Schedule − Existing Appointments
```

### Appointment
The **final source of truth** for a confirmed booking. Does not validate availability. Does not enforce scheduling rules. That is the service layer's job. The database enforces the no-overlap constraint.

**Status values:** `CONFIRMED` | `CANCELLED` | `COMPLETED`

### BookingRequest
Captures the raw **intent** from Vapi before any processing occurs. Enables idempotency — if Vapi retries a request due to a network failure, the system detects the duplicate via `idempotency_key` and returns the original result without reprocessing.

**Status values:** `RECEIVED` | `PROCESSING` | `SUCCESS` | `FAILED`

---

## Repository Layer

Repositories are **pure data access components**. They retrieve and persist data. They contain no business logic, no availability calculations, no conflict detection, and no booking orchestration.

| Repository | Responsibility |
|---|---|
| `ClinicRepository` | Retrieve clinic records |
| `DoctorRepository` | Retrieve doctor records by ID, specialty, or clinic |
| `PatientRepository` | Retrieve and create patient records |
| `ScheduleRepository` | Retrieve doctor schedule blocks |
| `AppointmentRepository` | Retrieve and persist appointments, update status and time |
| `BookingRequestRepository` | Create and retrieve booking requests, update status |

---

## Key Design Decisions

### 1. No Slot System
Slots create duplicated state and synchronization issues. This system computes availability dynamically from schedule and appointment data at request time.

### 2. BookingRequest ≠ Appointment
A `BookingRequest` is an intent record. An `Appointment` is a confirmed state record. Separating them provides an audit trail, supports idempotency, and handles Vapi's retry behavior safely.

### 3. Database is the Final Authority
The core invariant — **a doctor cannot have overlapping appointments** — is enforced at the database constraint level. Application-level checks improve UX and provide better error messages, but the database is the only truly concurrency-safe enforcement point.

### 4. Optimistic Concurrency
No row-level locking. Multiple booking requests may proceed simultaneously. The first valid insert wins. Others receive conflict responses with alternative suggestions. This keeps response times low for a conversational voice system.

### 5. UUID Primary Keys
All entities use UUID primary keys. This prevents ID collision across distributed contexts, supports idempotent retry flows, and avoids exposing predictable sequential IDs in public APIs.

---

## Production Safety

### Idempotency
Every booking request carries an `idempotency_key`. Before any processing begins, the system checks whether this key already exists in the `booking_requests` table. If it does, the original result is returned immediately, preventing duplicate appointments from retries or network failures.

### Conflict Handling
When an appointment INSERT fails due to a database overlap constraint:
- The system generates alternative available time slots.
- Returns them immediately to Vapi.
- No blocking retries. No queuing.

---

## Project Status

| Phase | Description | Status |
|---|---|---|
| 1 | Foundation (project setup, config, DB engine) | ✅ Complete |
| 2 | Domain Modeling (SQLAlchemy models) | ✅ Complete |
| 3 | Database Initialization (Alembic migrations) | ✅ Complete |
| 4 | System Behavior Design (business rules, scheduling policy) | ✅ Complete |
| 5 | Repository Layer Implementation | ✅ Complete |
| 6 | Service Layer (Availability Service, Booking Orchestration) | 🔲 Next |
| 7 | API Endpoints | 🔲 Upcoming |
| 8 | Vapi Integration | 🔲 Upcoming |

---

## Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL
- [`uv`](https://docs.astral.sh/uv/) package manager

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-booking-project

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env and set your DATABASE_URL

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

---

## Documentation

Internal architecture and design documents are located in [`app/docs/`](app/docs/):

- [`AI_BOOKING_SYSTEM_DESIGN_AND_ARCHITECTURE.md`](app/docs/AI_BOOKING_SYSTEM_DESIGN_AND_ARCHITECTURE.md) — Full system design, data model specification, and architecture layers
- [`AI_Booking_SYSTEM_DECISIONS_LOG.md`](app/docs/AI_Booking_SYSTEM_DECISIONS_LOG.md) — Architectural decision records with rationale and tradeoffs
- [`BUSINESS_RULES_&_SCHEDULING_POLICY.md`](app/docs/BUSINESS_RULES_&_SCHEDULING_POLICY.md) — Business rules and scheduling policies
- [`SYSTEM_BEHAVIOUR_DESIGN.md`](app/docs/SYSTEM_BEHAVIOUR_DESIGN.md) — System behavior design and flow specifications
