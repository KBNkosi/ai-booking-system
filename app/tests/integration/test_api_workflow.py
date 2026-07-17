import datetime

from sqlalchemy import select, func

from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.patient import Patient
from app.models.booking_request import BookingRequest
from app.models.appointment import Appointment

def test_full_happy_path_workflow(client, db_session):
    # Arrange: Create a clinic, doctor, and schedule 
    clinic = Clinic(name="Test Clinic")
    doctor = Doctor(
        name="Dr. Example", 
        clinic=clinic,
        specialty="General Practitioner",
        )

    requested_start = datetime.datetime(2025, 1, 1, 9, 0)
    schedule = Schedule(
        doctor=doctor,
        start_time=requested_start,
        end_time=datetime.datetime(2025, 1, 1, 17, 0),
    )

    db_session.add_all([clinic, doctor, schedule])
    db_session.flush()

    clinic_id = clinic.clinic_id
    doctor_id = doctor.doctor_id
    appointment_time = requested_start.isoformat()

    # 1. List doctors 
    doctors_response = client.get(f"/clinics/{clinic_id}/doctors")
    assert doctors_response.status_code == 200
    doctors = doctors_response.json()
    assert len(doctors) == 1
    assert doctors[0]["doctor_id"] == str(doctor_id)

    # 2. Check availability
    availability_response = client.get(
        f"/clinics/{clinic_id}/doctors/{doctor_id}/availability",
        params={"requested_start_time": appointment_time},
    )
    assert availability_response.status_code == 200
    availability_body = availability_response.json()
    assert availability_body["is_available"] is True
    assert availability_body["requested_slot"]["start_time"] == appointment_time
    assert availability_body["requested_slot"]["end_time"] == (
        requested_start + datetime.timedelta(minutes=30)
        ).isoformat()

    # 3. Create booking
    payload = {
     "doctor_id": str(doctor_id),
     "patient_name": "Alice Patient",
     "patient_phone": "+15551234567",
     "patient_email": "alice@example.com",
     "requested_start_time": appointment_time,
    }
    headers = {"Idempotency-Key": "test-key-123"}

    first_booking = client.post(
        f"/clinics/{clinic_id}/bookings",
        json=payload,
        headers=headers
    )

    assert first_booking.status_code == 201
    first_body = first_booking.json()
    assert first_body["status"] == "SUCCESS"
    first_appointment_id = first_body["appointment"]["appointment_id"]


    # 4. Attempt to create the same booking again with the same idempotency key
    second_booking = client.post(
        f"/clinics/{clinic_id}/bookings",
        json=payload,
        headers=headers
    )
    assert second_booking.status_code == 200
    second_body = second_booking.json()
    assert second_body["status"] == "SUCCESS"
    assert second_body["appointment"]["appointment_id"] == first_appointment_id


    # 5. Verify database state: There should be only one appointment, one patient, and one booking request
    appointment_count = db_session.scalar(select(func.count()).select_from(Appointment))
    patient_count = db_session.scalar(select(func.count()).select_from(Patient))
    booking_request_count = db_session.scalar(select(func.count()).select_from(BookingRequest))

    assert appointment_count == 1
    assert patient_count == 1
    assert booking_request_count == 1
