# API Layer Blueprint — AI Voice Booking System

Practical implementation guide for exposing the existing service layer via FastAPI. Based on the current codebase as of Phase 6 (services implemented, API not yet built).

---

## Executive Summary

**Minimum viable API (2 endpoints + health):**

| Endpoint | Service |
|---|---|
| `POST /clinics/{clinic_id}/bookings` | `BookingService.process_booking` |
| `GET /clinics/{clinic_id}/doctors/{doctor_id}/availability` | `AvailabilityService.check_availability` |
| `GET /health` | Already in `main.py` |

**Do not expose:** `PatientResolutionService` — internal to `BookingService`; only runs after availability is confirmed.

**Optional supporting read:** `GET /clinics/{clinic_id}/doctors` uses `DoctorRepository.list_by_clinic` only (no service exists yet). Include if the client needs to discover doctors; otherwise clients pass known `doctor_id` UUIDs.

**Out of scope:** Cancellation, rescheduling, appointment updates — repository methods exist but no service wraps them.

---

## 1. Recommended API Endpoints

### Core (required)

| # | Endpoint | Method | Purpose |
|---|---|---|---|
| 1 | `/health` | `GET` | Liveness check (already implemented) |
| 2 | `/clinics/{clinic_id}/bookings` | `POST` | Create a booking (or idempotently replay a prior attempt) |
| 3 | `/clinics/{clinic_id}/doctors/{doctor_id}/availability` | `GET` | Pre-check whether a 30-minute slot is free; return alternatives if not |

### Optional supporting read (repository-only today)

| # | Endpoint | Method | Purpose |
|---|---|---|---|
| 4 | `/clinics/{clinic_id}/doctors` | `GET` | List doctors so a client can obtain required `doctor_id` values |

---

## 2. HTTP Methods

| Endpoint | Method | Rationale |
|---|---|---|
| `/health` | `GET` | Read-only probe |
| `/clinics/{clinic_id}/bookings` | `POST` | Creates `BookingRequest` + possibly `Appointment`; idempotent via header |
| `/clinics/{clinic_id}/doctors/{doctor_id}/availability` | `GET` | Read-only computation; no persistence |
| `/clinics/{clinic_id}/doctors` (optional) | `GET` | Read-only list |

---

## 3. Purpose of Each Endpoint

### `GET /health`

Already in `app/main.py`. No changes needed beyond keeping it mounted.

### `POST /clinics/{clinic_id}/bookings`

Primary orchestration entry point. Maps 1:1 to `BookingService.process_booking`.

Handles:

- Idempotent replay via `idempotency_key`
- Doctor existence check
- Availability check
- Conditional patient creation (`PatientResolutionService`)
- Appointment creation on success
- Alternative slot suggestions on failure

### `GET /clinics/{clinic_id}/doctors/{doctor_id}/availability`

Exposes `AvailabilityService.check_availability` for a “is this slot free?” step before the user commits to booking. Returns up to 3 alternative 30-minute slots when unavailable.

### `GET /clinics/{clinic_id}/doctors` (optional)

Lists doctors via `DoctorRepository.list_by_clinic`. Useful because doctor selection is required and there is no doctor-resolution service.

---

## 4. Request DTO / Pydantic Schemas

Create under `app/schemas/` (referenced in README but not yet present).

### `app/schemas/common.py`

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class TimeSlotSchema(BaseModel):
    start_time: datetime
    end_time: datetime

class ClinicPathParams(BaseModel):
    clinic_id: UUID
