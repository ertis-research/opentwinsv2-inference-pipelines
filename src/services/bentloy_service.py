import httpx


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
                # Bentloy pages start at 1. Since we filter with `query` and only
                # use the first result, the first page is enough (no need to
                # iterate over the remaining pages).
                response = await client.post(f"{self.url}/list_models", json={"page": 1, "page_size": 10, "query": model_name})
                if response.status_code == 400:
                    try:
                        detail = response.json().get("detail", response.text)
                    except Exception:
                        detail = response.text
                    raise BentloyError(f"Bentloy rejected the request: {detail}")
                response.raise_for_status()
                models = (response.json()).get("discovered_models", [])
                if len(models) == 0:
                    return None
                return models[0]
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
            "model_name": service_name,
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