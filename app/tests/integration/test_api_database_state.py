"""
test_api_database_state.py — Verifies persistence and idempotency behaviour.

These tests make real API calls and then inspect the database directly to
confirm that exactly the right rows were created (or NOT created) and that
the idempotency machinery prevents duplicate writes on replay.
"""

import datetime
import uuid

from sqlalchemy import select, func

from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.booking_request import BookingRequest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

SLOT_START = datetime.datetime(2025, 6, 1, 9, 0)
SLOT_END = SLOT_START + datetime.timedelta(minutes=30)


def _create_available_setup(db_session):
    """Insert a clinic, doctor and schedule and return (clinic, doctor)."""
    clinic = Clinic(name="DB State Clinic")
    doctor = Doctor(name="Dr. DBState", specialty="GP", clinic=clinic)
    schedule = Schedule(
        doctor=doctor,
        start_time=datetime.datetime(2025, 6, 1, 8, 0),
        end_time=datetime.datetime(2025, 6, 1, 17, 0),
    )
    db_session.add_all([clinic, doctor, schedule])
    db_session.flush()
    return clinic, doctor


def _booking_payload(doctor_id, phone="+15551234567", start=SLOT_START):
    return {
        "doctor_id": str(doctor_id),
        "patient_name": "Test Patient",
        "patient_phone": phone,
        "patient_email": "test@example.com",
        "requested_start_time": start.isoformat(),
    }


# ---------------------------------------------------------------------------
# BookingRequest persistence
# ---------------------------------------------------------------------------

def test_booking_request_persisted_correctly(client, db_session):
    """
    After a successful booking the BookingRequest row must have:
    - status = SUCCESS
    - appointment_id pointing to the created appointment
    """
    clinic, doctor = _create_available_setup(db_session)
    idem_key = f"br-persist-{uuid.uuid4()}"

    resp = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json=_booking_payload(doctor.doctor_id),
        headers={"Idempotency-Key": idem_key},
    )
    assert resp.status_code == 201

    br = db_session.scalars(
        select(BookingRequest).where(BookingRequest.idempotency_key == idem_key)
    ).first()
    assert br is not None
    assert br.status == "SUCCESS"
    assert br.appointment_id is not None
    assert br.clinic_id == clinic.clinic_id
    assert br.doctor_id == doctor.doctor_id


# ---------------------------------------------------------------------------
# Appointment persistence
# ---------------------------------------------------------------------------

def test_appointment_persisted_correctly(client, db_session):
    """
    After a successful booking the Appointment row must match the requested slot.
    """
    clinic, doctor = _create_available_setup(db_session)
    idem_key = f"appt-persist-{uuid.uuid4()}"

    resp = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json=_booking_payload(doctor.doctor_id),
        headers={"Idempotency-Key": idem_key},
    )
    assert resp.status_code == 201
    body = resp.json()
    appt_id = uuid.UUID(body["appointment"]["appointment_id"])

    appt = db_session.get(Appointment, appt_id)
    assert appt is not None
    assert appt.clinic_id == clinic.clinic_id
    assert appt.doctor_id == doctor.doctor_id
    assert appt.start_time == SLOT_START
    assert appt.end_time == SLOT_END
    assert appt.status == "CONFIRMED"


# ---------------------------------------------------------------------------
# Patient creation
# ---------------------------------------------------------------------------

def test_patient_created_only_after_availability_succeeds(client, db_session):
    """A patient row must exist after a successful booking."""
    clinic, doctor = _create_available_setup(db_session)
    phone = "+15550001111"
    idem_key = f"patient-create-{uuid.uuid4()}"

    resp = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json=_booking_payload(doctor.doctor_id, phone=phone),
        headers={"Idempotency-Key": idem_key},
    )
    assert resp.status_code == 201

    patient = db_session.scalars(
        select(Patient)
        .where(Patient.clinic_id == clinic.clinic_id)
        .where(Patient.phone == phone)
    ).first()
    assert patient is not None
    assert patient.name == "Test Patient"


def test_patient_not_created_on_failed_booking(client, db_session):
    """
    When a booking fails (no schedule → unavailable), no Patient row must
    be created.  The booking service only resolves the patient after
    availability is confirmed.
    """
    clinic = Clinic(name="No Patient Clinic")
    doctor = Doctor(name="Dr. NoPatient", specialty="GP", clinic=clinic)
    # No schedule → always unavailable
    db_session.add_all([clinic, doctor])
    db_session.flush()

    phone = "+15559998888"
    resp = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json=_booking_payload(doctor.doctor_id, phone=phone),
        headers={"Idempotency-Key": f"no-patient-{uuid.uuid4()}"},
    )
    assert resp.status_code == 409

    patient_count = db_session.scalar(
        select(func.count()).select_from(Patient)
        .where(Patient.phone == phone)
    )
    assert patient_count == 0


