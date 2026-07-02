import uuid
import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.appointment import Appointment

class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, appointment_id: uuid.UUID) -> Optional[Appointment]:
        appointment = self.db.get(Appointment, appointment_id)
        if not appointment:
            return None
            
        return appointment

    def get_for_doctor_in_range(self, doctor_id: uuid.UUID, start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.doctor_id == doctor_id)
            .where(Appointment.start_time < end_datetime)
            .where(Appointment.end_time > start_datetime)
        )

        return self.db.scalars(stmt).all()

    def get_for_patient(self, patient_id: uuid.UUID) -> List[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.start_time.desc())
        )

        return self.db.scalars(stmt).all()

    def create(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()
        self.db.refresh(appointment)
        return appointment

    def update_status(self, appointment_id: uuid.UUID, status: str) -> Optional[Appointment]:
        appointment = self.db.get(Appointment, appointment_id)
        if not appointment:
            return None
        appointment.status = status
        self.db.flush()
        return appointment

    def update_time(self, appointment_id: uuid.UUID, start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> Optional[Appointment]:
        appointment = self.db.get(Appointment, appointment_id)
        if not appointment:
            return None
        appointment.start_time = start_datetime
        appointment.end_time = end_datetime
        self.db.flush()
        return appointment

    

    