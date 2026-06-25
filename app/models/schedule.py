import uuid
import datetime 
from typing import List
from sqlalchemy import Uuid, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .doctor import Doctor

class Schedule(Base):
    __tablename__ = "schedules"

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.doctor_id"), nullable=False)
    doctor: Mapped["Doctor"] = relationship(back_populates="schedules")
    start_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime.datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )