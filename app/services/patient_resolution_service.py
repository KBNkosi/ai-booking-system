import uuid
from typing import Optional
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository

class PatientResolutionService:
    def __init__(self, patient_repository: PatientRepository):
        self.patient_repository = patient_repository

    def resolve(self, clinic_id:uuid.UUID, name: str, phone: str, email: Optional[str] = None) -> Patient:
        existing_patient = self.patient_repository.get_by_phone(clinic_id, phone)

        if existing_patient:
            return existing_patient

        return self._create_patient(clinic_id, name, phone, email)

    def _create_patient(self, clinic_id: uuid.UUID, name: str, phone: str, email: Optional[str]) -> Patient:
        new_patient = Patient(
            clinic_id=clinic_id,
            name=name,
            phone=phone,
            email=email
        )
        return self.patient_repository.create(new_patient)