from datetime import datetime
from typing import Literal, cast

from app.models.appointment import Appointment
from app.models.booking_request import BookingRequest
from app.schemas.booking import (
    AppointmentSummary,
    BookingFailureResponse,
    BookingRequestSummary,
    BookingSuccessResponse,
)
from app.schemas.common import TimeSlotSchema
from app.services.booking_service import BookingResult


def _to_time_slot_schema(slot: tuple[datetime, datetime]) -> TimeSlotSchema:
    start_time, end_time = slot
    return TimeSlotSchema(start_time=start_time, end_time=end_time)


def booking_request_summary(booking_request: BookingRequest) -> BookingRequestSummary:
    return BookingRequestSummary(
        booking_request_id=booking_request.booking_request_id,
        idempotency_key=booking_request.idempotency_key,
        clinic_id=booking_request.clinic_id,
        doctor_id=booking_request.doctor_id,
        patient_name=booking_request.patient_name,
        patient_phone=booking_request.patient_phone,
        patient_email=booking_request.patient_email,
        requested_start_time=booking_request.requested_start_time,
        status=cast(Literal["RECEIVED", "PROCESSING", "SUCCESS", "FAILED"], booking_request.status),
        appointment_id=booking_request.appointment_id,
    )


def appointment_summary(appointment: Appointment) -> AppointmentSummary:
    return AppointmentSummary(
        appointment_id=appointment.appointment_id,
        clinic_id=appointment.clinic_id,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        status=appointment.status,
    )


def booking_response(result: BookingResult) -> BookingSuccessResponse | BookingFailureResponse:
    request_summary = booking_request_summary(result.booking_request)

    if result.status == "SUCCESS":
        assert result.appointment is not None
        return BookingSuccessResponse(
            status="SUCCESS",
            booking_request=request_summary,
            appointment=appointment_summary(result.appointment),
        )

    return BookingFailureResponse(
        status="FAILED",
        booking_request=request_summary,
        alternative_slots=[
            _to_time_slot_schema(slot) for slot in result.alternative_slots
        ],
    )