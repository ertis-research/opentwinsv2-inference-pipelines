import httpx

class BentloyService:
    url: str
    
    def __init__(self, url: str):
        self.url = url
    
    async def get_model(self, model_name: str):
        """Fetch the model from bentloy service"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.url}/list_models", json={"page":0, "page_size": 10, "query": model_name})
                response.raise_for_status()
                models = (response.json()).get("discovered_models", [])
                if len(models) == 0:
                    return None
                return models[0]
            except Exception as e:
                print(f"Error fetching the model: {e}")
                return None

    async def infere_with_model(self, model_name: str, input: dict):
        """Use the deployed model to infere and predict"""
        model = await self.get_model(model_name)
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