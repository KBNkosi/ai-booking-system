import uuid
import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from app.models.booking_request import BookingRequest
from app.models.appointment import Appointment
from app.services.patient_resolution_service import PatientResolutionService
from app.services.availability_service import AvailabilityService
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.booking_request import BookingRequestRepository
from app.repositories.doctor_repository import DoctorRepository


@dataclass
class BookingResult:
    status: str
    booking_request: BookingRequest
    appointment: Optional[Appointment] = None
    alternative_slots: List[tuple] = field(default_factory=list)


class BookingService:
    def __init__(
        self,
        patient_resolution_service: PatientResolutionService,
        availability_service: AvailabilityService,
        appointment_repository: AppointmentRepository,
        booking_request_repository: BookingRequestRepository,
        doctor_repository: DoctorRepository,
    ):
        self.patient_resolution_service = patient_resolution_service
        self.availability_service = availability_service
        self.appointment_repository = appointment_repository
        self.booking_request_repository = booking_request_repository
        self.doctor_repository = doctor_repository

    def process_booking(
        self,
        idempotency_key: str,
        clinic_id: uuid.UUID,
        doctor_id: uuid.UUID,
        patient_name: str,
        patient_phone: str,
        patient_email: Optional[str],
        requested_start_time: datetime.datetime
    ) -> BookingResult:
        
        # 1. Idempotency Check: Check if this request has already been processed
        existing_request = self.booking_request_repository.get_by_idempotency_key(idempotency_key)
        if existing_request:
            if existing_request.status == "SUCCESS":
                # Deterministic replay: retrieve the exact created appointment using appointment_id
                appointment = None
                if existing_request.appointment_id:
                    appointment = self.appointment_repository.get_by_id(existing_request.appointment_id)
                return BookingResult(
                    status="SUCCESS",
                    booking_request=existing_request,
                    appointment=appointment
                )
            else:
                return BookingResult(
                    status="FAILED",
                    booking_request=existing_request,
                    appointment=None
                )

        # Compute the fixed 30-minute end time
        requested_end_time = requested_start_time + datetime.timedelta(minutes=30)

        # 2. Record the new BookingRequest intent (no requested_end_time column in DB)
        booking_request = BookingRequest(
            idempotency_key=idempotency_key,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            patient_email=patient_email,
            requested_start_time=requested_start_time,
            status="RECEIVED"
        )
        booking_request = self.booking_request_repository.create(booking_request)

        # Update status to indicate processing has started
        self.booking_request_repository.update_status(booking_request.booking_request_id, "PROCESSING")

        # 3. Resolve Doctor: verify doctor exists
        doctor = self.doctor_repository.get_by_id(doctor_id)
        if not doctor:
            self.booking_request_repository.update_status(booking_request.booking_request_id, "FAILED")
            booking_request.status = "FAILED"
            return BookingResult(
                status="FAILED",
                booking_request=booking_request,
                appointment=None
            )

        # 4. Check Availability (Only passes requested_start_time; end time computed inside)
        availability = self.availability_service.check_availability(
            doctor_id=doctor_id,
            requested_start=requested_start_time
        )

        if availability.is_available:
            # 5. Resolve Patient Identity (Only resolved/created upon confirmed availability)
            patient = self.patient_resolution_service.resolve(
                clinic_id=clinic_id,
                name=patient_name,
                phone=patient_phone,
                email=patient_email
            )

            # 6. Create the Appointment
            appointment = Appointment(
                clinic_id=clinic_id,
                doctor_id=doctor_id,
                patient_id=patient.patient_id,
                start_time=requested_start_time,
                end_time=requested_end_time,
                status="CONFIRMED"
            )
            created_appointment = self.appointment_repository.create(appointment)

            # 7. Associate Appointment and update BookingRequest status to SUCCESS
            self.booking_request_repository.associate_appointment(
                booking_request.booking_request_id,
                created_appointment.appointment_id
            )
            self.booking_request_repository.update_status(booking_request.booking_request_id, "SUCCESS")
            booking_request.status = "SUCCESS"
            booking_request.appointment_id = created_appointment.appointment_id

            return BookingResult(
                status="SUCCESS",
                booking_request=booking_request,
                appointment=created_appointment
            )
        else:
            # Update BookingRequest to FAILED
            self.booking_request_repository.update_status(booking_request.booking_request_id, "FAILED")
            booking_request.status = "FAILED"

            return BookingResult(
                status="FAILED",
                booking_request=booking_request,
                appointment=None,
                alternative_slots=availability.alternative_slots
            )
