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
    assert len(response.json()["results"]) == 1

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


def _seed(db_session, n, prefix="auto"):
    from src.models.automation import Automation
    for i in range(1, n + 1):
        db_session.add(Automation(
            name=f"{prefix}-{i}", cron_expression="0 * * * *", status="active",
            source_things=json.dumps({}), ml_model="m1", target_events=json.dumps([]),
        ))
    db_session.commit()


def test_list_pagination_first_and_second_page(client, db_session):
    _seed(db_session, 5)
    r = client.get("/api/v1/automations/?page=1&pageSize=2").json()
    assert [a["name"] for a in r["results"]] == ["auto-1", "auto-2"]
    assert r["pagination"] == {
        "total_items": 5, "total_pages": 3, "current_page": 1,
        "page_size": 2, "has_next": True, "has_prev": False,
    }
    r = client.get("/api/v1/automations/?page=2&pageSize=2").json()
    assert [a["name"] for a in r["results"]] == ["auto-3", "auto-4"]
    assert r["pagination"]["has_next"] is True
    assert r["pagination"]["has_prev"] is True


def test_list_pagination_last_page(client, db_session):
    _seed(db_session, 5)
    r = client.get("/api/v1/automations/?page=3&pageSize=2").json()
    assert [a["name"] for a in r["results"]] == ["auto-5"]
    assert r["pagination"]["has_next"] is False
    assert r["pagination"]["has_prev"] is True


def test_list_pagination_out_of_range(client, db_session):
    _seed(db_session, 3)
    r = client.get("/api/v1/automations/?page=10&pageSize=2").json()
    assert r["results"] == []
    assert r["pagination"]["total_items"] == 3
    assert r["pagination"]["has_next"] is False


def test_list_pagination_empty(client):
    r = client.get("/api/v1/automations/").json()
    assert r["results"] == []
    assert r["pagination"]["total_items"] == 0
    assert r["pagination"]["total_pages"] == 0
    assert r["pagination"]["has_next"] is False
    assert r["pagination"]["has_prev"] is False


def test_list_pagination_search(client, db_session):
    _seed(db_session, 3, "alpha")
    _seed(db_session, 2, "beta")
    r = client.get("/api/v1/automations/?search=beta").json()
    assert r["pagination"]["total_items"] == 2
    assert all("beta" in a["name"] for a in r["results"])


def test_list_page_zero_is_422(client):
    assert client.get("/api/v1/automations/?page=0").status_code == 422
