from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    doctor_id: UUID
    clinic_id: UUID
    name: str
    specialty: str
    created_at: datetime