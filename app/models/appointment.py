import uuid
import datetime 
from typing import List
from sqlalchemy import Uuid, DateTime, func, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .clinic import Clinic
    from .doctor import Doctor
    from .patient import Patient
    from .booking_request import BookingRequest

class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_doctor_id", "doctor_id"),
        Index("ix_appointments_clinic_id", "clinic_id"),
        Index("ix_appointments_start_time", "start_time"),
    )

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False)
    clinic: Mapped["Clinic"] = relationship(back_populates="appointments")
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.doctor_id"), nullable=False)
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.patient_id"), nullable=False)
    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    booking_request: Mapped[List["BookingRequest"]] = relationship(back_populates="appointment")
    start_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )