# 🤖 AI-Assisted Appointment Booking Platform

An appointment booking platform designed to automate scheduling workflows for clinics and other appointment-based businesses.

The system enables patients to book appointments through a conversational interface while automatically handling patient identification, doctor lookup, availability validation, conflict detection, and appointment creation.

Rather than relying on manual scheduling processes, the platform is designed to streamline booking operations and reduce administrative effort through structured business workflows and automation.

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

This platform automates the appointment booking workflow from request to confirmation.

Patients interact with an AI-powered assistant that captures booking intent and submits structured booking requests to the backend platform.

The backend then:
1. Identifies or creates the patient record
2. Resolves the requested practitioner
3. Calculates real-time availability
4. Detects scheduling conflicts
5. Creates confirmed appointments
6. Suggests alternative times when conflicts occur

The result is a booking experience that reduces administrative overhead while maintaining scheduling accuracy.

---

## 🌟 Key Capabilities

### 📅 Appointment Scheduling
Create appointments through automated workflows that validate availability before confirmation.

### 🔍 Patient Resolution
Identify existing patients using phone numbers or create new patient records when necessary.

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
Duplicate booking requests are safely detected and ignored, preventing accidental double bookings caused by retries or network interruptions.

### 🔮 Alternative Appointment Suggestions
When a requested time is unavailable, the system generates alternative booking options for the patient.

---

## 🔄 System Workflow

```text
Patient
   │
   ▼
AI Assistant
   │
   ▼
Booking API
   │
   ▼
Patient Resolution
   │
   ▼
Doctor Resolution
   │
   ▼
Availability Validation
   │
   ▼
Conflict Detection
   │
   ▼
Appointment Creation
   │
   ▼
Confirmation Response
```

---

## 🛠️ Technology Stack

### ⚙️ Backend
* Python
* FastAPI

### 🗄️ Database
* PostgreSQL

### 🗺️ Data Access
* SQLAlchemy 2.0

### 🚀 Database Migrations
* Alembic

### 🧠 AI Integration
* Vapi (planned)

### 📦 Package Management
* uv

---

## 🏗️ Architecture Overview

The platform follows a layered architecture where each layer has a clearly defined responsibility.

```text
app/
├── core/
├── models/
├── repositories/
├── schemas/
├── docs/
└── main.py
```

### 📋 Layer Responsibilities

| Layer            | Responsibility                               |
| ---------------- | -------------------------------------------- |
| API Layer        | Request handling and validation              |
| Service Layer    | Booking orchestration and business workflows |
| Repository Layer | Data access and persistence                  |
| Domain Layer     | Business rules and domain models             |
| Core Layer       | Configuration and shared infrastructure      |

This separation helps keep business logic independent from database and API concerns.

---

## 🧩 Domain Model

The platform is built around six primary entities:

### 🏢 Clinic
Represents the organizational boundary for providers and patients.

### 🧑‍⚕️ Doctor
Healthcare practitioner with one or more availability schedules.

### 👤 Patient
Individual receiving care and requesting appointments.

### 🗓️ Schedule
Defines provider working hours and availability windows.

### 📝 Appointment
Represents a confirmed booking.

### 📥 Booking Request
Captures incoming scheduling intent before appointment creation.

This separation provides traceability, supports retry-safe operations, and simplifies workflow management.

---

## ⚡ Key Design Decisions

### 🔄 Dynamic Availability
Availability is calculated on demand rather than stored as pre-generated booking slots. This reduces duplicated state and simplifies schedule management.

### 🔀 Booking Requests and Appointments Are Separate
A booking request represents intent. An appointment represents a confirmed booking. Separating these concerns provides better auditability and safer processing.

### 🔒 Database-Enforced Scheduling Integrity
The database serves as the final authority for preventing overlapping appointments. Application-level validation improves user experience, while database constraints provide concurrency-safe protection.

### 🆔 UUID-Based Identifiers
All primary entities use UUIDs to support distributed workflows and prevent predictable public identifiers.

---

## 🚀 Production Considerations

### 🔑 Idempotency
Every booking request includes an idempotency key. Repeated requests return the original result rather than creating duplicate appointments.

### 🚧 Conflict Handling
When a scheduling conflict occurs:
1. The booking is rejected.
2. Alternative available times are generated.
3. Suggestions are returned immediately.

This approach supports responsive conversational booking experiences.

---

## 📈 Project Status

### 📊 Current Progress

| Phase                              | Status         |
| ---------------------------------- | -------------- |
| Foundation & Configuration         | ✅ Complete     |
| Domain Modeling                    | ✅ Complete     |
| Database Design & Migrations       | ✅ Complete     |
| Business Rules & Scheduling Design | ✅ Complete     |
| Repository Layer                   | ✅ Complete     |
| Service Layer                      | ✅ Complete     |
| API Endpoints                      | ✅ Complete     |
| AI Integration                     | 🚧 In Progress |

---

## 🏁 Getting Started

### 📋 Prerequisites
* Python 3.13+
* PostgreSQL
* uv

### 💻 Installation

Clone the repository:
```bash
git clone <repository-url>
cd ai-booking-platform
```

Install dependencies:
```bash
uv sync
```

Configure environment variables:
```bash
cp .env.example .env
```
Update the database connection settings in the `.env` file.

Run migrations:
```bash
alembic upgrade head
```

Start the development server:
```bash
uvicorn app.main:app --reload
```

---

## 📄 Documentation

Detailed design and architecture documents can be found in:
```text
app/docs/
```

Including:
* System Architecture
* Domain Design
* Scheduling Policies
* Business Rules
* Architectural Decisions

---

## 🔮 Future Enhancements

* Appointment rescheduling
* Appointment cancellation workflows
* Multi-channel booking support
* Provider calendar integrations
* Notifications and reminders 🔔
* Administrative dashboard 📊
* Reporting and analytics 📈

---

## 📜 License

MIT License
