import json
import uuid
from datetime import datetime

# Standalone mock for verification of worker logic
def mock_get_thing_state(thing_id, properties):
    print(f"[MOCK] Fetching {properties} for {thing_id}")
    return {p: (85.4 if "temp" in p else 1.2 if "vib" in p else 45.0) for p in properties}

def mock_run_inference(inputs, model):
    print(f"[MOCK] Running {model} with inputs {inputs}")
    return {"prediction": 0.89, "confidence": 0.95}

def verify_worker_logic():
    # Test Configuration (matches user example)
    source_things = {
        "urn:dev:wot:sensor-motor-xyz": [
            { "property": "temperature", "mapping_key": "input_temp" },
            { "property": "vibration", "mapping_key": "input_vib" }
        ],
        "urn:dev:wot:sensor-ambiente-abc": [
            { "property": "humidity", "mapping_key": "input_hum" }
        ]
    }
    ml_model = "exp-random-forest-v2"
    target_events = [
        {"topic": "wot.alertas.criticas", "event_type": "com.tuempresa.wot.anomalia.detectada"}
    ]

    print("--- STARTING WORKER LOGIC VERIFICATION ---")
    
    # 1. Map inputs
    inputs_used = {}
    for t_id, mappings in source_things.items():
        props = [m["property"] for m in mappings]
        states = mock_get_thing_state(t_id, props)
        for m in mappings:
            inputs_used[m["mapping_key"]] = states.get(m["property"])
    
    print(f"Mapped Inputs: {json.dumps(inputs_used, indent=2)}")

    # 2. Inference
    result = mock_run_inference(inputs_used, ml_model)
    
    # 3. CloudEvent generation
    for te in target_events:
        event = {
            "specversion": "1.0",
            "id": str(uuid.uuid4()),
            "source": f"urn:model:{ml_model}",
            "type": te["event_type"],
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": {
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "inputs_used": inputs_used
            }
        }
        print(f"Generated CloudEvent for topic [{te['topic']}]:")
        print(json.dumps(event, indent=2))

if __name__ == "__main__":
    verify_worker_logic()