```

### `app/schemas/booking.py`

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TimeSlotSchema

class CreateBookingRequest(BaseModel):
    doctor_id: UUID
    patient_name: str = Field(..., min_length=1, max_length=200)
    patient_phone: str = Field(..., min_length=1, max_length=50)
    patient_email: str | None = Field(default=None, max_length=254)
    requested_start_time: datetime

class BookingRequestSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_request_id: UUID
    idempotency_key: str
    clinic_id: UUID
    doctor_id: UUID
    patient_name: str
    patient_phone: str
    patient_email: str | None
    requested_start_time: datetime
    status: Literal["RECEIVED", "PROCESSING", "SUCCESS", "FAILED"]
    appointment_id: UUID | None

class AppointmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    clinic_id: UUID
    doctor_id: UUID
    patient_id: UUID
    start_time: datetime
    end_time: datetime
    status: str

class BookingSuccessResponse(BaseModel):
    status: Literal["SUCCESS"]
    booking_request: BookingRequestSummary
    appointment: AppointmentSummary

class BookingFailureResponse(BaseModel):
    status: Literal["FAILED"]
    booking_request: BookingRequestSummary
    reason: Literal["DOCTOR_NOT_FOUND", "SLOT_UNAVAILABLE", "PREVIOUSLY_FAILED"]
    alternative_slots: list[TimeSlotSchema] = Field(default_factory=list)

BookingResponse = BookingSuccessResponse | BookingFailureResponse
```

**Header (not body):** `Idempotency-Key: <string>` — required on every booking POST. Matches the unique constraint on `booking_requests.idempotency_key`.

### `app/schemas/availability.py`

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.common import TimeSlotSchema

class AvailabilityQueryParams(BaseModel):
    requested_start_time: datetime

class AvailabilityAvailableResponse(BaseModel):
    is_available: Literal[True]
    requested_slot: TimeSlotSchema

class AvailabilityUnavailableResponse(BaseModel):
    is_available: Literal[False]
    requested_slot: TimeSlotSchema
    alternative_slots: list[TimeSlotSchema] = Field(default_factory=list)

AvailabilityResponse = AvailabilityAvailableResponse | AvailabilityUnavailableResponse
```

### `app/schemas/doctor.py` (optional)

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    clinic_id: UUID
    name: str
    specialty: str
    created_at: datetime
```

---

## 5. Response DTO / Pydantic Schemas

Map service dataclasses to API schemas in thin mapper functions (keep routers dumb).

### Booking mappers

`BookingResult` (from `BookingService`) → `BookingResponse`:

| Service outcome | HTTP | Response schema |
|---|---|---|
| `status == "SUCCESS"`, new booking | `201 Created` | `BookingSuccessResponse` |
| `status == "SUCCESS"`, idempotent replay | `200 OK` | `BookingSuccessResponse` |
| `status == "FAILED"`, doctor missing | `404 Not Found` | `BookingFailureResponse` with `reason=DOCTOR_NOT_FOUND` |
| `status == "FAILED"`, slot taken | `409 Conflict` | `BookingFailureResponse` with `reason=SLOT_UNAVAILABLE` + alternatives |
| `status == "FAILED"`, idempotent replay of prior failure | `409 Conflict` | `BookingFailureResponse` with `reason=PREVIOUSLY_FAILED` |

**Infer `reason` in the router/mapper** (service does not expose it today):

- Idempotent path with no alternatives → `PREVIOUSLY_FAILED`
- Non-idempotent path, `alternative_slots` non-empty → `SLOT_UNAVAILABLE`
- Non-idempotent path, no alternatives, doctor lookup failed → `DOCTOR_NOT_FOUND`

### Availability mappers

`AvailabilityResult` (from `AvailabilityService`) → `AvailabilityResponse`:

Always return `200 OK` with `is_available: true/false`. Convert `(start, end)` tuples to `TimeSlotSchema`.

---

## 6. Validation at the API Boundary

Validate here; do not duplicate business logic that already lives in services.

### Structural (Pydantic)

| Field | Rule |
|---|---|
| `clinic_id` (path) | Valid UUID |
| `doctor_id` | Valid UUID, required |
| `patient_name` | Non-empty string |
| `patient_phone` | Non-empty string |
| `patient_email` | Optional; if present, basic format check |
| `requested_start_time` | Required timezone-aware or normalize to UTC in deps |
| `Idempotency-Key` header | Non-empty string |

### Referential (before calling service)

