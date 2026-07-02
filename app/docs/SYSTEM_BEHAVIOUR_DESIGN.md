## Phase 3 — System Behavior Design (Final)## 
## 1. Core Booking Flow

   1. Receive BookingRequest (Vapi → FastAPI)
   2. Persist BookingRequest (idempotency safe)
   3. Resolve Patient Identity
   4. Resolve Doctor (if applicable)
   5. Fetch Schedule Data
   6. Compute Availability
   7. Detect Conflicts
   8. If valid → Create Appointment
   9. Update BookingRequest status
   10. Return outcome

------------------------------
## 2. Patient Resolution Rule

* Ownership: Patient Resolution Service
* Rules:
* Patient is identified using phone (primary key for real-world matching).
   * If patient exists → reuse.
   * If patient does NOT exist → create BEFORE appointment creation.
* Constraint: Patient creation is CONDITIONAL, not automatic per request. No patient = no booking continuation.

------------------------------
## 3. Doctor Resolution Rule

* Ownership: Booking Service (or dedicated Doctor Resolution logic)
* Rules:
* Doctor may be: specified, inferred (future extension), or null initially.
   * Must be resolved before availability check.

------------------------------
## 4. Availability Engine (Single Owner)

* Ownership: Availability Service ONLY
* Definition: Availability = Schedule Blocks − Existing Appointments
* Inputs: doctor_id, requested datetime range
* Outputs: available / unavailable, or suggested alternative slots
* Responsibilities:
* Fetch schedule blocks (via repository)
   * Fetch appointments in range (via repository)
   * Compute free slots
   * Suggest alternatives if needed

------------------------------
## 5. Conflict Detection Rule

* Ownership: Availability Service (pre-check)
* Database Role: Final enforcement only
* Logic:
* Check overlap before insert.
   * Prevent obvious invalid bookings.
   * DB still enforces constraint as final guard.

------------------------------
## 6. Booking Service (Orchestrator)

* Ownership: Booking Service
* Responsibilities:
* Coordinates entire workflow.
   * Calls: Patient Resolution Service, Availability Service.
   * Decides: whether appointment should be created, what response to return.
* Does NOT: compute availability, query raw schedules directly, bypass repositories.

------------------------------
## 7. Repository Contracts (Finalized)

* Clinic Repository
* find_by_id
   * find_by_name
* Doctor Repository
* find_by_id
   * find_by_clinic
   * find_by_specialty
* Patient Repository
* find_by_id
   * find_by_phone (CRITICAL)
   * find_by_email
   * find_by_clinic + phone
* Schedule Repository
* find_by_doctor_id
   * find_by_time_range
* Appointment Repository
* find_by_id
   * find_by_doctor_id + time_range (CRITICAL)
   * find_by_patient_id
   * create_appointment
   * update_status
* BookingRequest Repository
* create_request
   * find_by_id
   * find_by_idempotency_key (CRITICAL)
   * update_status

------------------------------
## 8. Ownership Matrix

| Action | Owner |
|---|---|
| Find patient | Patient Repository |
| Create patient | Patient Service |
| Resolve patient | Patient Resolution Service |
| Calculate availability | Availability Service |
| Detect conflicts | Availability Service |
| Enforce conflicts | Database |
| Create appointment | Booking Service |
| Persist appointment | Appointment Repository |

------------------------------
## 9. Failure Handling Rules

* No patient → create or reject workflow
* No doctor → suggest alternatives or reject
* No availability → suggest alternatives
* Schedule missing → system error fallback
* Conflict detected → retry or alternate slot
* Duplicate request → idempotent return
* DB failure → rollback + retry safe response

------------------------------
## 10. Core Architectural Truth (Important)

The system is NOT: a CRUD system, a database wrapper, or a REST API.
The system IS: a decision engine that produces valid appointments under constraints.
Everything else supports that.




