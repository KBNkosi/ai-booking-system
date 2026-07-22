"""
test_api_failures.py — Tests for business-logic failure conditions.

Covers: clinic/doctor not found, doctor belonging to a different clinic,
no schedule exists, overlapping appointments, and booking a slot that
is unavailable.
"""

import datetime
import uuid

from sqlalchemy import select, func

from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.booking_request import BookingRequest


# ---------------------------------------------------------------------------
# 404 — not-found scenarios
# ---------------------------------------------------------------------------

def test_clinic_not_found(client):
    """GET /doctors for a non-existent clinic must return 404."""
    fake_clinic_id = str(uuid.uuid4())
    response = client.get(f"/clinics/{fake_clinic_id}/doctors")
    assert response.status_code == 404
    assert response.json()["detail"] == "Clinic not found"


def test_doctor_not_found_for_availability(client, db_session):
    """GET /availability for a non-existent doctor must return 404."""
    clinic = Clinic(name="Clinic NF")
    db_session.add(clinic)
    db_session.flush()

    fake_doctor_id = str(uuid.uuid4())
    response = client.get(
        f"/clinics/{clinic.clinic_id}/doctors/{fake_doctor_id}/availability",
        params={"requested_start_time": "2025-01-01T09:00:00"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Doctor not found"


def test_doctor_wrong_clinic_for_availability(client, db_session):
    """Doctor that exists but belongs to a different clinic must return 404."""
    clinic_a = Clinic(name="Clinic A")
    clinic_b = Clinic(name="Clinic B")
    doctor = Doctor(name="Dr. Other", specialty="GP", clinic=clinic_a)
    db_session.add_all([clinic_a, clinic_b, doctor])
    db_session.flush()

    # Query using clinic_b's ID even though the doctor belongs to clinic_a
    response = client.get(
        f"/clinics/{clinic_b.clinic_id}/doctors/{doctor.doctor_id}/availability",
        params={"requested_start_time": "2025-01-01T09:00:00"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Doctor not found"


def test_doctor_not_found_for_booking(client, db_session):
    """POST /bookings for a non-existent doctor must return 404."""
    clinic = Clinic(name="Booking NF Clinic")
    db_session.add(clinic)
    db_session.flush()

    payload = {
        "doctor_id": str(uuid.uuid4()),
        "patient_name": "Alice",
        "patient_phone": "+15559990000",
        "requested_start_time": "2025-01-01T09:00:00",
    }
    response = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json=payload,
        headers={"Idempotency-Key": "nf-doctor-booking-key"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Doctor not found"


def test_doctor_wrong_clinic_for_booking(client, db_session):
    """POST /bookings with a doctor from a different clinic must return 404."""
    clinic_a = Clinic(name="Booking Clinic A")
    clinic_b = Clinic(name="Booking Clinic B")
    doctor = Doctor(name="Dr. WrongClinic", specialty="GP", clinic=clinic_a)
    db_session.add_all([clinic_a, clinic_b, doctor])
    db_session.flush()

    payload = {
        "doctor_id": str(doctor.doctor_id),
        "patient_name": "Bob",
        "patient_phone": "+15558880000",
        "requested_start_time": "2025-01-01T09:00:00",
    }
    # Use clinic_b — doctor belongs to clinic_a
    response = client.post(
        f"/clinics/{clinic_b.clinic_id}/bookings",
        json=payload,
        headers={"Idempotency-Key": "wrong-clinic-booking-key"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Doctor not found"


def test_clinic_not_found_for_booking(client):
    """POST /bookings for a non-existent clinic must return 404."""
    fake_clinic_id = str(uuid.uuid4())
    payload = {
        "doctor_id": str(uuid.uuid4()),
        "patient_name": "Bob",
        "patient_phone": "+15558880000",
        "requested_start_time": "2025-01-01T09:00:00",
    }
    response = client.post(
        f"/clinics/{fake_clinic_id}/bookings",
        json=payload,
        headers={"Idempotency-Key": "clinic-nf-booking-key"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Clinic not found"


# ---------------------------------------------------------------------------
# Availability — slot unavailable scenarios
# ---------------------------------------------------------------------------

def test_unavailable_slot_no_schedule(client, db_session):
    """Availability returns is_available=False when the doctor has no schedule."""
    clinic = Clinic(name="No Schedule Clinic")
    doctor = Doctor(name="Dr. NoSchedule", specialty="GP", clinic=clinic)
    db_session.add_all([clinic, doctor])
    db_session.flush()
    # No schedule row added

    response = client.get(
        f"/clinics/{clinic.clinic_id}/doctors/{doctor.doctor_id}/availability",
        params={"requested_start_time": "2025-06-01T09:00:00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_available"] is False


def test_unavailable_slot_overlap(client, db_session):
    """Availability returns is_available=False when an appointment already overlaps."""
    clinic = Clinic(name="Overlap Clinic")
    doctor = Doctor(name="Dr. Overlap", specialty="GP", clinic=clinic)

    slot_start = datetime.datetime(2025, 6, 1, 9, 0)
    slot_end = datetime.datetime(2025, 6, 1, 9, 30)

    schedule = Schedule(
        doctor=doctor,
        start_time=datetime.datetime(2025, 6, 1, 8, 0),
        end_time=datetime.datetime(2025, 6, 1, 17, 0),
    )

    # Create a patient directly to attach to the overlapping appointment
    from app.models.patient import Patient
    patient = Patient(
        clinic_id=clinic.clinic_id,
        name="Existing Patient",
        phone="+15550001111",
    )

    db_session.add_all([clinic, doctor, schedule])
    db_session.flush()

    patient.clinic_id = clinic.clinic_id
    db_session.add(patient)
    db_session.flush()

    existing_appt = Appointment(
        clinic_id=clinic.clinic_id,
        doctor_id=doctor.doctor_id,
        patient_id=patient.patient_id,
        start_time=slot_start,
        end_time=slot_end,
        status="CONFIRMED",
    )
    db_session.add(existing_appt)
    db_session.flush()

    response = client.get(
        f"/clinics/{clinic.clinic_id}/doctors/{doctor.doctor_id}/availability",
        params={"requested_start_time": slot_start.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_available"] is False


# ---------------------------------------------------------------------------
# Booking failure — no schedule → FAILED booking request
# ---------------------------------------------------------------------------

def test_booking_fails_for_unavailable_slot(client, db_session):
    """
    POST /bookings when the slot is unavailable must:
    - Return 409
    - Return status=FAILED in the body
    - Create exactly one booking_request row with status=FAILED
    - Create no appointment row
    - Create no patient row
    """
    clinic = Clinic(name="Failed Booking Clinic")
    doctor = Doctor(name="Dr. Unavailable", specialty="GP", clinic=clinic)
    # No schedule — so slot will always be unavailable
    db_session.add_all([clinic, doctor])
    db_session.flush()

    payload = {
        "doctor_id": str(doctor.doctor_id),
        "patient_name": "Charlie",
        "patient_phone": "+15557770000",
        "requested_start_time": "2025-06-01T09:00:00",
    }
    response = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json=payload,
        headers={"Idempotency-Key": "failed-booking-key-001"},
    )
    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "FAILED"

    # Verify DB state: booking request exists with FAILED status
    br_count = db_session.scalar(
        select(func.count()).select_from(BookingRequest)
        .where(BookingRequest.idempotency_key == "failed-booking-key-001")
    )
    assert br_count == 1

    br = db_session.scalars(
        select(BookingRequest)
        .where(BookingRequest.idempotency_key == "failed-booking-key-001")
    ).first()
    assert br.status == "FAILED"
    assert br.appointment_id is None

    # No appointment created
    appt_count = db_session.scalar(
        select(func.count()).select_from(Appointment)
    )
    assert appt_count == 0

    # No patient created (patient is only resolved after availability is confirmed)
    patient_count = db_session.scalar(
        select(func.count()).select_from(Patient)
    )
    assert patient_count == 0
