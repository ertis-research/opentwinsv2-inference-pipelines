FROM python:3.11-slim

WORKDIR /app

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ .

COPY src/__init__.py ./src/
COPY src/services/__init__.py ./src/services/

COPY src/services/bentloy_service.py ./src/services/
COPY src/services/wot_service.py ./src/services/

CMD ["python", "main.py"]
