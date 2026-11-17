# OpenTrack Engine

OpenTrack Engine is a high-performance ML inference orchestration system designed for Industrial IoT (IIoT) environments. It leverages the **Web of Things (WoT)** standard for device interaction and uses **Kubernetes** to manage ephemeral, scheduled, and on-demand inference workloads. Results are published to **Apache Kafka** following the **CloudEvents v1.0** specification.

## Architecture Overview

The system follows a control-plane/data-plane separation:

1.  **Control Plane (REST API)**: Built with FastAPI, it manages the lifecycle of automations, persisting metadata in SQLite and orchestrating Kubernetes resources.
2.  **Data Plane (Ephemeral Worker)**: Lightweight Python-based containers triggered by Kubernetes `CronJobs` or `Jobs`. They fetch real-time telemetry from WoT "Things", run inference, and terminate.
3.  **Messaging Layer (Kafka)**: A reliable bus for distributing inference results to downstream consumers (e.g., Dashboards, ERPs, Alert Systems).

## Core Features

*   **Native K8s Orchestration**: Automations are translated into `CronJobs`. Manual triggers create instant `Jobs`.
*   **WoT Integration**: Dynamic data collection based on Thing Descriptions (TD).
*   **Standardized Messaging**: Native support for **CloudEvents** over Kafka.
*   **Concurrency Control**: Prevents job overlap using Kubernetes `Forbid` policy.
*   **Full Observability**: Track execution history and logs directly via the API.

## 🛠 Prerequisites

*   **Kubernetes Cluster**: Docker Desktop, Minikube, or a production-grade cluster.
*   **Apache Kafka**: Accessible brokers for message publication.
*   **Python 3.11+**: For local development and API execution.
*   **Docker**: For building worker images.

## Configuration

The system uses a `.env` file for environment-specific settings.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `KUBERNETES_NAMESPACE` | K8s namespace for worker execution | (Required) |
| `KAFKA_BROKERS` | Comma-separated list of Kafka brokers | (Required) |
| `THINGS_SERVICE_URL` | Base URL for the WoT Things Service | (Required) |
| `BENTLOY_SERVICE_URL` | Base URL for the Bentloy Service | (Required) |
| `WORKER_IMAGE` | Docker image for the worker | `opentrack-worker:latest` |
| `DATABASE_URL` | SQLite database path | `sqlite:///./automations.db` |

## Quick Start

### 1. Environment Setup
```bash
# Clone and enter the repo
cd opentrack-engine

# Create and configure .env
cp .env.example .env  # Edit with your laboratory IPs

# Install dependencies
pip install -r requirements.txt
```

### 2. Build the Worker Image
```bash
docker build -t opentrack-worker:latest ./worker
```

### 3. Deploy Kubernetes RBAC
```bash
kubectl apply -f rbac.yaml
```

### 4. Run the API
```bash
$env:PYTHONPATH = "."
uvicorn src.main:app --port 8000 --reload
```
Access the interactive documentation at `http://localhost:8000/docs`.

## Deployment

Replace the dynamic values in the commands before running them.

### 1. Create worker image on registry

```bash
docker build -t <YOUR_REGISTRY>/<YOUR_PROJECT>/opentrack-worker:latest ./worker/
```

### 2. Push worker image into registry

```bash
docker push <YOUR_REGISTRY>/<YOUR_PROJECT>/opentrack-worker:latest
```

### 3. Create API image on registry

```bash
docker build -t <YOUR_REGISTRY>/<YOUR_PROJECT>/opentrack:latest ./
```

### 4. Push API image into registry

```bash
docker push <YOUR_REGISTRY>/<YOUR_PROJECT>/opentrack:latest
```

### 5. Kubernetes Deployment

**IMPORTANT: REPLACE DYNAMIC DATA IN YAML FILES BEFORE RUNNING**

Run the commands on the following order:

```bash
kubectl create secret generic opentrack-cont-creds --from-env-file=.env -n <YOUR_K8S_NAMESPACE>
```

```bash
kubectl apply -f ./deployment.yaml -n <YOUR_K8S_NAMESPACE>
```

```bash
kubectl apply -f ./rbac.yaml -n <YOUR_K8S_NAMESPACE>
```

After that, check with the following command the pod status:

```bash
kubectl get pods -n <YOUR_K8S_NAMESPACE>
```

When it has reaches Ready status, look for the service IP address and port that belongs to opentrack

```bash
kubectl get svc -n <YOUR_K8S_NAMESPACE>
```

## 📖 API Usage Example

### Create an Automation
**POST** `/api/v1/automations/`
```json
{
  "name": "Machine Temperature Monitor",
  "cron_expression": "*/5 * * * *",
  "ml_model": "temp-anomaly-v1",
  "source_things": {
    "urn:dev:ops:sensor-01": [
      { "property": "temperature", "mapping_key": "t1" }
    ]
  },
  "target_events": [
    { "topic": "alerts.temperature", "event_type": "io.opentrack.anomaly" }
  ]
}
```

## Testing

Run the test suite to verify the integration:

```bash
pytest tests/
```
---

## Related Documentation

*   [RUNBOOK.txt](./docs/RUNBOOK.txt): Technical deployment and troubleshooting guide.
*   [PROJECT_EXPLANATION.txt](./docs/PROJECT_EXPLANATION.txt): Architectural deep-dive.
