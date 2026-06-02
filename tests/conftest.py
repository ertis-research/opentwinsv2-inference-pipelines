import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db
from src.main import app
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_k8s_service(mocker):
    # Mock the k8s_service instance in the service module
    mock = mocker.patch("src.services.k8s_service.k8s_service")
    mock.create_cronjob.return_value = MagicMock()
    mock.delete_cronjob.return_value = MagicMock()
    mock.suspend_cronjob.return_value = MagicMock()
    mock.trigger_job.return_value = MagicMock(metadata=MagicMock(name="manual-job"))
    mock.get_job_executions.return_value = [{"name": "job-1", "status": "succeeded"}]
    return mock
