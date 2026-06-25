```markdown
# SYSTEM DESIGN & ARCHITECTURE — AI VOICE BOOKING SYSTEM (V3.1)

## 1. PRODUCT DEFINITION
We are building a **voice-driven AI appointment booking system** for clinics using **Vapi + FastAPI + PostgreSQL**.

### Core Objective
* Patients book appointments via phone calls.
* AI extracts intent (Vapi).
* Backend processes structured booking requests.
* System guarantees no double booking.
* Must maintain fast conversational response time.

---

## 2. SYSTEM BOUNDARIES

### 2.1 External Layer (Vapi)
Responsible for:
* Speech-to-intent conversion
* Conversation handling
* Sending structured booking requests to backend

### 2.2 Backend Layer (FastAPI)
Responsible for:
* Business logic execution
* Booking orchestration
* Validation rules
* Conflict handling
* Response generation

### 2.3 Data Layer (PostgreSQL)
Responsible for:
* Data persistence
* Constraint enforcement
* Source of truth for appointments
* Final authority on correctness

---

## 3. CORE DOMAIN MODEL (FINAL)

### 3.1 Overview

The system defines six core entities:
* **Clinic** — Tenant boundary
* **Doctor** — Practitioner within a clinic
* **Patient** — Client booking appointments
* **Schedule** — Doctor availability rules
* **Appointment** — Confirmed booking (final truth)
* **BookingRequest** — Intent capture + idempotency

**For detailed field specifications, constraints, and relationships, see Section 15 (Data Model Specification).**

### 3.2 Explicitly Rejected Entities
* ❌ Slot entity (schedule-based computation instead)
* ❌ Calendar entity (no pre-generation)
* ❌ Pre-generated availability tables (dynamic calculation)

---

## 4. CORE SYSTEM INVARIANT

### PRIMARY RULE
* **A doctor cannot have overlapping appointments.**

### Enforcement Strategy

#### 1. Database Level (FINAL AUTHORITY)
* Prevents overlapping inserts under concurrency.

#### 2. Service Level (UX OPTIMIZATION)
* Pre-checks schedule validity.
* Improves response clarity.
* *NOT* a guarantee.

---

## 5. CONCURRENCY MODEL

### Strategy
* **Optimistic concurrency** (speed-first system).

### Behavior
* Multiple booking requests may proceed simultaneously.
* No locking during availability checks.
* Conflicts resolved at database `INSERT` time.

### Outcome
* First valid insert wins.
* Others fail safely.
* System remains responsive under load.

---

## 6. BOOKING FLOW (FINAL)

```text
Vapi
  │
  ▼
FastAPI Endpoint
  │
  ▼
Idempotency Check (BookingRequest)
  │
  ▼
Schedule Validation (Service Layer)
  │
  ▼
Appointment INSERT Attempt (Repository)
  │
  ▼
Database Constraint Decision
  │
  ▼
Response Returned
  │
  ▼
Vapi communicates result to user

```

---

## 7. CONFLICT HANDLING STRATEGY

If booking fails due to conflict:

* System generates alternative available slots.
* Returns suggestions immediately.
* No blocking retries.
* No queueing system.

---

## 8. PRODUCTION SAFETY MODEL

### 9.1 Idempotency (CRITICAL)

Prevents duplicate bookings caused by:

* Vapi retries
* Network failures
* User repetition

### Strategy

* Generate `idempotency_key`.
* Store `BookingRequest`.
* Reuse result if request already processed.

---

## 9. API DESIGN (CURRENT STATE)


### 9.1 Health Check

`GET /health`

### 9.2 Booking Endpoint

`POST /appointments/book`

#### Request

```json
{
  "patient_name": "string",
  "phone": "string",
  "doctor_id": 1,
  "preferred_start_time": "datetime",
  "preferred_end_time": "datetime"
}

```

#### Response (Success)

```json
{
  "status": "CONFIRMED",
  "appointment_id": 123
}

```

#### Response (Failure)

```json
{
  "status": "FAILED",
  "reason": "SLOT_TAKEN",
  "suggestions": []
}

