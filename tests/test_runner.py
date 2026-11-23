import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add src to path
sys.path.append(os.path.abspath("Documents/opentrack-engine"))

from fastapi.testclient import TestClient
from src.main import app
from src.database import get_db, Base, engine
from sqlalchemy.orm import sessionmaker

# Setup test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestAutomations(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        
        # Mock K8s Service
        self.k8s_patcher = patch("src.services.k8s_service.k8s_service")
        self.mock_k8s = self.k8s_patcher.start()
        self.mock_k8s.create_cronjob.return_value = MagicMock()
        self.mock_k8s.trigger_job.return_value = MagicMock(metadata=MagicMock(name="manual-job"))
        self.mock_k8s.get_job_executions.return_value = [{"name": "job-1", "status": "succeeded"}]

    def tearDown(self):
        self.k8s_patcher.stop()
        Base.metadata.drop_all(bind=engine)

    def test_complete_flow(self):
        # 1. Create
        payload = {
            "name": "motor-test",
            "cron_expression": "*/15 * * * *",
            "source_things": {
                "thing-1": [{"property": "temp", "mapping_key": "t"}]
            },
            "ml_model": "model-v1",
            "target_events": [
                {"topic": "alerts", "event_type": "anomaly"}
            ]
        }
        res = self.client.post("/api/v1/automations/", json=payload)
        self.assertEqual(res.status_code, 200)
        auto_id = res.json()["id"]
        
        # 2. List
        res = self.client.get("/api/v1/automations/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["results"]), 1)
        
        # 3. Trigger
        res = self.client.post(f"/api/v1/automations/{auto_id}/trigger")
        self.assertEqual(res.status_code, 200)
        self.assertIn("job_name", res.json())
        
        # 4. Executions
        res = self.client.get(f"/api/v1/automations/{auto_id}/executions")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(len(res.json()) > 0)
        
        # 5. Delete
        res = self.client.delete(f"/api/v1/automations/{auto_id}")
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
