from app.schemas.availability import (
    AvailabilityAvailableResponse,
    AvailabilityUnavailableResponse,
)
from app.schemas.common import TimeSlotSchema
from app.services.availability_service import AvailabilityResult


def _to_time_slot_schema(start_time, end_time) -> TimeSlotSchema:
    return TimeSlotSchema(start_time=start_time, end_time=end_time)


def availability_response(result: AvailabilityResult) -> AvailabilityAvailableResponse | AvailabilityUnavailableResponse:
    requested_slot = _to_time_slot_schema(
        result.requested_start,
        result.requested_end,
    )

    if result.is_available:
        return AvailabilityAvailableResponse(
            is_available=True,
            requested_slot=requested_slot,
        )

    alternative_slots = [
        _to_time_slot_schema(start, end)
        for start, end in result.alternative_slots
    ]

    return AvailabilityUnavailableResponse(
        is_available=False,
        requested_slot=requested_slot,
        alternative_slots=alternative_slots,
    )