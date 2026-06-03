import httpx
from src.config import settings

class WotService:
    async def get_things(self):
        """Fetch all things from the WoT directory service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{settings.THINGS_SERVICE_URL}/things")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error fetching things: {e}")
                return []

    def validate_things(self, things: list[str]):
        # Implementation to check if things exist in WoT directory
        return True

wot_service = WotService()
