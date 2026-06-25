import uuid
import datetime 
from typing import List
from sqlalchemy import Uuid, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .doctor import Doctor
    from .patient import Patient
    from .appointment import Appointment
    from .booking_request import BookingRequest
    

class Clinic(Base):
    __tablename__ = "clinics"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
        )
    name: Mapped[str] = mapped_column(nullable=False)
    doctors: Mapped[List["Doctor"]] = relationship(back_populates="clinic")
    patients: Mapped[List["Patient"]] = relationship(back_populates="clinic")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="clinic")
    booking_requests: Mapped[List["BookingRequest"]] = relationship(back_populates="clinic")
    created_at:Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