def test_patient_reuse_same_clinic_and_phone(client, db_session):
    """
    Two successful bookings for the same phone number within the same clinic
    must reuse the same patient row (PatientResolutionService deduplication).
    """
    # First booking
    clinic1 = Clinic(name="Patient Reuse Clinic")
    doctor1 = Doctor(name="Dr. Reuse1", specialty="GP", clinic=clinic1)
    sched1 = Schedule(
        doctor=doctor1,
        start_time=datetime.datetime(2025, 6, 1, 8, 0),
        end_time=datetime.datetime(2025, 6, 1, 17, 0),
    )
    # Second booking uses a different doctor (different slot) in the same clinic
    doctor2 = Doctor(name="Dr. Reuse2", specialty="GP", clinic=clinic1)
    sched2 = Schedule(
        doctor=doctor2,
        start_time=datetime.datetime(2025, 6, 2, 8, 0),
        end_time=datetime.datetime(2025, 6, 2, 17, 0),
    )
    db_session.add_all([clinic1, doctor1, sched1, doctor2, sched2])
    db_session.flush()

    phone = "+15550002222"
    slot2_start = datetime.datetime(2025, 6, 2, 9, 0)

    # First booking → creates patient
    resp1 = client.post(
        f"/clinics/{clinic1.clinic_id}/bookings",
        json=_booking_payload(doctor1.doctor_id, phone=phone),
        headers={"Idempotency-Key": f"reuse-1-{uuid.uuid4()}"},
    )
    assert resp1.status_code == 201

    # Second booking with same phone → must reuse patient
    resp2 = client.post(
        f"/clinics/{clinic1.clinic_id}/bookings",
        json=_booking_payload(doctor2.doctor_id, phone=phone, start=slot2_start),
        headers={"Idempotency-Key": f"reuse-2-{uuid.uuid4()}"},
    )
    assert resp2.status_code == 201

    # Only one patient row should exist for this phone in this clinic
    patient_count = db_session.scalar(
        select(func.count()).select_from(Patient)
        .where(Patient.clinic_id == clinic1.clinic_id)
        .where(Patient.phone == phone)
    )
    assert patient_count == 1


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_no_duplicate_appointment_on_idempotent_replay(client, db_session):
    """
    Replaying the same request with the same Idempotency-Key must not create
    a second appointment row.
    """
    clinic, doctor = _create_available_setup(db_session)
    idem_key = f"idempotent-replay-{uuid.uuid4()}"
    payload = _booking_payload(doctor.doctor_id)
    headers = {"Idempotency-Key": idem_key}

    resp1 = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=payload, headers=headers)
    assert resp1.status_code == 201

    resp2 = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=payload, headers=headers)
    assert resp2.status_code == 200  # idempotent replay returns 200

    # Appointment + BookingRequest counts must remain at 1
    appt_count = db_session.scalar(select(func.count()).select_from(Appointment))
    br_count = db_session.scalar(select(func.count()).select_from(BookingRequest))
    assert appt_count == 1
    assert br_count == 1


def test_replay_returns_same_appointment(client, db_session):
    """
    The appointment_id returned by the replay must be identical to the one
    from the original request.
    """
    clinic, doctor = _create_available_setup(db_session)
    idem_key = f"same-appt-replay-{uuid.uuid4()}"
    payload = _booking_payload(doctor.doctor_id)
    headers = {"Idempotency-Key": idem_key}

    first = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=payload, headers=headers)
    assert first.status_code == 201
    first_appt_id = first.json()["appointment"]["appointment_id"]

    second = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=payload, headers=headers)
    assert second.status_code == 200
    second_appt_id = second.json()["appointment"]["appointment_id"]

    assert first_appt_id == second_appt_id


def test_replay_failed_booking_with_same_key(client, db_session):
    """
    Replaying a failed booking with the same Idempotency-Key must:
    - Return 409 again
    - Return status=FAILED
    - Not create any new appointment
    - Not create a new BookingRequest row
    """
    # No schedule → unavailable
    clinic = Clinic(name="Failed Replay Clinic")
    doctor = Doctor(name="Dr. FailedReplay", specialty="GP", clinic=clinic)
    db_session.add_all([clinic, doctor])
    db_session.flush()

    idem_key = f"failed-replay-{uuid.uuid4()}"
    payload = {
        "doctor_id": str(doctor.doctor_id),
        "patient_name": "Replay Patient",
        "patient_phone": "+15556660000",
        "requested_start_time": "2025-06-01T09:00:00",
    }
    headers = {"Idempotency-Key": idem_key}

    resp1 = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=payload, headers=headers)
    assert resp1.status_code == 409
    assert resp1.json()["status"] == "FAILED"

    resp2 = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=payload, headers=headers)
    assert resp2.status_code == 409
    assert resp2.json()["status"] == "FAILED"

    # Still only one booking request row
    br_count = db_session.scalar(
        select(func.count()).select_from(BookingRequest)
        .where(BookingRequest.idempotency_key == idem_key)
    )
    assert br_count == 1

    # Still no appointment
    appt_count = db_session.scalar(select(func.count()).select_from(Appointment))
    assert appt_count == 0


def test_same_key_different_payload_returns_original(client, db_session):
    """
    Sending a different payload with an already-used Idempotency-Key must
    return the original result (the new payload is ignored entirely).
    """
    clinic, doctor = _create_available_setup(db_session)
    idem_key = f"same-key-diff-payload-{uuid.uuid4()}"

    original_payload = _booking_payload(doctor.doctor_id, phone="+15550003333")
    headers = {"Idempotency-Key": idem_key}

    first = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=original_payload, headers=headers)
    assert first.status_code == 201
    original_appt_id = first.json()["appointment"]["appointment_id"]

    # Completely different patient details — but same key
    different_payload = {
        "doctor_id": str(doctor.doctor_id),
        "patient_name": "Completely Different Name",
        "patient_phone": "+19999999999",
        "patient_email": "different@example.com",
        "requested_start_time": SLOT_START.isoformat(),
    }
    second = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=different_payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["appointment"]["appointment_id"] == original_appt_id
    assert second.json()["status"] == "SUCCESS"
