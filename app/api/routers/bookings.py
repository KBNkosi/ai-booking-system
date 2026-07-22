from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from app.api.deps import (
    get_booking_service,
    get_clinic_repository,
    get_doctor_repository,
    get_booking_request_repository,
)
from app.api.mappers.booking import booking_response
from app.schemas.booking import BookingResponse, CreateBookingRequest
from app.repositories.booking_request import BookingRequestRepository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.doctor_repository import DoctorRepository
from app.services.booking_service import BookingService

router = APIRouter()


@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_booking(
    clinic_id: UUID,
    body: CreateBookingRequest,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    booking_service: BookingService = Depends(get_booking_service),
    clinic_repository: ClinicRepository = Depends(get_clinic_repository),
    doctor_repository: DoctorRepository = Depends(get_doctor_repository),
    booking_request_repository: BookingRequestRepository = Depends(
        get_booking_request_repository
    ),
) -> BookingResponse:
    clinic = clinic_repository.get_by_id(clinic_id)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    doctor = doctor_repository.get_by_id(body.doctor_id)
    if doctor is None or doctor.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    existing_request = booking_request_repository.get_by_idempotency_key(idempotency_key)
    if existing_request is not None:
        if existing_request.status == "SUCCESS":
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_409_CONFLICT

    result = booking_service.process_booking(
        idempotency_key=idempotency_key,
        clinic_id=clinic_id,
        doctor_id=body.doctor_id,
        patient_name=body.patient_name,
        patient_phone=body.patient_phone,
        patient_email=body.patient_email,
        requested_start_time=body.requested_start_time,
    )

    if result.status == "FAILED":
        response.status_code = status.HTTP_409_CONFLICT

    return booking_response(result)