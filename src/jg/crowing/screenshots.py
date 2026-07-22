"""Imperative shell: screenshot event page elements with a headless browser.

Uses Playwright driving a free and open source browser (Firefox by default) to open
the live event page, flatten its links and hide the media card's call to action, then
grab one screenshot per element. Playwright is imported lazily so the rest of the tool
(and its tests) runs without the browser binaries installed.
"""

from io import BytesIO

from PIL import Image

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import Shot
from jg.crowing.rendering import reading_seconds


MEDIA_CARD_SELECTOR = ".media-card-featured"
LEAD_PARAGRAPH_SELECTOR = ".lead p"  # one screenshot per paragraph inside .lead
NOTE_EXPLAINER_ITEM_SELECTOR = ".note-explainer-item"

MEDIA_CARD_VIEWPORT_WIDTH = 400
LEAD_VIEWPORT_WIDTH = 400
NOTE_EXPLAINER_VIEWPORT_WIDTH = 300
VIEWPORT_HEIGHT = 2000  # tall enough that any single element renders in full

WHITE = "#ffffff"
LEAD_BACKGROUND = "#f4f8fe"  # light blue, the same as the media card's own background

# Render at 3x the CSS resolution (as a Retina display would) so the narrow viewports
# still yield more pixels than the square's content box; the screenshots are then
# downsampled onto the square, which keeps the text crisp instead of upscaling it.
DEVICE_SCALE_FACTOR = 3

# Injected before screenshotting: drop every link's underline, paint the links in
# their parent's text colour (``inherit``) except the blue ``.icon-links``, which keep
# their colour, and hide the media card's call-to-action button and its badge.
PREPARATION_CSS = (
    "a, a * { text-decoration: none !important; }\n"  # .icon-link underlines its span
    "a:not(.icon-link) { color: inherit !important; }\n"
    ".media-card-button, .media-card-badge { display: none !important; }\n"
)

# The screenshots, in the order the carousel expects them, each as
# ``(viewport width, selector, background)``: the featured media card, one per lead
# paragraph (on yellow), then one per note explainer item.
_SHOOTS = [
    (MEDIA_CARD_VIEWPORT_WIDTH, MEDIA_CARD_SELECTOR, WHITE),
    (LEAD_VIEWPORT_WIDTH, LEAD_PARAGRAPH_SELECTOR, LEAD_BACKGROUND),
    (NOTE_EXPLAINER_VIEWPORT_WIDTH, NOTE_EXPLAINER_ITEM_SELECTOR, WHITE),
]


async def capture_event(url: str, *, browser_name: str = "firefox") -> list[Shot]:
    """Screenshot the event page's media card, lead and note explainer items.

    Raises :class:`InvalidInputError` when the page has none of these elements.
    """
    from playwright.async_api import async_playwright

    shots: list[Shot] = []
    async with async_playwright() as playwright:
        browser = await getattr(playwright, browser_name).launch()
        try:
            for width, selector, background in _SHOOTS:
                shots += await _shoot_all(browser, url, width, selector, background)
        finally:
            await browser.close()
    if not shots:
        raise InvalidInputError(
            "Event page has none of the expected elements "
            f"(media card, lead, note explainer): {url}"
        )
    return shots


async def _shoot_all(
    browser, url: str, width: int, selector: str, background: str
) -> list[Shot]:
    """Load ``url`` at viewport ``width`` and screenshot every ``selector`` element."""
    page = await browser.new_page(
        viewport={"width": width, "height": VIEWPORT_HEIGHT},
        device_scale_factor=DEVICE_SCALE_FACTOR,
    )
    try:
        await page.goto(url, wait_until="networkidle")
        await page.add_style_tag(content=PREPARATION_CSS + _background_css(background))
        shots = []
        for element in await page.locator(selector).all():
            await element.scroll_into_view_if_needed()
            image = Image.open(BytesIO(await element.screenshot())).convert("RGB")
            shots.append(
                Shot(
                    image=image,
                    reading_seconds=reading_seconds(await element.inner_text()),
                    background=background,
                )
            )
        return shots
    finally:
        await page.close()


def _background_css(background: str) -> str:
    """Paint the page ``background`` and clear the lead's own so it shows through."""
    if background == WHITE:
        return ""
    return (
        f"html, body {{ background: {background} !important; }}\n"
        ".lead, .lead * { background-color: transparent !important; }\n"
    )
