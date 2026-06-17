```markdown
# SYSTEM DESIGN & ARCHITECTURE — AI VOICE BOOKING SYSTEM (V2.0)

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

### 3.1 Entities

#### Clinic
* Represents a tenant (medical practice).

#### Doctor
* Belongs to Clinic.
* Has Schedule.
* Has many Appointments.

#### Patient
* Belongs to Clinic.
* Has many Appointments.

#### Appointment (CORE ENTITY)
* Represents a confirmed booking.
* **Responsibilities:**
  * Stores final booked time.
  * Represents truth of system state.
  * *NOT* responsible for validation.

#### BookingRequest (TEMPORARY / AUDIT ENTITY)
* Represents:
  * Incoming request from Vapi.
  * Request tracking.
  * Idempotency control.

#### Schedule
* Defines doctor availability rules:
  * Working days
  * Working hours
  * Recurrence rules (simple weekly model)

### 3.2 Explicitly Rejected Entities
* ❌ Slot entity
* ❌ Calendar entity
* ❌ Pre-generated availability tables

---

## 4. SCHEDULING MODEL

### Approach
* Schedule-based availability (**NOT** slot-based).

### Schedule Structure
* `working_days` (Mon–Sun enum list)
* `start_time`
* `end_time`

### Availability Logic
$$\text{Availability} = \text{Schedule} - \text{Existing Appointments}$$

> ### Key Decision
> * Availability is **computed dynamically, never stored**.

---

## 5. CORE SYSTEM INVARIANT

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

## 6. CONCURRENCY MODEL

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

## 7. BOOKING FLOW (FINAL)

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

## 8. CONFLICT HANDLING STRATEGY

If booking fails due to conflict:

* System generates alternative available slots.
* Returns suggestions immediately.
* No blocking retries.
* No queueing system.

---

## 9. PRODUCTION SAFETY MODEL

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

## 10. DATABASE DESIGN STRATEGY

### 10.1 Core Tables

* `clinic`
* `doctor`
* `patient`
* `schedule`
* `appointment`
* `booking_request`

### 10.2 Appointment Constraint (CRITICAL)

* **No overlapping appointments per doctor.** This is enforced strictly at the DB level.

### 10.3 Design Philosophy

* DB is final truth.
* App layer does not “guarantee correctness”.
* App layer only improves UX.

---

## 11. API DESIGN (CURRENT STATE)

### 11.1 Health Check

`GET /health`

### 11.2 Booking Endpoint

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

## 12. ARCHITECTURE LAYERS

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

## 13. SYSTEM PHILOSOPHY (IMPORTANT)

### Core Principles

* Correctness enforced at database boundary.
* Speed preserved in user interaction layer.
* No slot pre-generation.
* No over-engineered scheduling system.
* Simple model first, extensible later.

---

## 14. FUTURE CONSIDERATIONS (NOT IMPLEMENTED YET)

These are intentionally deferred:

### 14.1 ScheduleException

Possible future addition:

* Doctor leave days
* Holidays
* Partial-day overrides

> *Reason deferred:* Increases scheduling complexity significantly; not required for MVP.

### 14.2 Slot System

* **Rejected for now:** Would introduce unnecessary state management complexity; not needed for dynamic scheduling model.

### 14.3 Multi-Clinic Scaling

Future design direction:

* Tenant isolation via `clinic_id`.
* Same backend supports multiple clinics.

---

## 15. CURRENT DEVELOPMENT PHASE

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