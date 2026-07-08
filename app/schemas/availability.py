from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import TimeSlotSchema


class AvailabilityQueryParams(BaseModel):
    requested_start_time: datetime


class AvailabilityAvailableResponse(BaseModel):
    is_available: Literal[True]
    requested_slot: TimeSlotSchema


class AvailabilityUnavailableResponse(BaseModel):
    is_available: Literal[False]
    requested_slot: TimeSlotSchema
    alternative_slots: list[TimeSlotSchema] = Field(default_factory=list)


AvailabilityResponse = AvailabilityAvailableResponse | AvailabilityUnavailableResponse

