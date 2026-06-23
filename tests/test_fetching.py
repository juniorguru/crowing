import httpx
import pytest

from jg.crowing.fetching import fetch_html


async def test_fetch_html_returns_body():
    def handler(request):
        assert request.url.host == "junior.guru"
        return httpx.Response(200, text="<h1>Hello</h1>")

    transport = httpx.MockTransport(handler)
    html = await fetch_html("https://junior.guru/handbook/git/", transport=transport)
    assert html == "<h1>Hello</h1>"


async def test_fetch_html_raises_for_status():
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        await fetch_html("https://junior.guru/handbook/nope/", transport=transport)
