"""
conftest.py — Shared test fixtures for the AI Clinic Booking System test suite.

Isolation strategy:
  Each test function gets its own fresh SQLite in-memory database, created
  and torn down entirely within that test.  This gives perfect isolation
  without any reliance on savepoint / rollback semantics that differ
  across database engines.

  A shared session-scoped engine is NOT used.  Instead, each function-scoped
  fixture creates a new engine pointing at `sqlite:///:memory:` using a
  StaticPool so that every connection to that URL sees the same in-memory DB.
"""

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api.deps import get_db
from app.models.database import Base
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment


# ---------------------------------------------------------------------------
# Per-test in-memory SQLite engine + schema
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    """Create a fresh in-memory SQLite engine for each test."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


# ---------------------------------------------------------------------------
# Session — one session per test, bound to the per-test engine
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(engine):
    """Return a SQLAlchemy session bound to the per-test in-memory database."""
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# HTTP test client — wires FastAPI's get_db to the per-test db_session
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session):
    """
    Return a FastAPI TestClient whose database operations go through
    the per-test db_session (and therefore the per-test in-memory SQLite DB).
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.flush()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Data factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_clinic(db_session):
    """Factory: create and flush a Clinic row."""
    def _make(name: str = "Test Clinic") -> Clinic:
        clinic = Clinic(name=name)
        db_session.add(clinic)
        db_session.flush()
        return clinic
    return _make


@pytest.fixture()
def make_doctor(db_session):
    """Factory: create and flush a Doctor row."""
    def _make(
        clinic: Clinic,
        name: str = "Dr. Test",
        specialty: str = "General Practitioner",
    ) -> Doctor:
        doctor = Doctor(name=name, specialty=specialty, clinic=clinic)
        db_session.add(doctor)
        db_session.flush()
        return doctor
    return _make


@pytest.fixture()
def make_schedule(db_session):
    """Factory: create and flush a Schedule row."""
    def _make(
        doctor: Doctor,
        start_time: datetime.datetime = datetime.datetime(2025, 6, 1, 9, 0),
        end_time: datetime.datetime = datetime.datetime(2025, 6, 1, 17, 0),
    ) -> Schedule:
        schedule = Schedule(
            doctor=doctor,
            start_time=start_time,
            end_time=end_time,
        )
        db_session.add(schedule)
        db_session.flush()
        return schedule
    return _make


@pytest.fixture()
def make_appointment(db_session):
    """Factory: create and flush an Appointment row."""
    def _make(
        clinic: Clinic,
        doctor: Doctor,
        patient_id,
        start_time: datetime.datetime = datetime.datetime(2025, 6, 1, 9, 0),
        end_time: datetime.datetime = datetime.datetime(2025, 6, 1, 9, 30),
        status: str = "CONFIRMED",
    ) -> Appointment:
        appt = Appointment(
            clinic_id=clinic.clinic_id,
            doctor_id=doctor.doctor_id,
            patient_id=patient_id,
            start_time=start_time,
            end_time=end_time,
            status=status,
        )
        db_session.add(appt)
        db_session.flush()
        return appt
    return _make