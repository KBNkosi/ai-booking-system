"""
test_patient_resolution_service.py — Unit tests for PatientResolutionService.resolve.

The patient repository is mocked so these tests verify only the branching
logic: return an existing patient vs. create a new one.
"""

import uuid
from unittest.mock import MagicMock, call

from app.models.patient import Patient
from app.services.patient_resolution_service import PatientResolutionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CLINIC_ID = uuid.uuid4()


def _make_patient(name="Alice", phone="+15551234567", email=None):
    p = Patient()
    p.patient_id = uuid.uuid4()
    p.clinic_id = CLINIC_ID
    p.name = name
    p.phone = phone
    p.email = email
    return p


def _make_service(existing_patient=None, created_patient=None):
    """
    Return a PatientResolutionService backed by a mocked PatientRepository.

    - existing_patient: what get_by_phone returns (None → not found)
    - created_patient: what create returns when a new patient is made
    """
    repo = MagicMock()
    repo.get_by_phone.return_value = existing_patient

    if created_patient is None:
        created_patient = _make_patient()
    repo.create.return_value = created_patient

    return PatientResolutionService(patient_repository=repo), repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_returns_existing_patient_when_found():
    """
    If the repository finds a patient with the given clinic_id + phone,
    resolve() must return that patient and must NOT call repo.create().
    """
    existing = _make_patient(name="Existing Alice", phone="+15551234567")
    svc, repo = _make_service(existing_patient=existing)

    result = svc.resolve(
        clinic_id=CLINIC_ID,
        name="Alice",
        phone="+15551234567",
        email="alice@example.com",
    )

    assert result is existing
    repo.get_by_phone.assert_called_once_with(CLINIC_ID, "+15551234567")
    repo.create.assert_not_called()


def test_creates_new_patient_when_not_found():
    """
    If the repository returns None for get_by_phone, resolve() must call
    repo.create() with the correct patient data and return the new patient.
    """
    new_patient = _make_patient(name="Bob", phone="+15559998888", email="bob@example.com")
    svc, repo = _make_service(existing_patient=None, created_patient=new_patient)

    result = svc.resolve(
        clinic_id=CLINIC_ID,
        name="Bob",
        phone="+15559998888",
        email="bob@example.com",
    )

    assert result is new_patient
    repo.get_by_phone.assert_called_once_with(CLINIC_ID, "+15559998888")
    repo.create.assert_called_once()

    # The patient passed to create must carry the correct attributes
    created_arg: Patient = repo.create.call_args[0][0]
    assert created_arg.clinic_id == CLINIC_ID
    assert created_arg.name == "Bob"
    assert created_arg.phone == "+15559998888"
    assert created_arg.email == "bob@example.com"


def test_creates_patient_without_email():
    """
    resolve() must work when email is None (optional field).
    """
    new_patient = _make_patient(name="Carol", phone="+15550001111", email=None)
    svc, repo = _make_service(existing_patient=None, created_patient=new_patient)

    result = svc.resolve(
        clinic_id=CLINIC_ID,
        name="Carol",
        phone="+15550001111",
        email=None,
    )

    assert result is new_patient
    created_arg: Patient = repo.create.call_args[0][0]
    assert created_arg.email is None
