from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_clinic_repository, get_doctor_repository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.doctor_repository import DoctorRepository
from app.schemas.doctor import DoctorResponse

router = APIRouter()


@router.get("/doctors", response_model=List[DoctorResponse])
def list_doctors(
    clinic_id: UUID,
    clinic_repository: ClinicRepository = Depends(get_clinic_repository),
    doctor_repository: DoctorRepository = Depends(get_doctor_repository),
) -> List[DoctorResponse]:
    clinic = clinic_repository.get_by_id(clinic_id)
    if clinic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found",
        )

    doctors = doctor_repository.list_by_clinic(clinic_id)

    return [DoctorResponse.model_validate(doctor) for doctor in doctors]