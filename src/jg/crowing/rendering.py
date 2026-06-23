"""Pure functions turning a :class:`Section` into Instagram-ready square images."""

from functools import lru_cache
from importlib.resources import files

from PIL import Image, ImageDraw, ImageFont

from jg.crowing.models import Section


SIZE = 1080
PADDING = 96
CONTENT = SIZE - 2 * PADDING
LINE_SPACING = 1.25

YELLOW = "#fffa72"
DARK = "#343434"
WHITE = "#ffffff"
BLUE = "#0f62fe"

CTA_TEXT = "junior.guru/handbook"

# Inter is bundled under the SIL Open Font License 1.1 (see assets/Inter-LICENSE.txt).
_FONT_PATH = str(files("jg.crowing") / "assets" / "Inter.ttf")
_OPTICAL_SIZE_MAX = 32


@lru_cache(maxsize=None)
def load_font(size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    """Load Inter at ``size`` pixels and the given variable-font ``weight``."""
    font = ImageFont.truetype(_FONT_PATH, size)
    font.set_variation_by_axes([min(size, _OPTICAL_SIZE_MAX), weight])
    return font


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Greedily wrap ``text`` so that each line fits within ``max_width``."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _line_height(font: ImageFont.FreeTypeFont) -> int:
    ascent, descent = font.getmetrics()
    return ascent + descent


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_height: int,
    weight: int = 400,
    max_size: int = 130,
    min_size: int = 12,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Find the largest font size at which ``text`` fits ``max_width`` × ``max_height``."""
    font = load_font(min_size, weight)
    lines = wrap_text(draw, text, font, max_width)
    for size in range(max_size, min_size, -2):
        font = load_font(size, weight)
        lines = wrap_text(draw, text, font, max_width)
        widest = max(draw.textlength(line, font=font) for line in lines)
        block = _line_height(font) * LINE_SPACING * len(lines)
        if widest <= max_width and block <= max_height:
            break
    return font, lines


def _draw_block(image: Image.Image, lines, font, fg, align) -> None:
    draw = ImageDraw.Draw(image)
    step = _line_height(font) * LINE_SPACING
    top = (SIZE - step * len(lines)) / 2
    for index, line in enumerate(lines):
        y = top + index * step
        if align == "center":
            x = (SIZE - draw.textlength(line, font=font)) / 2
        else:
            x = PADDING
        draw.text((x, y), line, font=font, fill=fg)


def _render_text(text: str, bg, fg, align: str, weight: int) -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(image)
    font, lines = fit_text(draw, text, CONTENT, CONTENT, weight)
    _draw_block(image, lines, font, fg, align)
    return image


def render_intro(text: str) -> Image.Image:
    """The opening slide: yellow background, centered dark title."""
    return _render_text(text, YELLOW, DARK, align="center", weight=700)


def render_paragraph(text: str) -> Image.Image:
    """A content slide: white background, left-aligned dark paragraph."""
    return _render_text(text, WHITE, DARK, align="left", weight=400)


def render_cta() -> Image.Image:
    """The closing call-to-action slide with a flat blue button."""
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    font = load_font(56, weight=600)
    text_width = draw.textlength(CTA_TEXT, font=font)
    text_height = _line_height(font)
    pad_x, pad_y = 64, 40
    half_w = text_width / 2 + pad_x
    half_h = text_height / 2 + pad_y
    centre = SIZE / 2
    box = (centre - half_w, centre - half_h, centre + half_w, centre + half_h)
    draw.rounded_rectangle(box, radius=int(half_h), fill=BLUE)
    draw.text((centre, centre), CTA_TEXT, font=font, fill=WHITE, anchor="mm")
    return image


def render_section(section: Section) -> list[Image.Image]:
    """Render the full carousel: intro, one slide per paragraph, then the CTA."""
    return [
        render_intro(section.intro),
        *(render_paragraph(paragraph) for paragraph in section.paragraphs),
        render_cta(),
    ]
