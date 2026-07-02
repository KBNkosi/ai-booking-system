import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.doctor import Doctor

class DoctorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, doctor_id: uuid.UUID) -> Optional[Doctor]:
        return self.db.get(Doctor, doctor_id)

    def get_by_specialty(self, clinic_id:uuid.UUID, specialty:str) -> List[Doctor]:
        stmt = (
            select(Doctor)
            .where(Doctor.clinic_id == clinic_id)
            .where(Doctor.specialty == specialty)
        )
        return list(self.db.scalars(stmt).all())

    def list_by_clinic(self, clinic_id: uuid.UUID) -> List[Doctor]:
        stmt = select(Doctor).where(Doctor.clinic_id == clinic_id)
        return list(self.db.scalars(stmt).all())