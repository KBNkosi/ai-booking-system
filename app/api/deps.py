from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.booking_request import BookingRequestRepository
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.clinic_repository import ClinicRepository
from app.services.availability_service import AvailabilityService
from app.services.booking_service import BookingService
from app.services.patient_resolution_service import PatientResolutionService


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_availability_service(
    db: Session = Depends(get_db),
) -> AvailabilityService:
    return AvailabilityService(
        schedule_repository=ScheduleRepository(db),
        appointment_repository=AppointmentRepository(db),
    )


def get_booking_service(
    db: Session = Depends(get_db),
) -> BookingService:
    schedule_repository = ScheduleRepository(db)
    appointment_repository = AppointmentRepository(db)
    patient_repository = PatientRepository(db)
    booking_request_repository = BookingRequestRepository(db)
    doctor_repository = DoctorRepository(db)

    return BookingService(
        patient_resolution_service=PatientResolutionService(patient_repository),
        availability_service=AvailabilityService(
            schedule_repository=schedule_repository,
            appointment_repository=appointment_repository,
        ),
        appointment_repository=appointment_repository,
        booking_request_repository=booking_request_repository,
        doctor_repository=doctor_repository,
    )

def get_clinic_repository(db: Session = Depends(get_db)) -> ClinicRepository:
    return ClinicRepository(db)

def get_booking_request_repository(
    db: Session = Depends(get_db),
) -> BookingRequestRepository:
    return BookingRequestRepository(db)

def get_doctor_repository(db: Session = Depends(get_db)) -> DoctorRepository:
    return DoctorRepository(db)