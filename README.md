# 🤖 AI-Assisted Appointment Booking Platform

An appointment booking platform designed to automate scheduling workflows for clinics and other appointment-based businesses.

The system enables patients to book appointments through a conversational interface (Vapi AI voice agent) while automatically handling patient identification, doctor lookup, availability validation, conflict detection, and appointment creation.

Rather than relying on manual scheduling processes, the platform streamlines booking operations and reduces administrative effort through structured business workflows and automation.

---

## ❓ The Problem

Many clinics still manage appointments through phone calls and manual scheduling processes.

Staff members often need to:
* Answer booking requests
* Verify patient information
* Check provider availability
* Prevent scheduling conflicts
* Create and update appointments

As appointment volumes grow, these processes become time-consuming, error-prone, and difficult to scale.

---

## 💡 The Solution

This platform automates the appointment booking workflow from voice request to confirmation.

Patients interact with a **Vapi AI voice assistant** that captures booking intent and invokes backend tools via a dedicated webhook API.

The backend then:
1. Resolves doctor availability dynamically in real time
2. Calculates free 30-minute schedule windows
3. Detects scheduling conflicts
4. Identifies existing patients or conditionally creates new patient records upon availability confirmation
5. Creates confirmed appointments atomically
6. Suggests alternative time slots when requested times are unavailable

The result is a low-latency booking experience that reduces administrative overhead while maintaining scheduling accuracy.

---

## 🌟 Key Capabilities

### 🗣️ Voice AI Integration (Vapi)
A dedicated `POST /vapi/webhook` adapter routes tool-call requests (`list_doctors`, `check_availability`, `create_booking`) seamlessly from live phone calls to backend services.

### 📅 Appointment Scheduling
Create appointments through automated workflows that validate availability before confirmation.

### 🔍 Patient Resolution
Identify existing patients using clinic ID + phone number, or create new patient records conditionally after availability is confirmed.

### 🩺 Doctor Resolution
Locate providers by clinic, specialty, or identifier.

### ⏱️ Dynamic Availability Calculation
Availability is calculated in real time using schedules and existing appointments.

```text
Available Time = Schedule − Existing Appointments
```

No pre-generated booking slots are required.

### 🚫 Conflict Detection
The platform prevents overlapping appointments and provides alternative scheduling options when conflicts occur.

### 🔄 Idempotent Request Processing
Duplicate booking requests are safely detected and ignored using unique `Idempotency-Key` headers (or Vapi `call.id`), preventing accidental double bookings.

### 🔮 Alternative Appointment Suggestions
When a requested time is unavailable, the system generates alternative booking options for the patient.

---

## 🔄 System Workflow

```text
Patient (Phone Call)
   │
   ▼
Vapi AI Voice Assistant
   │
   ▼
POST /vapi/webhook  <──>  REST Endpoints (/clinics/{id}/...)
   │
   ▼
Doctor Resolution (DoctorRepository)
   │
   ▼
Availability Validation (AvailabilityService)
   │
   ▼
Conditional Patient Resolution (PatientResolutionService)
   │
   ▼
Appointment Creation & DB Constraint Guard
   │
   ▼
Structured Confirmation & Alternative Suggestions
```

---

## 🛠️ Technology Stack

### ⚙️ Backend
* Python 3.13+
* FastAPI

### 🗄️ Database
* PostgreSQL (Production)
* SQLite in-memory with StaticPool (Isolated Unit & Integration Testing)

### 🗺️ Data Access
* SQLAlchemy 2.0 (ORM & Core)

### 🚀 Database Migrations
* Alembic

### 🧠 AI Voice Integration
* Vapi AI (vapi.ai) Function Calling & Webhooks

### 📦 Package Management
* uv

---

## 🏗️ Architecture Overview

The platform follows a layered architecture where each layer has a clearly defined responsibility.

```text
app/
├── api/
│   ├── deps.py              # Dependency injection & wired services
│   ├── mappers/             # Response mappers
│   └── routers/
│       ├── availability.py  # GET /doctors/{id}/availability
│       ├── bookings.py      # POST /bookings
│       ├── doctors.py       # GET /doctors
│       └── vapi.py          # POST /vapi/webhook (AI Tool Webhook)
├── core/
│   ├── config.py
│   └── db.py
├── models/                  # SQLAlchemy domain entities
├── repositories/            # Data access & persistence
├── schemas/                 # Pydantic DTOs & validation
├── services/                # Business logic & orchestration
└── main.py                  # FastAPI application entrypoint
```

