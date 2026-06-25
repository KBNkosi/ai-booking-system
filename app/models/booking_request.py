import uuid
import datetime 
from typing import List
from sqlalchemy import Uuid, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .clinic import Clinic
    from .doctor import Doctor

class BookingRequest(Base):
    __tablename__ = "booking_requests"

    booking_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    idempotency_key: Mapped[str] = mapped_column(nullable=False, unique=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False)
    clinic: Mapped["Clinic"] = relationship(back_populates="booking_requests")
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.doctor_id"), nullable=True)
    doctor: Mapped["Doctor"] = relationship(back_populates="booking_requests")
    patient_name: Mapped[str] = mapped_column(nullable=False)
    patient_email: Mapped[str] = mapped_column(nullable=True)
    patient_phone: Mapped[str] = mapped_column(nullable=False)
    requested_date: Mapped[datetime.date] = mapped_column(nullable=False)
    requested_start_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    requested_end_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
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