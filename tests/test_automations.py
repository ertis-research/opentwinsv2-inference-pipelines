import pytest
import json

def test_create_automation(client):
    payload = {
        "name": "test-automation",
        "cron_expression": "*/5 * * * *",
        "source_things": {
            "urn:dev:wot:sensor-1": [
                {"property": "temp", "mapping_key": "t"}
            ]
        },
        "ml_model": "test-model",
        "target_events": [
            {"topic": "test-topic", "event_type": "test-event"}
        ]
    }
    response = client.post("/api/v1/automations/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-automation"
    assert data["status"] == "active"
    assert "id" in data

def test_list_automations(client):
    # Create one first
    client.post("/api/v1/automations/", json={
        "name": "auto-1",
        "cron_expression": "0 * * * *",
        "source_things": {},
        "ml_model": "m1",
        "target_events": []
    })
    
    response = client.get("/api/v1/automations/")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_get_automation(client):
    create_res = client.post("/api/v1/automations/", json={
        "name": "auto-2",
        "cron_expression": "0 * * * *",
        "source_things": {"t1": []},
        "ml_model": "m1",
        "target_events": []
    })
    auto_id = create_res.json()["id"]
    
    response = client.get(f"/api/v1/automations/{auto_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "auto-2"

def test_update_status(client):
    create_res = client.post("/api/v1/automations/", json={
        "name": "auto-3",
        "cron_expression": "0 * * * *",
        "source_things": {},
        "ml_model": "m1",
        "target_events": []
    })
    auto_id = create_res.json()["id"]
    
    # Pause
    response = client.patch(f"/api/v1/automations/{auto_id}/status", json={"status": "paused"})
    assert response.status_code == 200
    assert response.json()["status"] == "paused"

def test_delete_automation(client):
    create_res = client.post("/api/v1/automations/", json={
        "name": "auto-4",
        "cron_expression": "0 * * * *",
        "source_things": {},
        "ml_model": "m1",
        "target_events": []
    })
    auto_id = create_res.json()["id"]
    
    response = client.delete(f"/api/v1/automations/{auto_id}")
    assert response.status_code == 200
    
    # Verify it's gone
    get_res = client.get(f"/api/v1/automations/{auto_id}")
    assert get_res.status_code == 404

def test_trigger_automation(client):
    create_res = client.post("/api/v1/automations/", json={
        "name": "auto-5",
        "cron_expression": "0 * * * *",
        "source_things": {},
        "ml_model": "m1",
        "target_events": []
    })
    auto_id = create_res.json()["id"]
    
    response = client.post(f"/api/v1/automations/{auto_id}/trigger")
    assert response.status_code == 200
    assert "job_name" in response.json()

def test_get_executions(client):
    create_res = client.post("/api/v1/automations/", json={
        "name": "auto-6",
        "cron_expression": "0 * * * *",
        "source_things": {},
        "ml_model": "m1",
        "target_events": []
    })
    auto_id = create_res.json()["id"]
    
    response = client.get(f"/api/v1/automations/{auto_id}/executions")
    assert response.status_code == 200
    assert len(response.json()) > 0