---

## 🧩 Domain Model

The platform is built around six primary entities (all using UUID primary keys):

* **🏢 Clinic**: Organizational boundary for providers and patients.
* **🧑‍⚕️ Doctor**: Healthcare practitioner with one or more availability schedules.
* **👤 Patient**: Individual receiving care and requesting appointments.
* **🗓️ Schedule**: Defines provider working hours and availability windows.
* **📝 Appointment**: Represents a confirmed booking (final state).
* **📥 BookingRequest**: Captures incoming scheduling intent before appointment creation (idempotency layer).

---

## ⚡ Key Design Decisions

### 🤖 Dedicated Vapi Webhook Adapter (`POST /vapi/webhook`)
Rather than forcing individual REST routes on the voice AI, a unified Vapi webhook adapter unwraps tool-call payloads (`list_doctors`, `check_availability`, `create_booking`), extracts arguments, auto-injects `Idempotency-Key` headers using Vapi `call.id`, and formats results for the voice assistant.

### 🔄 Dynamic Availability
Availability is calculated on demand rather than stored as pre-generated booking slots (`Schedule - Appointments`).

### 🔀 Booking Requests and Appointments Are Separate
A booking request represents intent. An appointment represents a confirmed booking.

### 🔒 Database-Enforced Scheduling Integrity
The database serves as the final authority for preventing overlapping appointments. Application-level validation improves user experience, while database constraints provide concurrency-safe protection.

### 🆔 UUID-Based Identifiers
All primary entities use UUIDs to support distributed workflows and prevent predictable public identifiers.

### 👤 Conditional Patient Creation
Patients are resolved/created only AFTER doctor availability is confirmed, preventing orphan patient records on failed booking attempts.

---

## 🚀 Production Safety & Status Codes

### 🔑 Idempotency
Every booking request includes an idempotency key. Repeated successful requests return `200 OK` with the original appointment details.

### 🚧 Business Failure Mapping
When a booking fails due to an unavailable slot or missing schedule:
- Endpoint returns `409 Conflict`.
- Response body contains `"status": "FAILED"` and `alternative_slots`.
- No `Patient` or `Appointment` rows are created.

---

## 📈 Project Status

| Phase                              | Status      |
| ---------------------------------- | ----------- |
| Foundation & Configuration         | ✅ Complete  |
| Domain Modeling                    | ✅ Complete  |
| Database Design & Migrations       | ✅ Complete  |
| Business Rules & Scheduling Design | ✅ Complete  |
| Repository Layer                   | ✅ Complete  |
| Service Layer                      | ✅ Complete  |
| API Endpoints                      | ✅ Complete  |
| AI Voice Integration (Vapi)        | ✅ Complete  |

---

## 🏁 Getting Started

### 📋 Prerequisites
* Python 3.13+
* PostgreSQL (or SQLite for development)
* uv

### 💻 Installation

Clone the repository:
```bash
git clone <repository-url>
cd ai-booking-project
```

Activate virtual environment & sync dependencies:
```bash
source .venv/Scripts/activate  # On Windows Git Bash
uv sync
```

Run migrations:
```bash
alembic upgrade head
```

Run unit & integration test suite (48 tests):
```bash
pytest
```

Start development server:
```bash
uvicorn app.main:app --reload --port 8000
```

Expose via ngrok for Vapi AI Webhook integration:
```bash
ngrok http 8000
```
Then configure `https://<your-ngrok-domain>/vapi/webhook` in your Vapi Dashboard.

---

## 📄 Documentation

Detailed design and architecture documents can be found in `app/docs/`:
* `AI_BOOKING_SYSTEM_DESIGN_AND_ARCHITECTURE.md`
* `SYSTEM_BEHAVIOUR_DESIGN.md`
* `BUSINESS_RULES_&_SCHEDULING_POLICY.md`
* `AI_Booking_SYSTEM_DECISIONS_LOG.md`

---

## 📜 License

MIT License
