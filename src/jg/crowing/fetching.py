"""Imperative shell: download handbook HTML over HTTP."""

import httpx


async def fetch_html(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    """Download ``url`` and return its HTML body, raising on HTTP errors."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        transport=transport,
        timeout=30,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
