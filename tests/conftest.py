from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.api.main import app
from src.db.session import get_db
from src.db.models import Base

# Setup SQLite in-memory for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create the database and tables."""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a clean database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Provide a TestClient with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def sample_companion_payload():
    """Return a sample payload for a companion journey."""
    return {
        "userId": 1,
        "departureAddress": "Paris",
        "arrivalAddress": "Lyon",
        "departureLon": 2.3522,
        "departureLat": 48.8566,
        "arrivalLon": 4.8357,
        "arrivalLat": 45.7640,
        "departureTime": datetime(2024, 5, 1, 10, 0),
        "arrivalTime": datetime(2024, 5, 1, 14, 0)
    }

@pytest.fixture
def sample_passenger_payload():
    """Return a sample payload for a passenger journey."""
    return {
        "userId": 2,
        "departureAddress": "Paris",
        "arrivalAddress": "Lyon",
        "departureLon": 2.3522,
        "departureLat": 48.8566,
        "arrivalLon": 4.8357,
        "arrivalLat": 45.7640,
        "departureTime": datetime(2024, 5, 1, 10, 15),
        "arrivalTime": datetime(2024, 5, 1, 13, 45)
    }
