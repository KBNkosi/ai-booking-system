"""
test_booking_service.py — Unit tests for BookingService.process_booking.

All external dependencies (repositories and services) are mocked so these
tests exercise the orchestration logic in isolation.
"""

import datetime
import uuid
from unittest.mock import MagicMock

from app.models.appointment import Appointment
from app.models.booking_request import BookingRequest
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.services.availability_service import AvailabilityResult
from app.services.booking_service import BookingResult, BookingService

# Sentinel used to distinguish "not provided" from "explicitly None"
_UNSET = object()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(
    *,
    existing_request=None,
    doctor=_UNSET,
    availability_result=None,
    created_patient=None,
    created_appointment=None,
):
    """
    Build a BookingService with fully mocked dependencies.

    Pass ``doctor=None`` to simulate a doctor-not-found scenario.
    Omit ``doctor`` (or pass ``doctor=_UNSET``) to get a default valid doctor.
    """
    clinic_id = uuid.uuid4()
    doctor_id = uuid.uuid4()

    if doctor is _UNSET:
        doctor = Doctor()
        doctor.doctor_id = doctor_id
        doctor.clinic_id = clinic_id

    if created_patient is None:
        created_patient = Patient()
        created_patient.patient_id = uuid.uuid4()
        created_patient.clinic_id = clinic_id
        created_patient.name = "Alice"
        created_patient.phone = "+15551234567"

    start = datetime.datetime(2025, 6, 1, 9, 0)
    end = start + datetime.timedelta(minutes=30)

    if availability_result is None:
        availability_result = AvailabilityResult(
            is_available=True,
            requested_start=start,
            requested_end=end,
        )

    if created_appointment is None:
        created_appointment = Appointment()
        created_appointment.appointment_id = uuid.uuid4()
        created_appointment.clinic_id = clinic_id
        created_appointment.doctor_id = doctor_id
        created_appointment.patient_id = created_patient.patient_id
        created_appointment.start_time = start
        created_appointment.end_time = end
        created_appointment.status = "CONFIRMED"

    # --- Mocks ---
    booking_req_repo = MagicMock()
    booking_req_repo.get_by_idempotency_key.return_value = existing_request
    booking_req_repo.create.side_effect = lambda br: br  # return same object
    booking_req_repo.update_status.return_value = None
    booking_req_repo.associate_appointment.return_value = None

    doctor_repo = MagicMock()
    doctor_repo.get_by_id.return_value = doctor

    availability_svc = MagicMock()
    availability_svc.check_availability.return_value = availability_result

    patient_svc = MagicMock()
    patient_svc.resolve.return_value = created_patient

    appt_repo = MagicMock()
    appt_repo.get_by_id.return_value = created_appointment
    appt_repo.create.return_value = created_appointment

    svc = BookingService(
        patient_resolution_service=patient_svc,
        availability_service=availability_svc,
        appointment_repository=appt_repo,
        booking_request_repository=booking_req_repo,
        doctor_repository=doctor_repo,
    )
    return svc, clinic_id, doctor_id


# ---------------------------------------------------------------------------
# Idempotency — existing SUCCESS request
# ---------------------------------------------------------------------------

def test_idempotent_replay_success():
    """
    When an existing booking request with status=SUCCESS is found,
    process_booking must return the same appointment without any new DB writes.
    """
    existing_appt = Appointment()
    existing_appt.appointment_id = uuid.uuid4()

    existing_req = BookingRequest()
    existing_req.booking_request_id = uuid.uuid4()
    existing_req.status = "SUCCESS"
    existing_req.appointment_id = existing_appt.appointment_id

    svc, clinic_id, doctor_id = _make_service(
        existing_request=existing_req,
        created_appointment=existing_appt,
    )

    result = svc.process_booking(
        idempotency_key="existing-key",
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        patient_name="Alice",
        patient_phone="+15551234567",
        patient_email=None,
        requested_start_time=datetime.datetime(2025, 6, 1, 9, 0),
    )

    assert result.status == "SUCCESS"
    assert result.booking_request is existing_req
    assert result.appointment is existing_appt

    # No new writes should have happened
    svc.booking_request_repository.create.assert_not_called()
    svc.appointment_repository.create.assert_not_called()
    svc.patient_resolution_service.resolve.assert_not_called()


