"""
test_availability_service.py — Unit tests for AvailabilityService.check_availability.

Repositories are mocked so these tests exercise only the scheduling logic:
  - no schedule → unavailable
  - schedule exists, no conflicts → available
  - schedule exists, overlapping appointment → unavailable + alternatives
  - alternative-slot finder covers edge cases
"""

import datetime
import uuid
from unittest.mock import MagicMock

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.services.availability_service import AvailabilityService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOCTOR_ID = uuid.uuid4()

SLOT_START = datetime.datetime(2025, 6, 1, 9, 0)
SLOT_END = SLOT_START + datetime.timedelta(minutes=30)


def _make_service(schedules=None, appointments=None):
    """Return an AvailabilityService with mocked repositories."""
    schedule_repo = MagicMock()
    schedule_repo.get_for_date_range.return_value = schedules or []

    appt_repo = MagicMock()
    appt_repo.get_for_doctor_in_range.return_value = appointments or []

    return AvailabilityService(
        schedule_repository=schedule_repo,
        appointment_repository=appt_repo,
    )


def _make_schedule(
    start=datetime.datetime(2025, 6, 1, 8, 0),
    end=datetime.datetime(2025, 6, 1, 17, 0),
):
    s = Schedule()
    s.schedule_id = uuid.uuid4()
    s.doctor_id = DOCTOR_ID
    s.start_time = start
    s.end_time = end
    return s


def _make_appointment(
    start=SLOT_START,
    end=SLOT_END,
):
    a = Appointment()
    a.appointment_id = uuid.uuid4()
    a.doctor_id = DOCTOR_ID
    a.start_time = start
    a.end_time = end
    a.status = "CONFIRMED"
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_unavailable_when_no_schedule_exists():
    """No schedule row → is_available must be False."""
    svc = _make_service(schedules=[])  # no schedules

    result = svc.check_availability(doctor_id=DOCTOR_ID, requested_start=SLOT_START)

    assert result.is_available is False
    assert result.requested_start == SLOT_START
    assert result.requested_end == SLOT_END
    assert result.alternative_slots == []


def test_available_when_schedule_exists_and_no_appointments():
    """Schedule covers the slot and no existing appointments → is_available=True."""
    svc = _make_service(schedules=[_make_schedule()], appointments=[])

    result = svc.check_availability(doctor_id=DOCTOR_ID, requested_start=SLOT_START)

    assert result.is_available is True
    assert result.requested_start == SLOT_START
    assert result.requested_end == SLOT_END


def test_unavailable_when_appointment_overlaps():
    """Existing appointment in the same slot → is_available=False."""
    existing = _make_appointment(start=SLOT_START, end=SLOT_END)
    svc = _make_service(schedules=[_make_schedule()], appointments=[existing])

    result = svc.check_availability(doctor_id=DOCTOR_ID, requested_start=SLOT_START)

    assert result.is_available is False


def test_unavailable_when_partial_overlap_start():
    """Existing appointment starts before and ends inside the requested slot."""
    existing = _make_appointment(
        start=SLOT_START - datetime.timedelta(minutes=15),
        end=SLOT_START + datetime.timedelta(minutes=15),
    )
    svc = _make_service(schedules=[_make_schedule()], appointments=[existing])

    result = svc.check_availability(doctor_id=DOCTOR_ID, requested_start=SLOT_START)

    assert result.is_available is False


def test_finds_alternative_slots_when_unavailable():
    """
    When the requested slot is booked, the service must suggest alternative
    slots from the same schedule.

    The implementation finds ALL free 30-minute windows within the schedule,
    including any gaps before the booked slot.  The schedule is 08:00–17:00
    and the booked slot is 09:00–09:30, so there is a 1h free window at
    08:00–09:00 and then another free window starting at 09:30.
    """
    # Schedule: 08:00–17:00.  Booked: 09:00–09:30.
    existing = _make_appointment(start=SLOT_START, end=SLOT_END)
    svc = _make_service(schedules=[_make_schedule()], appointments=[existing])

    result = svc.check_availability(doctor_id=DOCTOR_ID, requested_start=SLOT_START)

    assert result.is_available is False
    assert len(result.alternative_slots) >= 1

    schedule_start = datetime.datetime(2025, 6, 1, 8, 0)
    schedule_end = datetime.datetime(2025, 6, 1, 17, 0)

    for alt_start, alt_end in result.alternative_slots:
        # Each alternative must be a 30-minute slot
        assert alt_end - alt_start == datetime.timedelta(minutes=30)
        # Each alternative must lie within the schedule window
        assert alt_start >= schedule_start
        assert alt_end <= schedule_end
        # No alternative must overlap with the booked slot
        assert not (alt_start < SLOT_END and alt_end > SLOT_START)


def test_no_alternatives_when_schedule_fully_booked():
    """
    When the entire schedule is covered by appointments, the alternative_slots
    list must be empty.
    """
    # One appointment that covers the whole working day
    all_day = _make_appointment(
        start=datetime.datetime(2025, 6, 1, 8, 0),
        end=datetime.datetime(2025, 6, 1, 17, 0),
    )
    svc = _make_service(schedules=[_make_schedule()], appointments=[all_day])

    result = svc.check_availability(doctor_id=DOCTOR_ID, requested_start=SLOT_START)

    assert result.is_available is False
    assert result.alternative_slots == []
