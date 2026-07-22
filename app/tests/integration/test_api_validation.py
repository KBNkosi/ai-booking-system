"""
test_api_validation.py — Validates that FastAPI rejects malformed requests
before any business logic runs.

These tests verify path-parameter coercion, query-parameter requirements,
header requirements, and request-body schema enforcement.
"""

import datetime
import uuid

from app.models.clinic import Clinic
from app.models.doctor import Doctor


# ---------------------------------------------------------------------------
# Header validation
# ---------------------------------------------------------------------------

def test_missing_idempotency_key_header(client, db_session):
    """POST /bookings without Idempotency-Key must return 422."""
    clinic = Clinic(name="Validation Clinic")
    doctor = Doctor(
        name="Dr. Validation",
        clinic=clinic,
        specialty="General Practitioner",
    )
    db_session.add_all([clinic, doctor])
    db_session.flush()

    payload = {
        "doctor_id": str(doctor.doctor_id),
        "patient_name": "Alice Patient",
        "patient_phone": "+15551234567",
        "patient_email": "alice@example.com",
        "requested_start_time": datetime.datetime(2025, 1, 1, 9, 0).isoformat(),
    }

    response = client.post(f"/clinics/{clinic.clinic_id}/bookings", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body

    # Pydantic v2 uses "missing" (not "value_error.missing")
    assert any(
        error["loc"] == ["header", "Idempotency-Key"] and error["type"] == "missing"
        for error in body["detail"]
    )


# ---------------------------------------------------------------------------
# Path-parameter validation
# ---------------------------------------------------------------------------

def test_invalid_clinic_id_path_param(client):
    """Non-UUID clinic_id must return 422 before any DB access."""
    response = client.get("/clinics/not-a-uuid/doctors")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    # FastAPI should flag the path parameter
    assert any("clinic_id" in str(error["loc"]) for error in body["detail"])


def test_invalid_doctor_id_path_param(client):
    """Non-UUID doctor_id in the availability route must return 422."""
    valid_clinic_id = str(uuid.uuid4())
    response = client.get(
        f"/clinics/{valid_clinic_id}/doctors/not-a-uuid/availability",
        params={"requested_start_time": "2025-01-01T09:00:00"},
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any("doctor_id" in str(error["loc"]) for error in body["detail"])


# ---------------------------------------------------------------------------
# Query-parameter validation
# ---------------------------------------------------------------------------

def test_missing_requested_start_time(client, db_session):
    """Availability endpoint without requested_start_time must return 422."""
    clinic = Clinic(name="Query Param Clinic")
    doctor = Doctor(
        name="Dr. QueryParam",
        clinic=clinic,
        specialty="General Practitioner",
    )
    db_session.add_all([clinic, doctor])
    db_session.flush()

    response = client.get(
        f"/clinics/{clinic.clinic_id}/doctors/{doctor.doctor_id}/availability"
        # Intentionally omitting the required ?requested_start_time= param
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(
        "requested_start_time" in str(error["loc"]) for error in body["detail"]
    )


def test_invalid_requested_start_time_format(client, db_session):
    """Availability endpoint with a non-datetime string must return 422."""
    clinic = Clinic(name="Bad DateTime Clinic")
    doctor = Doctor(
        name="Dr. BadDate",
        clinic=clinic,
        specialty="General Practitioner",
    )
    db_session.add_all([clinic, doctor])
    db_session.flush()

    response = client.get(
        f"/clinics/{clinic.clinic_id}/doctors/{doctor.doctor_id}/availability",
        params={"requested_start_time": "not-a-date"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Request-body validation
# ---------------------------------------------------------------------------

def test_invalid_booking_body_missing_required_fields(client, db_session):
    """POST /bookings with missing required body fields must return 422."""
    clinic = Clinic(name="Body Validation Clinic")
    db_session.add(clinic)
    db_session.flush()

    # Completely empty body — all required fields are missing
    response = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json={},
        headers={"Idempotency-Key": "body-validation-key"},
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    # All required fields should appear in the errors
    error_fields = [str(e["loc"]) for e in body["detail"]]
    assert any("doctor_id" in f for f in error_fields)
    assert any("patient_name" in f for f in error_fields)
    assert any("patient_phone" in f for f in error_fields)


def test_invalid_booking_body_bad_doctor_id(client, db_session):
    """POST /bookings with a non-UUID doctor_id in the body must return 422."""
    clinic = Clinic(name="Bad Doctor ID Clinic")
    db_session.add(clinic)
    db_session.flush()

    payload = {
        "doctor_id": "not-a-uuid",
        "patient_name": "Alice",
        "patient_phone": "+15551234567",
        "requested_start_time": "2025-01-01T09:00:00",
    }
    response = client.post(
        f"/clinics/{clinic.clinic_id}/bookings",
        json=payload,
        headers={"Idempotency-Key": "bad-doctor-id-key"},
    )
    assert response.status_code == 422