# ---------------------------------------------------------------------------
# Idempotency — existing FAILED request
# ---------------------------------------------------------------------------

def test_idempotent_replay_failed():
    """
    When an existing booking request with status=FAILED is found,
    process_booking must return FAILED immediately without re-processing.
    """
    existing_req = BookingRequest()
    existing_req.booking_request_id = uuid.uuid4()
    existing_req.status = "FAILED"
    existing_req.appointment_id = None

    svc, clinic_id, doctor_id = _make_service(existing_request=existing_req)

    result = svc.process_booking(
        idempotency_key="failed-key",
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        patient_name="Bob",
        patient_phone="+15559998888",
        patient_email=None,
        requested_start_time=datetime.datetime(2025, 6, 1, 9, 0),
    )

    assert result.status == "FAILED"
    assert result.booking_request is existing_req
    assert result.appointment is None

    svc.booking_request_repository.create.assert_not_called()
    svc.appointment_repository.create.assert_not_called()


# ---------------------------------------------------------------------------
# Doctor not found
# ---------------------------------------------------------------------------

def test_booking_fails_when_doctor_not_found():
    """
    When the doctor is not found, process_booking must mark the booking
    request FAILED and return a FAILED result.

    Note: ``doctor=None`` uses the sentinel so the repo returns None,
    simulating a doctor-not-found lookup.
    """
    svc, clinic_id, doctor_id = _make_service(doctor=None)

    result = svc.process_booking(
        idempotency_key="no-doctor-key",
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        patient_name="Charlie",
        patient_phone="+15557770000",
        patient_email=None,
        requested_start_time=datetime.datetime(2025, 6, 1, 9, 0),
    )

    assert result.status == "FAILED"
    assert result.appointment is None
    # update_status must have been called with FAILED at some point
    called_statuses = [
        call.args[1]
        for call in svc.booking_request_repository.update_status.call_args_list
    ]
    assert "FAILED" in called_statuses
    svc.appointment_repository.create.assert_not_called()


# ---------------------------------------------------------------------------
# Slot unavailable
# ---------------------------------------------------------------------------

def test_booking_fails_when_slot_unavailable():
    """
    When the availability service says the slot is taken, process_booking
    must return FAILED and must NOT create a patient or appointment.
    """
    unavailable = AvailabilityResult(
        is_available=False,
        requested_start=datetime.datetime(2025, 6, 1, 9, 0),
        requested_end=datetime.datetime(2025, 6, 1, 9, 30),
        alternative_slots=[],
    )
    svc, clinic_id, doctor_id = _make_service(availability_result=unavailable)

    result = svc.process_booking(
        idempotency_key="unavailable-key",
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        patient_name="Dave",
        patient_phone="+15556660000",
        patient_email=None,
        requested_start_time=datetime.datetime(2025, 6, 1, 9, 0),
    )

    assert result.status == "FAILED"
    assert result.appointment is None
    svc.patient_resolution_service.resolve.assert_not_called()
    svc.appointment_repository.create.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path — successful booking
# ---------------------------------------------------------------------------

def test_booking_succeeds_creates_patient_and_appointment():
    """
    When the slot is available, process_booking must:
    1. Resolve (or create) the patient
    2. Create an appointment
    3. Associate the appointment with the booking request
    4. Return SUCCESS with the created appointment
    """
    svc, clinic_id, doctor_id = _make_service()

    result = svc.process_booking(
        idempotency_key="success-key",
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        patient_name="Eve",
        patient_phone="+15550001111",
        patient_email="eve@example.com",
        requested_start_time=datetime.datetime(2025, 6, 1, 9, 0),
    )

    assert result.status == "SUCCESS"
    assert result.appointment is not None

    svc.patient_resolution_service.resolve.assert_called_once()
    svc.appointment_repository.create.assert_called_once()
    svc.booking_request_repository.associate_appointment.assert_called_once()
    svc.booking_request_repository.update_status.assert_called_with(
        result.booking_request.booking_request_id, "SUCCESS"
    )
