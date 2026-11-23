import httpx


PAGE_SIZE = 100
MAX_PAGES = 50  # safety cap to avoid endless paging


class BentloyError(Exception):
    """Raised when the Bentloy service rejects a request (e.g. HTTP 400)."""


class BentloyService:
    url: str
    
    def __init__(self, url: str):
        self.url = url
    
    async def get_model(self, model_name: str):
        """Fetch the model from bentloy service"""
        async with httpx.AsyncClient() as client:
            try:
                # `query` is a case-insensitive substring match on
                # `inferred_model_name`, so several models can match (e.g.
                # "churn_v2" also matches "churn_v2_eu"). We page through the
                # results and require an exact match on the name.
                page = 1
                while page <= MAX_PAGES:
                    response = await client.post(
                        f"{self.url}/list_models",
                        json={"page": page, "page_size": PAGE_SIZE, "query": model_name},
                    )
                    if response.status_code == 400:
                        try:
                            detail = response.json().get("detail", response.text)
                        except Exception:
                            detail = response.text
                        raise BentloyError(f"Bentloy rejected the request: {detail}")
                    response.raise_for_status()
                    body = response.json()
                    discovery = body.get("discovery") or {}
                    if discovery.get("status") == "error":
                        raise BentloyError(f"Bentloy model discovery failed: {discovery.get('error')}")
                    for model in body.get("discovered_models", []):
                        if model.get("inferred_model_name") == model_name:
                            return model
                    pagination = (body.get("pagination") or {}).get("discovered_models") or {}
                    if not pagination.get("has_next"):
                        break
                    page += 1
                return None
            except BentloyError:
                raise
            except Exception as e:
                print(f"Error fetching the model: {e}")
                return None

    async def infere_with_model(self, model_name: str, input: dict):
        """Use the deployed model to infere and predict"""
        try:
            model = await self.get_model(model_name)
        except BentloyError as e:
            print(f"Error fetching the model: {e}")
            model = None
        if model is None:
            raise KeyError("Model was not found")
        service_name = model.get("service_name", model_name)
        predict_url = model.get("predict_endpoint", f"http://{service_name}:3000/predict")

        payload = {
            "model_name": model.get("inferred_model_name", model_name),
            "model_url": predict_url,
            "data": input
        }

        async with httpx.AsyncClient() as client:
            try:
                # Changed from settings.BENTLOY_SERVICE_URL to self.url
                response = await client.post(f"{self.url}/predict", json=payload)
                response.raise_for_status()
                response_json = response.json()
                return response_json.get("predictions", response_json)
            except Exception as e:
                print(f"Error fetching the model: {e}")
                return {}