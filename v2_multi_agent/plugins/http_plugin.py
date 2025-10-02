from semantic_kernel.functions import kernel_function
import aiohttp
from typing import Optional


class HttpClientPlugin:
    """Plugin for making HTTP requests."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    @kernel_function(
        description="Fetch content from a given URL. Returns the response text.",
        name="fetch_url",
    )
    async def fetch_url(self, url: str) -> str:
        """Fetch content from the specified URL and return the response text."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()