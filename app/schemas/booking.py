from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TimeSlotSchema


class CreateBookingRequest(BaseModel):
    doctor_id: UUID
    patient_name: str = Field(..., min_length=1, max_length=200)
    patient_phone: str = Field(..., min_length=1, max_length=50)
    patient_email: str | None = Field(default=None, max_length=254)
    requested_start_time: datetime


class BookingRequestSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    booking_request_id: UUID
    idempotency_key: str
    clinic_id: UUID
    doctor_id: UUID
    patient_name: str
    patient_phone: str
    patient_email: str | None
    requested_start_time: datetime
    status: Literal["RECEIVED", "PROCESSING", "SUCCESS", "FAILED"]
    appointment_id: UUID | None


class AppointmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    clinic_id: UUID
    doctor_id: UUID
    patient_id: UUID
    start_time: datetime
    end_time: datetime
    status: str


class BookingSuccessResponse(BaseModel):
    status: Literal["SUCCESS"]
    booking_request: BookingRequestSummary
    appointment: AppointmentSummary


class BookingFailureResponse(BaseModel):
    status: Literal["FAILED"]
    booking_request: BookingRequestSummary
    alternative_slots: list[TimeSlotSchema] = Field(default_factory=list)


BookingResponse = BookingSuccessResponse | BookingFailureResponse

