import uuid
import datetime
from sqlalchemy import Uuid, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .clinic import Clinic
    from .appointment import Appointment
    from .schedule import Schedule
    from .booking_request import BookingRequest

class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False)
    clinic: Mapped["Clinic"] = relationship(back_populates="doctors")
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="doctor")
    booking_requests: Mapped[List["BookingRequest"]] = relationship(back_populates="doctor")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="doctor")
    name: Mapped[str] = mapped_column(nullable=False)
    specialty: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

