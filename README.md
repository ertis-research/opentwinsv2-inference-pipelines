# OpenTrack Engine

OpenTrack Engine is an ML inference automation engine based on microservices, designed to operate in IoT (Internet of Things) environments using the **Web of Things (WoT)** standard and notifying results via **Kafka**.

## Features

*   **REST API (FastAPI)**: Full lifecycle management of automations.
*   **Native Kubernetes Orchestration**: Uses `CronJobs` for scheduled executions and `Jobs` for on-demand runs.
*   **Ephemeral Worker**: Lightweight containers that collect real sensor data, run inference, and terminate after completing their task.
*   **WoT Integration**: Connection with external "Things" services via HTTP.
*   **CloudEvents**: Results published to Kafka following industry standards.

## Requirements

*   Kubernetes (Docker Desktop, Minikube, or real cluster).
*   Apache Kafka (Accessible cluster).
*   Python 3.11+.
*   Docker.

## Quick Install

1.  **Clone the repository** and configure the environment:
    ```bash
    cp .env.example .env  # Configure your laboratory IPs here
    pip install -r requirements.txt
    ```

2.  **Build the Worker**:
    ```bash
    docker build -t opentrack-worker:latest ./worker
    ```

3.  **Launch the API**:
    ```bash
    $env:PYTHONPATH = "."
    uvicorn src.main:app --port 8002 --reload
    ```

## Related Documentation

*   [RUNBOOK.txt](./RUNBOOK.txt): Step-by-step guide for technical deployment and RBAC.
*   [PROJECT_EXPLANATION.txt](./PROJECT_EXPLANATION.txt): Deep dive into architecture and file-by-file function breakdown.
