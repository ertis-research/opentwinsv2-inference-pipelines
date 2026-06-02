import json
from unittest.mock import MagicMock

# Mocking the K8s service and other components to simulate API behavior
def dry_run_api_logic():
    print("--- STARTING API DRY RUN ---")
    
    # 1. Simulating AutomationCreate schema input
    config = {
        "name": "prediccion-anomalias-dry-run",
        "cron_expression": "*/15 * * * *",
        "source_things": {
            "urn:dev:wot:sensor-motor-xyz": [
                { "property": "temperature", "mapping_key": "input_temp" }
            ]
        },
        "ml_model": "exp-v2",
        "target_events": [
            {"topic": "alerts", "event_type": "anomaly"}
        ]
    }

    # 2. Simulate preparation for K8s (logic from create_automation)
    env_vars = {
        "SOURCE_THINGS": json.dumps(config["source_things"]),
        "ML_MODEL": config["ml_model"],
        "TARGET_EVENTS": json.dumps(config["target_events"]),
        "KAFKA_BROKERS": "localhost:9092"
    }
    
    k8s_name = config["name"].lower().replace(" ", "-")
    
    print(f"Preparing to create CronJob: {k8s_name}")
    print(f"Schedule: {config['cron_expression']}")
    print(f"Env Vars injected into K8s:")
    for k, v in env_vars.items():
        print(f"  {k}: {v}")

    # 3. Simulate DB save
    db_item = {
        "id": 1,
        "name": config["name"],
        "status": "active",
        "source_things": json.dumps(config["source_things"]),
        "target_events": json.dumps(config["target_events"])
    }
    print(f"Simulated DB Save: {db_item['name']} with ID {db_item['id']}")

    # 4. Simulate response formatting
    response = db_item.copy()
    response["source_things"] = json.loads(db_item["source_things"])
    response["target_events"] = json.loads(db_item["target_events"])
    
    print(f"Final API Response Format:")
    print(json.dumps(response, indent=2))
    
    print("--- API DRY RUN COMPLETED SUCCESSFULLY ---")

if __name__ == "__main__":
    dry_run_api_logic()
