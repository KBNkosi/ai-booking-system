import datetime
import json
import uuid

from sqlalchemy import select, func
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.booking_request import BookingRequest


def test_vapi_webhook_non_tool_calls(client):
    """Vapi non-tool-call messages (e.g. status-update) return status ok."""
    payload = {
        "message": {
            "type": "status-update",
            "status": "in-progress"
        }
    }
    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_vapi_webhook_list_doctors(client, db_session):
    """Vapi tool-call list_doctors returns doctor list."""
    clinic = Clinic(name="Vapi Clinic")
    doctor = Doctor(name="Dr. Vapi", specialty="Pediatrics", clinic=clinic)
    db_session.add_all([clinic, doctor])
    db_session.flush()

    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_list_001",
                    "type": "function",
                    "function": {
                        "name": "list_doctors",
                        "arguments": {
                            "clinic_id": str(clinic.clinic_id)
                        }
                    }
                }
            ]
        }
    }

    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1

    res0 = data["results"][0]
    assert res0["toolCallId"] == "call_list_001"
    assert len(res0["result"]) == 1
    assert res0["result"][0]["doctor_id"] == str(doctor.doctor_id)
    assert res0["result"][0]["name"] == "Dr. Vapi"


def test_vapi_webhook_list_doctors_json_string_arguments(client, db_session):
    """Vapi tool-call with stringified JSON arguments is correctly parsed."""
    clinic = Clinic(name="Vapi String Args Clinic")
    doctor = Doctor(name="Dr. StringArgs", specialty="Derma", clinic=clinic)
    db_session.add_all([clinic, doctor])
    db_session.flush()

    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_string_args_001",
                    "type": "function",
                    "function": {
                        "name": "list_doctors",
                        "arguments": json.dumps({"clinic_id": str(clinic.clinic_id)})
                    }
                }
            ]
        }
    }

    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    res0 = data["results"][0]
    assert res0["toolCallId"] == "call_string_args_001"
    assert len(res0["result"]) == 1
    assert res0["result"][0]["name"] == "Dr. StringArgs"


def test_vapi_webhook_check_availability_available(client, db_session):
    """Vapi tool-call check_availability returns is_available=True when slot is free."""
    clinic = Clinic(name="Vapi Avail Clinic")
    doctor = Doctor(name="Dr. Avail", specialty="Cardiology", clinic=clinic)
    start_time = datetime.datetime(2025, 6, 1, 9, 0)
    schedule = Schedule(
        doctor=doctor,
        start_time=start_time,
        end_time=datetime.datetime(2025, 6, 1, 17, 0)
    )
    db_session.add_all([clinic, doctor, schedule])
    db_session.flush()

    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_avail_001",
                    "type": "function",
                    "function": {
                        "name": "check_availability",
                        "arguments": {
                            "clinic_id": str(clinic.clinic_id),
                            "doctor_id": str(doctor.doctor_id),
                            "requested_start_time": "2025-06-01T09:00:00Z"
                        }
                    }
                }
            ]
        }
    }

    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    res0 = data["results"][0]
    assert res0["toolCallId"] == "call_avail_001"
    assert res0["result"]["is_available"] is True


def test_vapi_webhook_check_availability_unavailable_no_schedule(client, db_session):
    """Vapi check_availability returns is_available=False when doctor has no schedule."""
    clinic = Clinic(name="Vapi No Schedule Clinic")
    doctor = Doctor(name="Dr. NoSched", specialty="GP", clinic=clinic)
    db_session.add_all([clinic, doctor])
    db_session.flush()

    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_no_sched_001",
                    "type": "function",
                    "function": {
                        "name": "check_availability",
                        "arguments": {
                            "clinic_id": str(clinic.clinic_id),
                            "doctor_id": str(doctor.doctor_id),
                            "requested_start_time": "2025-06-01T09:00:00"
                        }
                    }
                }
            ]
        }
    }

    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    res0 = data["results"][0]
    assert res0["toolCallId"] == "call_no_sched_001"
    assert res0["result"]["is_available"] is False


def test_vapi_webhook_create_booking_success(client, db_session):
    """Vapi tool-call create_booking successfully processes a valid booking request."""
    clinic = Clinic(name="Vapi Booking Clinic")
    doctor = Doctor(name="Dr. Book", specialty="GP", clinic=clinic)
    start_time = datetime.datetime(2025, 6, 1, 10, 0)
    schedule = Schedule(
        doctor=doctor,
        start_time=start_time,
        end_time=datetime.datetime(2025, 6, 1, 17, 0)
    )
    db_session.add_all([clinic, doctor, schedule])
    db_session.flush()

    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_book_001",
                    "type": "function",
                    "function": {
                        "name": "create_booking",
                        "arguments": {
                            "clinic_id": str(clinic.clinic_id),
                            "doctor_id": str(doctor.doctor_id),
                            "patient_name": "Jane Vapi",
                            "patient_phone": "+15551112222",
                            "requested_start_time": "2025-06-01T10:00:00"
                        }
                    }
                }
            ]
        }
    }

    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    res0 = data["results"][0]
    assert res0["toolCallId"] == "call_book_001"
    assert res0["result"]["status"] == "SUCCESS"
    assert res0["result"]["appointment_id"] is not None

    # Verify appointment saved in database
    appt_count = db_session.scalar(select(func.count()).select_from(Appointment))
    assert appt_count == 1


def test_vapi_webhook_create_booking_failed_unavailable(client, db_session):
    """Vapi tool-call create_booking handles failure gracefully when doctor has no schedule."""
    clinic = Clinic(name="Vapi Failed Clinic")
    doctor = Doctor(name="Dr. Fail", specialty="GP", clinic=clinic)
    db_session.add_all([clinic, doctor])
    db_session.flush()

    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_fail_001",
                    "type": "function",
                    "function": {
                        "name": "create_booking",
                        "arguments": {
                            "clinic_id": str(clinic.clinic_id),
                            "doctor_id": str(doctor.doctor_id),
                            "patient_name": "Bob Vapi",
                            "patient_phone": "+15553334444",
                            "requested_start_time": "2025-06-01T10:00:00"
                        }
                    }
                }
            ]
        }
    }

    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    res0 = data["results"][0]
    assert res0["toolCallId"] == "call_fail_001"
    assert res0["result"]["status"] == "FAILED"
    assert res0["result"]["appointment_id"] is None


def test_vapi_webhook_invalid_doctor_id(client, db_session):
    """Vapi tool-call with non-existent doctor returns error in result object."""
    clinic = Clinic(name="Vapi Bad Doc Clinic")
    db_session.add(clinic)
    db_session.flush()

    fake_doctor_id = str(uuid.uuid4())
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCalls": [
                {
                    "id": "call_bad_doc_001",
                    "type": "function",
                    "function": {
                        "name": "check_availability",
                        "arguments": {
                            "clinic_id": str(clinic.clinic_id),
                            "doctor_id": fake_doctor_id,
                            "requested_start_time": "2025-06-01T09:00:00"
                        }
                    }
                }
            ]
        }
    }

    response = client.post("/vapi/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    res0 = data["results"][0]
    assert res0["toolCallId"] == "call_bad_doc_001"
    assert "error" in res0["result"]
    assert res0["result"]["error"] == "Doctor not found"
