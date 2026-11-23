import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db
from src.main import app
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import src.api.v1.automations as automations_router

# Use a file-based SQLite database (./test.db) for testing
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
    # Patch the reference the router imported at import time
    mock = mocker.patch.object(automations_router, "k8s_service")
    mock.create_cronjob.return_value = MagicMock()
    mock.delete_cronjob.return_value = MagicMock()
    mock.suspend_cronjob.return_value = MagicMock()
    mock.trigger_job.return_value = MagicMock(metadata=MagicMock(name="manual-job"))
    mock.get_job_executions.return_value = [{"name": "job-1", "status": "succeeded"}]
    return mock

@pytest.fixture(autouse=True)
def mock_external_services(mocker):
    # Patch the router's service instances (not the classes) so no real WoT/Bentloy calls are made
    get_thing = mocker.patch.object(
        automations_router.wot_service, "get_thing",
        AsyncMock(return_value={"id": "thing", "properties": {}}),
    )
    get_model = mocker.patch.object(
        automations_router.bentloy_service, "get_model",
        AsyncMock(return_value={
            "inferred_model_name": "m1",
            "service_name": "bentloy-model-m1",
            "predict_endpoint": "http://bentloy-model-m1:3000/predict",
        }),
    )
    return {"get_thing": get_thing, "get_model": get_model}
