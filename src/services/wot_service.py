import httpx

class WotService:
    def __init__(self, url: str):
            self.url = url
    async def get_thing(self, thing_id: str):
        """Fetch a thing from the WoT directory service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.url}/things/{thing_id}")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error fetching things: {e}")
                return None

    async def get_thing_state(self, thing_id: str):
        print(f"Fetching state for thing: {thing_id}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.url}/things/{thing_id}/state")
                response.raise_for_status()
                state_wrapper = response.json()
                print(f"Successfully fetched state for {thing_id}: {state_wrapper}")
                return state_wrapper.get("data", state_wrapper)
            except Exception as e:
                print(f"Error fetching thing state from {e}")
                return None