| Check | How | Why |
|---|---|---|
| Clinic exists | `ClinicRepository.get_by_id(clinic_id)` → 404 | Path param must be valid tenant |
| Doctor exists | `DoctorRepository.get_by_id(doctor_id)` → 404 | Fail fast before booking |
| Doctor belongs to clinic | `doctor.clinic_id == clinic_id` → 404 | Prevents cross-clinic booking; **not enforced in service today** |

### Scheduling policy (business rules — not enforced in services yet)

From `BUSINESS_RULES_&_SCHEDULING_POLICY.md`, enforce at API until moved into service:

| Rule | Validation |
|---|---|
| C2 — no past bookings | `requested_start_time > now()` |
| C1 — 7-day window | `requested_start_time <= now() + 7 days` |
| A2 — 30-minute grid | `requested_start_time.minute % 30 == 0` and `second == 0`, `microsecond == 0` |
| A1 — fixed 30 minutes | Do **not** accept `end_time` from client; service computes it |

### Do NOT validate at API

| Concern | Owner |
|---|---|
| Overlap detection | `AvailabilityService` |
| Patient create vs reuse | `PatientResolutionService` (via `BookingService`) |
| Idempotent replay logic | `BookingService` |
| Alternative slot discovery | `AvailabilityService` |

---

## 7. Which Service Each Endpoint Calls

| Endpoint | Primary call | Secondary (API-only pre-checks) |
|---|---|---|
| `POST .../bookings` | `BookingService.process_booking(...)` | `ClinicRepository`, `DoctorRepository` for existence/scoping |
| `GET .../availability` | `AvailabilityService.check_availability(doctor_id, requested_start)` | Same clinic/doctor pre-checks |
| `GET .../doctors` (optional) | **No service** — `DoctorRepository.list_by_clinic(clinic_id)` until a thin read service is added |

### Dependency wiring (per request)

Each handler needs a DB session from `app/core/db.py` and wired services:

```
Session → Repositories → Services
  ├─ ScheduleRepository ─┐
  ├─ AppointmentRepository ─┴─→ AvailabilityService
  ├─ PatientRepository ─→ PatientResolutionService
  ├─ BookingRequestRepository ─┐
  ├─ DoctorRepository ───────────┴─→ BookingService
```

**Important implementation gap:** repositories call `flush()` but nothing commits. The API dependency should `commit()` on success and `rollback()` on exception after each mutating request.

---

## 8. Recommended FastAPI Router Structure

```python
# app/main.py
from fastapi import FastAPI
from app.api.routers import bookings, availability, doctors  # doctors optional

app = FastAPI(title="AI Booking System")

app.include_router(bookings.router, prefix="/clinics/{clinic_id}", tags=["bookings"])
app.include_router(availability.router, prefix="/clinics/{clinic_id}", tags=["availability"])
# app.include_router(doctors.router, prefix="/clinics/{clinic_id}", tags=["doctors"])

@app.get("/health")
def health():
    return {"status": "ok"}
```

```python
# app/api/routers/bookings.py
router = APIRouter()

@router.post("/bookings", response_model=BookingResponse, status_code=201)
def create_booking(
    clinic_id: UUID,
    body: CreateBookingRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    booking_service: BookingService = Depends(get_booking_service),
    ...
):
    ...
```

```python
# app/api/routers/availability.py
router = APIRouter()

@router.get(
    "/doctors/{doctor_id}/availability",
    response_model=AvailabilityResponse,
)
def check_availability(...):
    ...
```

Keep routers thin: validate → pre-check → call service → map result → set HTTP status → commit/rollback.

---

## 9. Recommended File Structure

```
app/
├── api/
│   ├── __init__.py
│   ├── deps.py              # get_db, get_booking_service, get_availability_service
│   ├── mappers/
│   │   ├── __init__.py
│   │   ├── booking.py       # BookingResult → BookingResponse + reason inference
│   │   └── availability.py  # AvailabilityResult → AvailabilityResponse
│   └── routers/
│       ├── __init__.py
│       ├── bookings.py
│       ├── availability.py
│       └── doctors.py       # optional
├── schemas/
│   ├── __init__.py
│   ├── common.py
│   ├── booking.py
│   ├── availability.py
│   └── doctor.py            # optional
├── core/                    # existing
├── models/                  # existing
├── repositories/            # existing
├── services/                # existing
└── main.py                  # mount routers
```

