## Phase 4 — Business Rules & Scheduling Policies (Final Locked Spec)## 1. Appointment Structure Rules## A1 — Appointment Duration (STRICT)

* Rule: All appointments have a fixed duration.
* Configuration: Duration is defined per clinic configuration (not per patient, not per request).
* Assumption: Uniform duration across all appointments unless explicitly extended in future versions.
* Core Constraint:

No variable-length appointments in MVP


## A2 — Time Granularity (STRICT GRID SYSTEM)

* Rule: Scheduling operates on a fixed time grid.
* Example: 15 or 30-minute intervals (clinic-defined).
* Core Constraint:

All appointment start times MUST align to grid boundaries

* Consequences:
* No arbitrary start times.
   * No mid-grid bookings.

## A3 — Overlap Definition (STRICT)

* Rule: Two appointments conflict if any time interval overlaps EVEN PARTIALLY.
* Formal Formula: A.start < B.end AND A.end > B.start
* Buffers: Optional buffer time (e.g., 5–10 minutes) is treated as part of the appointment duration.
* Core Constraint:

End time is EXCLUSIVE


------------------------------
## 2. Doctor Availability Rules## B1 — Working Hours

* Structure: Each doctor has one or more schedule blocks per day.
* Block Definition: Contains start_time and end_time.
* Core Constraint:

Doctors can have multiple shifts per day


## B2 — Break Handling

* Storage: Breaks are NOT explicitly stored.
* Logic: Breaks are implicitly created when gaps exist between schedule blocks or appointments.
* Core Constraint:

No explicit break entity in MVP


## B3 — Clinic Scope (CORRECTED)

* Structure: A doctor belongs to exactly ONE clinic.
* Scoping: All schedules and appointments belong strictly to that single clinic context.
* Core Constraint:

No doctor exists outside its clinic boundary


------------------------------
## 3. Booking Behavior Rules## C1 — Booking Window

* Window: Patients can book up to 7 days in advance.
* Type: Window is rolling (from current time forward).
* Core Constraint:

No bookings beyond 7-day horizon


## C2 — Past Booking

* Rule: No booking in the past allowed.
* Core Constraint:

Only future times are valid


## C3 — Doctor Selection Rule

* Scenario: If a doctor is NOT specified.
* Behavior: System suggests available doctors. System does NOT auto-assign silently.
* Core Constraint:

No implicit doctor assignment in MVP


## C4 — Slot Suggestion Rule

* Scenario: If the requested time is unavailable.
* Behavior:
* System must try the same doctor first.
   * If unavailable → suggest nearest slots.
* Limitation: Limit suggestions to the same day first, then adjacent days within the 7-day window.
* Core Constraint:

Maximum 3–5 suggestions per response (bounded output)


------------------------------
## 4. Rescheduling Rules## D1 — Rescheduling Allowed

* Rule: Rescheduling is ALWAYS allowed in the MVP.
* Core Constraint:

No restriction on rescheduling frequency


## D2 — Reschedule Implementation

* Logic: Rescheduling = UPDATE existing appointment record.
* Core Constraint:

Previous state must be preserved internally (audit-safe fields or metadata)


------------------------------
## 5. Cancellation Rules## E1 — Cancellation Allowed

* Rule: Patients can cancel at any time.
* Core Constraint:

No time-based restrictions in MVP


## E2 — Post-Cancellation Behavior

* Logic: Slot becomes immediately available again.
* Core Constraint:

No cooldown period


------------------------------
## 6. Patient Identity Rules## F1 — Unique Identity Key

* Rule: Patient is uniquely identified by phone + clinic_id.
* Core Constraint:

Same phone in different clinics = different patient records


## F2 — Identity Conflicts

* Scenario A: Same phone, different name.
* Rule: Phone overrides name (system source of truth).
* Scenario B: Same email, different phone.
* Rule: Phone still remains the primary identifier.

------------------------------
## 7. System Consistency Rules## G1 — Idempotency

* Scenario: If the same booking request is received.
* Behavior: Return the ORIGINAL result. Do NOT fail. Do NOT duplicate.
* Core Constraint:

Idempotency guarantees stable responses


## G2 — Race Conditions (CORRECTED)

* Scenario: If two users book the exact same slot.
* Behavior: First valid booking wins within the same clinic + doctor + time slot. The losing request fails the availability check and receives alternative suggestions.
* Core Constraint:

No cross-clinic conflict resolution exists (since there is no multi-tenancy)


------------------------------
## 8. Voice Input Rules (Vapi Behavior Contract)## H1 — Ambiguous Requests

* Scenario: If input is ambiguous (e.g., "tomorrow morning").
* Behavior: Do NOT guess silently. The system must return multiple valid options.
* Core Constraint:

Always return options, never assumptions


## H2 — Minimum Required Input

* Scenario: To proceed with booking.
* Data Requirements:
* Required: patient name, patient phone
   * Optional: doctor, exact time
* Core Constraint:

System can proceed with partial data but must resolve ambiguity explicitly


------------------------------
## 9. Core System Principle## Determinism Rule (REFINED)

Given the same system state + same input, the system MUST always produce the same output.
Note: This determinism applies within a single clinic context only. The system is not globally distributed across tenants, and no cross-clinic state reconciliation is required.

This architectural truth guarantees:

* Predictable voice behavior
* Safe retries
* A highly debuggable system
* Prevention of phantom bookings




