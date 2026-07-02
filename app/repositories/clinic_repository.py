import uuid
from typing import Optional 
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.clinic import Clinic

class ClinicRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, clinic_id:uuid.UUID) -> Optional[Clinic]:
        return self.db.get(Clinic, clinic_id)

    def get_by_name(self, name:str) -> Optional[Clinic]:
        stmt = select(Clinic).where(Clinic.name == name)
        return self.db.scalar(stmt)