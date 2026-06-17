# SYSTEM DESIGN DECISIONS LOG (V1)

## 1. Scheduling Model Decision

### Decision
We use **dynamic schedule-based availability**, not pre-generated slots.

### Why We Chose It
* Avoids maintaining slot state.
* Reduces database complexity.
* Eliminates sync issues between slots and appointments.
* Allows flexible real-time computation.

### Tradeoff Accepted
* Slightly more computation at request time.
* Requires careful overlap checking logic.

### Rejected Alternatives
* **Slot generation system:** Too state-heavy.
* **Calendar-based availability engine:** Over-engineered for MVP.

---

## 2. Appointment vs BookingRequest Separation

### Decision
We strictly separate:
* **BookingRequest** (Intent)
* **Appointment** (Confirmed State)

### Why
* Voice systems retry requests (idempotency requirement).
* We need an audit trail of failed/successful booking attempts.
* Prevents duplicate processing issues.

### Tradeoff
* More database tables.
* Higher system complexity.

### Alternative Rejected
* **Single Appointment table handling both intent + result:** Breaks under retries and partial network failures.

---

## 3. Appointment Responsibility Boundaries

### Decision
The `Appointment` entity does **NOT** validate:
* Availability
* Schedule rules
* Booking correctness

### Why
* `Appointment` is a result entity, not a decision entity.
* Validation belongs strictly to the service + database layers.

### Tradeoff
* Requires stronger service layer discipline.

### Risk Accepted
* Poor service design could still misuse the model (mitigated by strict architectural boundaries).

---

## 4. Database as Final Authority

### Decision
The Database enforces the core invariant: **no overlapping appointments per doctor**.

### Why
* Concurrency cannot be safely handled in the application layer alone.
* Multiple requests can bypass service checks under race conditions.
* DB constraints are atomic, isolated, and reliable.

### Tradeoff
* Business logic constraints are partially pushed into the database layer.
* Requires careful schema design (constraints/indexes).

### Alternatives Rejected
* **Service-only validation:** Unsafe under concurrency.
* **Locking in the application layer:** Too slow for a low-latency voice system.

---

## 5. Concurrency Strategy

### Decision
We use **optimistic concurrency**.

### Why
* Voice systems require low latency to maintain conversational flow.
* Locking resources reduces responsiveness and creates bottlenecks.
* Conflicts are relatively rare compared to successful bookings.

### Tradeoff
* Occasional failed database inserts.
* Requires instant fallback retry/suggestion logic.

---

## 6. Slot System Rejection

### Decision
No `Slot` entity.

### Why
* Slots create duplicated state (`Slot` state vs. `Appointment` state).
* Leads to synchronization issues.
* Increases system complexity significantly.

### Alternative Rejected
* **Pre-generated slot inventory system:** Classic calendar-like system that requires constant maintenance and background workers.

---

## 7. Future Deferred: ScheduleException

### Decision
Not included in the MVP.

### Why
* Increases scheduling complexity significantly.
* Not required for core booking functionality.
* Can be layered in later without breaking the core data model.