import uuid
import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.schedule import Schedule

class ScheduleRepository:
    def __init__(self, db: Session):
        self.db = db
    # Get schedules for a doctor
    def get_by_doctor(self, doctor_id: uuid.UUID) -> List[Schedule]:
        stmt = (
            select(Schedule)
            .where(Schedule.doctor_id == doctor_id)
            .order_by(Schedule.start_time.asc())
        )

        return self.db.scalars(stmt).all()

    # Get schedules for a doctor within a date range
    def get_for_date_range(self, doctor_id: uuid.UUID, start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[Schedule]:
        stmt = (
            select(Schedule)
            .where(Schedule.doctor_id == doctor_id)
            .where(Schedule.start_time < end_datetime)
            .where(Schedule.end_time > start_datetime)
            .order_by(Schedule.start_time.asc()) 
        )

        return self.db.scalars(stmt).all()
        