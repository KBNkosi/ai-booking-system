import uuid
import datetime
from sqlalchemy import Uuid, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .clinic import Clinic

class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.clinic_id"), nullable=False)
    clinic: Mapped["Clinic"] = relationship(back_populates="patients")
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )