import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.api.deps import get_db
from app.models.database import Base

TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        future=True
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(connection):
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        future=True,
        )
    session = SessionLocal()
    try:
      yield session
    finally:
      session.close()

@pytest.fixture(scope="function")
def client(db_session):
   def override_get_db():
       try:
           yield db_session
       finally:
           pass

   app.dependency_overrides[get_db] = override_get_db
   with TestClient(app) as test_client:
      yield test_client
   app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def connection(engine):
    connection = engine.connect()
    yield connection
    connection.close()