```

---

## 10. DATABASE DESIGN STRATEGY (UPDATED)

### 10.1 Core Principle

All primary entities use UUID as their primary key.

---

### 10.2 Why UUIDs

* Prevents ID collision across distributed systems
* Supports retry-heavy voice system (Vapi)
* Safe for idempotent booking flows
* Future-proof for multi-clinic SaaS scaling
* Avoids predictable sequential IDs in public APIs

---

### 10.3 Identifier Standard (NEW RULE)

All core entities **MUST use:**
* **UUID PRIMARY KEY**

---

### 10.4 Core Tables (UPDATED)

#### clinic
* `clinic_id` (UUID PK)
* `name`
* `created_at`

#### doctor
* `doctor_id` (UUID PK)
* `clinic_id` (UUID FK)
* `name`
* `specialty`
* `created_at`

#### patient
* `patient_id` (UUID PK)
* `clinic_id` (UUID FK)
* `name`
* `phone`
* `email`
* `created_at`

#### schedule
* `schedule_id` (UUID PK)
* `doctor_id` (UUID FK)
* `working_days`
* `start_time`
* `end_time`

#### appointment
* `appointment_id` (UUID PK)
* `clinic_id` (UUID FK)
* `doctor_id` (UUID FK)
* `patient_id` (UUID FK)
* `date`
* `start_time`
* `end_time`
* `status`
* `created_at`
* `updated_at`

#### booking_request
* `booking_request_id` (UUID PK)
* `idempotency_key` (string)
* `clinic_id` (UUID FK)
* `doctor_id` (UUID FK)
* `patient_name`
* `phone`
* `email`
* `requested_date`
* `requested_start_time`
* `requested_end_time`
* `status`
* `created_at`

---

### 10.5 Indexing Note (IMPORTANT ADDITION)

Even though UUIDs are used:
* Indexes should still be applied on:
  * `doctor_id`
  * `clinic_id`
  * `start_time` (appointments)
  * `idempotency_key` (booking_request)

---

### 10.6 Appointment Constraint (UNCHANGED BUT REAFFIRMED)

**No overlapping appointments per doctor is enforced at DB level.**

UUID choice does NOT affect this rule.

---

## 11. ARCHITECTURE LAYERS

### API Layer

* Request handling
* Validation
* Idempotency entry point

### Service Layer

* Booking orchestration
* Schedule validation
* Conflict resolution logic

### Repository Layer

* Database operations only

### Domain Layer

* Business rules definition
* Invariants

### Core Layer

* Config
* Database setup
* Shared utilities

### Production Safety Layer

* Idempotency handling
* Concurrency safety strategy

---

## 12. SYSTEM PHILOSOPHY (IMPORTANT)

### Core Principles

* Correctness enforced at database boundary.
* Speed preserved in user interaction layer.
* No slot pre-generation.
* No over-engineered scheduling system.
* Simple model first, extensible later.

---

## 13. DATA MODEL SPECIFICATION (UPDATED TO UUID STANDARD)

This section defines the **exact structure of all persistent domain entities**.

### GLOBAL RULE

**All entities now use:**
* `entity_id` (UUID PRIMARY KEY)

---

## 13.1 Clinic

### Purpose

Represents a tenant (medical practice boundary).

---

### Fields

```
clinic_id (UUID)
name
created_at
```

---

### Relationships

- Has many Doctors
- Has many Patients
- Has many Appointments

---

### Notes

- Minimal by design
- No operational clinic metadata included (MVP scope)

---

## 13.2 Doctor

### Purpose

Represents a practitioner within a clinic.

---

### Fields

```
doctor_id (UUID)
clinic_id (UUID)
name
specialty
created_at
```

---

### Relationships

- Belongs to Clinic
- Has many Appointments
- Has multiple Schedule entries

---

### Notes

- Schedule is NOT embedded here
- Availability is derived via Schedule entity

---

## 13.3 Patient

### Purpose

Represents a client booking appointments.

---

### Fields

```
patient_id (UUID)
clinic_id (UUID)
name
phone
email
created_at
```

---

### Relationships

- Belongs to Clinic
- Has many Appointments

---

### Notes

- Email included for future notifications
- Phone is primary booking channel (voice-first system)

---

## 13.4 Schedule

### Purpose

Defines doctor availability rules.

---

### Fields

```
schedule_id (UUID)
doctor_id (UUID)
working_days
start_time
end_time
```

---

### Relationships

- Belongs to Doctor

---

### Critical Design Decision

- A doctor can have **multiple schedule entries**
- Each entry represents an independent time block

Example:

- Mon–Fri 08:00–12:00
- Mon–Fri 13:00–17:00

---

### Notes

- No slot generation
- No calendar system
- Availability computed dynamically

---

## 13.5 Appointment

### Purpose

Represents a confirmed booking outcome.

---

### Fields

```
appointment_id (UUID)
clinic_id (UUID)
doctor_id (UUID)
patient_id (UUID)
start_time
end_time
status
created_at
updated_at
```

---

### Relationships

- Belongs to Clinic
- Belongs to Doctor
- Belongs to Patient

---

### Status Values

```
CONFIRMED
CANCELLED
COMPLETED
```

---

### Critical Rules

- Appointment does NOT validate availability
- Appointment does NOT enforce scheduling rules
- Appointment is a final state record only

---

### Notes

- Source of truth for booked time slots
- DB constraint enforces no overlap per doctor

---

## 13.6 BookingRequest

### Purpose

Captures incoming booking intent from Vapi.

---

### Fields

```
booking_request_id (UUID)
idempotency_key (string)
clinic_id (UUID)
doctor_id (UUID)
patient_name
phone
email
preferred_start_time
preferred_end_time
status
created_at
```

---

### Status Values

```
RECEIVED
PROCESSING
SUCCESS
FAILED
```

---

### Critical Role

- Prevents duplicate bookings via idempotency
- Tracks full lifecycle of voice-driven requests
- Handles retries safely

---

### Relationship Behavior

- May exist without an Appointment
- Acts as the "intent layer" of the system

---

## 14. CORE DATA MODEL PRINCIPLES (UPDATED)

---

### 14.1 Separation of Concerns

| Layer | Responsibility |
|-------|----------------|
| BookingRequest | Intent + idempotency |
| Schedule | Availability rules |
| Appointment | Final truth |
| Database | Conflict enforcement |

---

### 14.2 No Slot System

- No pre-generated slots
- No calendar table
- No availability cache

---

### 14.3 Schedule-Based Computation

Availability is always:

```
Schedule - Existing Appointments
```

---

### 14.4 Database is Final Authority

- Prevents overlapping appointments
- Handles concurrency correctness
- Rejects invalid writes

---

## 15. ARCHITECTURE STATUS

### COMPLETED

- Domain Model
- Data Model Specification
- Scheduling Strategy
- Booking Flow
- Concurrency Model
- API Design (initial)
- System Boundaries

---

## 16. FUTURE CONSIDERATIONS & DEVELOPMENT PHASE

### Completed

* Product definition
* System architecture
* Domain modeling
* Scheduling model
* Concurrency strategy
* Booking flow design
* API contracts (initial)
* Production safety design

### Next Phase (ACTIVE)

**IMPLEMENTATION START**

Focus:

* Project structure (done)
* Core infrastructure (db + config)
* SQLAlchemy models
* Repository layer
* Booking service implementation
* API endpoint integration

```

```

