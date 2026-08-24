"""Imperative shell: download handbook HTML over HTTP."""

import httpx2


async def fetch_html(
    url: str, *, transport: httpx2.AsyncBaseTransport | None = None
) -> str:
    """Download ``url`` and return its HTML body, raising on HTTP errors."""
    async with httpx2.AsyncClient(
        follow_redirects=True,
        transport=transport,
        timeout=30,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