`deps.py` is the single place for service construction — mirrors existing constructor signatures exactly.

---

## 10. Suggested Implementation Order

1. **`app/schemas/`** — Define all request/response models first; they document the contract.
2. **`app/api/deps.py`** — `get_db` with commit/rollback wrapper; factory functions for repositories and services.
3. **`app/api/mappers/`** — Pure functions converting ORM/dataclass → Pydantic (especially `alternative_slots` tuples → `TimeSlotSchema`).
4. **Availability router** — Simplest endpoint; no DB writes; good first integration test of deps + mappers.
5. **Booking router** — Core value; wire `Idempotency-Key` header; implement HTTP status mapping and failure-reason inference.
6. **Clinic/doctor pre-check helper** — Shared dependency used by both routers.
7. **Scheduling policy validators** — Pydantic `@field_validator` or a small `validators/scheduling.py` module for past/7-day/grid rules.
8. **Mount routers in `main.py`** — Replace bare `FastAPI()` setup.
9. **Optional doctors router** — Only if clients need discovery; consider a thin `DoctorQueryService` wrapper over `DoctorRepository.list_by_clinic` to stay consistent with “handlers delegate to services.”
10. **Manual smoke test** — Seed clinic/doctor/schedule via DB, then exercise availability → booking → idempotent replay.

---

## Alignment Notes with Existing Code

| Topic | Current state | API implication |
|---|---|---|
| Design doc path `POST /appointments/book` | Outdated (used int IDs, `preferred_end_time`) | Prefer clinic-scoped paths above; they match current service signatures |
| `PatientResolutionService` | Internal only | Never expose as its own endpoint |
| Failure reasons | All return `status="FAILED"` | API mapper must derive `reason` |
| Doctor-clinic scoping | Not checked in `BookingService` | Add at API pre-check |
| Past / 7-day / grid rules | Documented but not in services | Enforce at API boundary for MVP |
| `schemas/` folder | Referenced in README, not created | First thing to build |

---

## Example Request / Response Shapes

### Check availability

```http
GET /clinics/{clinic_id}/doctors/{doctor_id}/availability?requested_start_time=2026-07-10T09:00:00Z
```

### Create booking

```http
POST /clinics/{clinic_id}/bookings
Idempotency-Key: vapi-call-abc123
Content-Type: application/json

{
  "doctor_id": "...",
  "patient_name": "Jane Doe",
  "patient_phone": "+15551234567",
  "patient_email": "jane@example.com",
  "requested_start_time": "2026-07-10T09:00:00Z"
}
```

### Success (201 or 200 on replay)

```json
{
  "status": "SUCCESS",
  "booking_request": { "...": "..." },
  "appointment": {
    "appointment_id": "...",
    "start_time": "2026-07-10T09:00:00Z",
    "end_time": "2026-07-10T09:30:00Z",
    "status": "CONFIRMED"
  }
}
```

### Conflict (409)

```json
{
  "status": "FAILED",
  "booking_request": { "...": "..." },
  "reason": "SLOT_UNAVAILABLE",
  "alternative_slots": [
    { "start_time": "...", "end_time": "..." }
  ]
}
```

---

## Related Documentation

- [`AI_BOOKING_SYSTEM_DESIGN_AND_ARCHITECTURE.md`](AI_BOOKING_SYSTEM_DESIGN_AND_ARCHITECTURE.md) — Full system design and data model
- [`SYSTEM_BEHAVIOUR_DESIGN.md`](SYSTEM_BEHAVIOUR_DESIGN.md) — Service ownership and booking flow
- [`BUSINESS_RULES_&_SCHEDULING_POLICY.md`](BUSINESS_RULES_&_SCHEDULING_POLICY.md) — Scheduling validation rules
- [`AI_Booking_SYSTEM_DECISIONS_LOG.md`](AI_Booking_SYSTEM_DECISIONS_LOG.md) — Architectural decisions
