import uuid
import datetime 

from sqlalchemy import Uuid, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Clinic(Base):
    __tablename__ = "clinics"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
        )
    name: Mapped[str] = mapped_column(nullable=False)
    created_at:Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

