import asyncio
import os
import json
import uuid
import requests
import sys
import socket 
from datetime import datetime
from kafka import KafkaProducer
from src.services.wot_service import WotService
from src.services.bentloy_service import BentloyService
from cloudevents.v1.http import from_dict
from cloudevents.v1.conversion import to_structured

wot_service = WotService(os.getenv("THINGS_SERVICE_URL", ""))
bentloy_service = BentloyService(os.getenv("BENTLOY_SERVICE_URL", ""))

async def get_thing_state(thing_id, properties):
    """
    Fetches the wanted properties from the current state of the thing.

    Values are passed on as the Thing reports them (numbers, booleans, text, dates...): the model
    preprocessing converts each one according to its input feature type. A property that cannot be
    read is sent as a missing value (None), which the model fills in, instead of a made-up number.
    """
    try:
        state = await wot_service.get_thing_state(thing_id)
    except Exception as e:
        print(f"Error while retrieving the state of {thing_id}: {e}")
        state = None
    if state is None:
        print(f"The state of {thing_id} could not be read: its properties are sent as missing values")
        return {prop: None for prop in properties}

    results = {}
    for prop in properties:
        prop_data = state.get(prop)
        if not isinstance(prop_data, dict) or prop_data.get("value") is None:
            print(f"Property {prop} of {thing_id} has no value: it is sent as a missing value")
            results[prop] = None
        else:
            results[prop] = prop_data["value"]
    return results

async def run_inference(inputs_used, model_id):
    print(f"Running inference with model: {model_id} and inputs: {inputs_used}")
    prediction_response = await bentloy_service.infere_with_model(model_name=model_id, input=inputs_used)
    if isinstance(prediction_response, dict) and "predictions" in prediction_response:
        data = prediction_response["predictions"][0]
    # If the variable is the list of predictions itself
    elif isinstance(prediction_response, list):
        data = prediction_response[0]
    # If the variable is already the single prediction dictionary
    else:
        data = prediction_response

    # Extract only the keys ending in "_predictions" and strip the suffix
    return {
        key.replace("_predictions", ""): value 
        for key, value in data.items() 
        if key.endswith("_predictions")
    }

async def main():
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
        states = await get_thing_state(thing_id, props_to_fetch)
        
        # Map to inputs_used
        for m in mappings:
            inputs_used[m["mapping_key"]] = states.get(m["property"])

    # 2. Run Model Inference
    result = await run_inference(inputs_used, ml_model)

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
                "outputs": result,
                "inputs": inputs_used
            } 
            
            # Merge attributes and data into one dict for from_dict
            event_dict = attributes.copy()
            event_dict["data"] = data
            
            event = from_dict(event_dict)
            headers, body = to_structured(event)
            
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
    asyncio.run(main())
