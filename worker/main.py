import os
import json
import uuid
import requests
import sys
import socket 
from datetime import datetime
from kafka import KafkaProducer
from cloudevents.v1.http import from_dict
from cloudevents.v1.conversion import to_binary

# --- LABORATORY NETWORK HACK ---

def resolve_laboratory_ip():
    original_getaddrinfo = socket.getaddrinfo
    def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        # Redirect ANY non-local host to the lab IP
        target_host = host
        if host not in ["localhost", "127.0.0.1"] and not host.startswith("10."):
            target_host = "192.168.218.12"
        return original_getaddrinfo(target_host, port, family, type, proto, flags)
    socket.getaddrinfo = patched_getaddrinfo

resolve_laboratory_ip()
# ------------------------------------

def get_thing_state(thing_id, properties):
    """
    Performs an HTTP request to the things-service to get the real state of the Thing.
    """
    base_url = os.getenv("THINGS_SERVICE_URL")
    # Build the URL based on the API documentation: {base_url}/things/things/{thing_id}/state
    url = f"{base_url.rstrip('/')}/things/things/{thing_id}/state"
    
    print(f"Fetching state for thing: {thing_id} at {url}")
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        state_data = response.json()
        
        print(f"Successfully fetched state for {thing_id}: {state_data}")
        
        # The API returns { "prop": { "value": X, "lastUpdate": Y } }
        results = {}
        for prop in properties:
            prop_data = state_data.get(prop, {})
            val = prop_data.get("value")
            results[prop] = float(val) if val is not None else 0.0
            
        return results
    except Exception as e:
        print(f"Error fetching thing state from {url}: {e}")
        return {prop: 0.0 for prop in properties}

def run_inference(inputs_used, model_id):
    # Mocking inference logic
    print(f"Running inference with model: {model_id} and inputs: {inputs_used}")
    return {"prediction": 0.89, "confidence": 0.95}

def main():
    print("Worker starting...")
    
    # Read configuration from env
    source_things_raw = os.getenv("SOURCE_THINGS", "{}")
    source_things = json.loads(source_things_raw)
    ml_model = os.getenv("ML_MODEL", "default-model")
    target_events_raw = os.getenv("TARGET_EVENTS", "[]")
    target_events = json.loads(target_events_raw)
    
    # Use the new ports as default if the env var is not present
    kafka_brokers = os.getenv("KAFKA_BROKERS")

    # 1. Collect Data from WoT based on mapping
    inputs_used = {}
    for thing_id, mappings in source_things.items():
        # Get list of properties to fetch
        props_to_fetch = [m["property"] for m in mappings]
        states = get_thing_state(thing_id, props_to_fetch)
        
        # Map to inputs_used
        for m in mappings:
            inputs_used[m["mapping_key"]] = states.get(m["property"], 0.0)

    # 2. Run Model Inference
    result = run_inference(inputs_used, ml_model)

    # 3. Publish to Kafka for each target event
    print(f"Connecting to Kafka at: {kafka_brokers}")
    try:
        producer = KafkaProducer(
            bootstrap_servers=kafka_brokers.split(","),
            # api_version=(0, 10),          # Removed forced old version for compatibility with modern cluster
            acks=1,                       # Changed to 1 to ensure broker receives the message
            retries=3,                    # Added retries for robustness
            request_timeout_ms=30000,     # 30 seconds
            metadata_max_age_ms=300000,   # 5 minutes
            max_block_ms=30000            # 30 seconds
        )
    except Exception as e:
        print(f"CRITICAL: Failed to connect to Kafka: {e}")
        sys.exit(1)
    
    try:
        for event_cfg in target_events:
            topic = event_cfg["topic"]
            event_type = event_cfg["event_type"]
            
            attributes = {
                "type": event_type,
                "source": f"urn:model:{ml_model}",
                "datacontenttype": "application/json",
                "time": datetime.utcnow().isoformat() + "Z",
                "specversion": "1.0",
                "id": str(uuid.uuid4())
            }
            
            data = {
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "inputs_used": inputs_used
            }
            
            # Merge attributes and data into one dict for from_dict
            event_dict = attributes.copy()
            event_dict["data"] = data
            
            event = from_dict(event_dict)
            headers, body = to_binary(event)
            
            # Convert CloudEvents headers (dict) to Kafka headers (list of tuples with bytes)
            kafka_headers = [
                (k, v.encode("utf-8") if isinstance(v, str) else v) 
                for k, v in headers.items()
            ]
            
            producer.send(topic, value=body, headers=kafka_headers)
            print(f"Result sent to producer for topic [{topic}] with type [{event_type}]")
        
        print("Flushing Kafka producer (timeout=180s)...")
        producer.flush(timeout=180) 
        print("Flush completed.")
    except Exception as e:
        print(f"CRITICAL: Error during Kafka publication: {e}")
        
    print("Worker finished successfully.")

if __name__ == "__main__":
    main()
