import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_availability_service, get_clinic_repository, get_doctor_repository
from app.api.mappers.availability import availability_response
from app.schemas.availability import AvailabilityQueryParams, AvailabilityResponse
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.doctor_repository import DoctorRepository
from app.services.availability_service import AvailabilityService

router = APIRouter()


@router.get(
    "/doctors/{doctor_id}/availability",
    response_model=AvailabilityResponse,
)
def check_availability(
    clinic_id: UUID,
    doctor_id: UUID,
    query: AvailabilityQueryParams = Depends(),
    availability_service: AvailabilityService = Depends(get_availability_service),
    clinic_repository: ClinicRepository = Depends(get_clinic_repository),
    doctor_repository: DoctorRepository = Depends(get_doctor_repository),
) -> AvailabilityResponse:
    clinic = clinic_repository.get_by_id(clinic_id)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    doctor = doctor_repository.get_by_id(doctor_id)
    if doctor is None or doctor.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    result = availability_service.check_availability(
        doctor_id=doctor_id,
        requested_start=query.requested_start_time,
    )

    return availability_response(result)