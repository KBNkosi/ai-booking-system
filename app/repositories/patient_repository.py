import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.patient import Patient

class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: uuid.UUID) -> Optional[Patient]:
        return self.db.get(Patient, patient_id)

    def get_by_phone(self, clinic_id: uuid.UUID,  phone:str) -> Optional[Patient]:
        stmt = (
            select(Patient)
            .where(Patient.clinic_id == clinic_id)
            .where(Patient.phone == phone)
        )
        return self.db.scalar(stmt)

    def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        self.db.refresh(patient)
        return patient
        
