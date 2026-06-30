# verify_models.py
from sqlalchemy.orm import configure_mappers

from app.models.database import Base
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.booking_request import BookingRequest
    
configure_mappers()

print("All relationships have been configured successfully.")