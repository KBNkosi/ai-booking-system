import uuid
import datetime
from dataclasses import dataclass, field
from typing import List

from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.appointment_repository import AppointmentRepository


# Structured return type for availability checks
@dataclass
class AvailabilityResult:
    is_available: bool
    requested_start: datetime.datetime
    requested_end: datetime.datetime
    alternative_slots: List[tuple] = field(default_factory=list)


# Core service for checking availability and finding alternatives
class AvailabilityService:
    def __init__(
        self,
        schedule_repository: ScheduleRepository,
        appointment_repository: AppointmentRepository
    ):
        self.schedule_repository = schedule_repository
        self.appointment_repository = appointment_repository

    # Main method: check if a slot is available and find alternatives
    def check_availability(
        self,
        doctor_id: uuid.UUID,
        requested_start: datetime.datetime,
        requested_end: datetime.datetime
    ) -> AvailabilityResult:

        # Get doctor schedules for the requested date range
        schedules = self.schedule_repository.get_for_date_range(
            doctor_id, requested_start, requested_end
        )

        # If no schedule exists, the slot is not available
        if not schedules:
            return AvailabilityResult(
                is_available=False,
                requested_start=requested_start,
                requested_end=requested_end,
                alternative_slots=[]
            )

        schedule_start = min(s.start_time for s in schedules)
        schedule_end = max(s.end_time for s in schedules)

        # Get existing appointments for the same doctor in the same date range
        existing_appointments = self.appointment_repository.get_for_doctor_in_range(
            doctor_id, schedule_start, schedule_end
        )

        # Check if the requested slot overlaps with any existing appointments
        slot_is_free = not self._overlaps_any_appointment(
            requested_start, requested_end, existing_appointments
        )

        # If the slot is free, return it as available
        if slot_is_free:
            return AvailabilityResult(
                is_available=True,
                requested_start=requested_start,
                requested_end=requested_end
            )

        # Calculate duration and find alternatives
        duration = requested_end - requested_start
        alternatives = self._find_alternative_slots(
            schedules, existing_appointments, duration
        )

       # Return the result with found alternatives
        return AvailabilityResult(
            is_available=False,
            requested_start=requested_start,
            requested_end=requested_end,
            alternative_slots=alternatives
        )
    
    # Helper method to check for overlaps with existing appointments    
    def _overlaps_any_appointment(
        self,
        requested_start: datetime.datetime,
        requested_end: datetime.datetime,
        appointments: List[Appointment]
    ) -> bool:
 
      # Iterate over existing appointments and check for overlaps
      for appointment in appointments:
        if requested_start < appointment.end_time and requested_end > appointment.start_time:
            return True

      return False

    # Helper method to find alternative slots
    def _find_alternative_slots(
        self,
        schedules: List[Schedule],
        existing_appointments: List[Appointment],
        duration: datetime.timedelta,
        max_suggestions: int = 3
    ) -> List[tuple]:

      alternatives = []

      # Iterate over doctor schedules to find free slots
      for schedule in schedules:
        # Get booked times for the current schedule
        booked_times = sorted(
            [(a.start_time, a.end_time) for a in existing_appointments
            if a.start_time >= schedule.start_time and a.end_time <= schedule.end_time],
            key=lambda x: x[0]
        )
        # Initialize cursor to schedule start time
        cursor = schedule.start_time

        # Iterate over booked times to find free slots
        for booked_start, booked_end in booked_times:
            # If there's a gap before the next booking, add it as an alternative
            if cursor + duration <= booked_start:
                alternatives.append((cursor, cursor + duration))
                # Stop if we've found enough alternatives
                if len(alternatives) >= max_suggestions:
                    return alternatives
            # Move cursor to end of current booking
            cursor = max(cursor, booked_end)

        # Check for free slot after last booking
        if cursor + duration <= schedule.end_time:
            alternatives.append((cursor, cursor + duration))
        # Stop if we've found enough alternatives
        if len(alternatives) >= max_suggestions:
            return alternatives

      return alternatives


        

    