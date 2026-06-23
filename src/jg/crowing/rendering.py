"""Pure functions turning a :class:`Section` into Instagram-ready square images."""

import re
from functools import lru_cache
from importlib.resources import files

from PIL import Image, ImageDraw, ImageFont

from jg.crowing.models import RichText, Run, Section


SIZE = 1080
PADDING = 96
CONTENT = SIZE - 2 * PADDING
LINE_SPACING = 1.25
INTRO_TITLE_RATIO = 0.5
INTRO_GAP_RATIO = 0.4

YELLOW = "#fffa72"
DARK = "#343434"
WHITE = "#ffffff"
BLUE = "#1755d1"  # Bootstrap primary blue, as on junior.guru thumbnails

CTA_TEXT = "junior.guru/handbook"
CTA_ICON = "\uf447"  # Bootstrap Icons "journals" (U+F447)
CTA_TEXT_SIZE = 46
CTA_ICON_SIZE = 50
CTA_ICON_GAP = 18
CTA_PADDING_X = 42
CTA_PADDING_Y = 26
BUTTON_RADIUS_RATIO = 0.1  # only slightly rounded corners, not a pill

# Inter and Liberation Mono are bundled under the SIL Open Font License 1.1
# (see assets/Inter-LICENSE and assets/LiberationMono-LICENSE).
# Bootstrap Icons is bundled under the MIT License (see assets/bootstrap-icons-LICENSE).
_ASSETS = files("jg.crowing") / "assets"
_FONT_PATHS = {
    False: str(_ASSETS / "Inter.ttf"),
    True: str(_ASSETS / "Inter-Italic.ttf"),
}
_ICON_PATH = str(_ASSETS / "bootstrap-icons.ttf")
_MONO_PATH = str(_ASSETS / "LiberationMono.ttf")
_OPTICAL_SIZE_MAX = 32

Segment = tuple[str, bool, bool]
Word = list[Segment]
Font = ImageFont.FreeTypeFont
Draw = ImageDraw.ImageDraw


@lru_cache(maxsize=None)
def load_font(size: int, weight: int = 400, italic: bool = False) -> Font:
    """Load Inter at ``size`` pixels with the given weight and slant."""
    font = ImageFont.truetype(_FONT_PATHS[italic], size)
    font.set_variation_by_axes([min(size, _OPTICAL_SIZE_MAX), weight])
    return font


def _segment_font(size: int, bold: bool, italic: bool) -> Font:
    return load_font(size, 700 if bold else 400, italic)


@lru_cache(maxsize=None)
def load_icon_font(size: int) -> Font:
    """Load the bundled Bootstrap Icons font at ``size`` pixels."""
    return ImageFont.truetype(_ICON_PATH, size)


@lru_cache(maxsize=None)
def load_mono_font(size: int) -> Font:
    """Load the bundled Liberation Mono font at ``size`` pixels (for monospace text)."""
    return ImageFont.truetype(_MONO_PATH, size)


def _line_height(font: Font) -> float:
    ascent, descent = font.getmetrics()
    return (ascent + descent) * LINE_SPACING


# --- plain text (intro) -----------------------------------------------------


def wrap_text(draw: Draw, text: str, font: Font, max_width: int) -> list[str]:
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


def _block_fits(draw: Draw, lines: list[str], font: Font, max_width: int) -> bool:
    return all(draw.textlength(line, font=font) <= max_width for line in lines)


def fit_intro(
    draw: Draw, title: str, heading: str, max_size: int = 130, min_size: int = 20
) -> tuple[list[str], list[str], Font, Font]:
    """Pick the largest heading size (monospace title scaled down) at which the intro fits."""
    title_font = load_mono_font(min_size)
    heading_font = load_font(min_size, 700)
    title_lines = wrap_text(draw, title, title_font, CONTENT)
    heading_lines = wrap_text(draw, heading, heading_font, CONTENT)
    for size in range(max_size, min_size, -2):
        title_font = load_mono_font(int(size * INTRO_TITLE_RATIO))
        heading_font = load_font(size, 700)
        title_lines = wrap_text(draw, title, title_font, CONTENT)
        heading_lines = wrap_text(draw, heading, heading_font, CONTENT)
        height = _intro_height(title_lines, title_font, heading_lines, heading_font)
        widths_ok = _block_fits(draw, title_lines, title_font, CONTENT) and _block_fits(
            draw, heading_lines, heading_font, CONTENT
        )
        if widths_ok and height <= CONTENT:
            break
    return title_lines, heading_lines, title_font, heading_font


def _intro_height(
    title_lines, title_font: Font, heading_lines, heading_font: Font
) -> float:
    title_block = _line_height(title_font) * len(title_lines)
    heading_block = _line_height(heading_font) * len(heading_lines)
    gap = _line_height(heading_font) * INTRO_GAP_RATIO
    return title_block + gap + heading_block


def _draw_left(
    draw: Draw, lines: list[str], font: Font, fill: str, top: float
) -> float:
    step = _line_height(font)
    for index, line in enumerate(lines):
        draw.text((PADDING, top + index * step), line, font=font, fill=fill)
    return top + step * len(lines)


def render_intro(title: str, heading: str) -> Image.Image:
    """The opening slide: a small monospace title, a line break, then the larger heading."""
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    title_lines, heading_lines, title_font, heading_font = fit_intro(
        draw, title, heading
    )
    height = _intro_height(title_lines, title_font, heading_lines, heading_font)
    top = (SIZE - height) / 2
    top = _draw_left(draw, title_lines, title_font, DARK, top)
    top += _line_height(heading_font) * INTRO_GAP_RATIO
    _draw_left(draw, heading_lines, heading_font, DARK, top)
    return image


# --- rich text (paragraphs) -------------------------------------------------


def to_words(runs: RichText) -> list[Word]:
    """Split styled runs into words, each a list of same-style segments."""
    words: list[Word] = []
    current: Word = []
    for run in runs:
        current = _split_run(run, words, current)
    if current:
        words.append(current)
    return words


def _split_run(run: Run, words: list[Word], current: Word) -> Word:
    for part in re.split(r"(\s+)", run.text):
        if not part:
            continue
        if part.isspace():
            if current:
                words.append(current)
                current = []
        else:
            current.append((part, run.bold, run.italic))
    return current


def _word_width(draw: Draw, word: Word, size: int) -> float:
    return sum(
        draw.textlength(text, font=_segment_font(size, b, i)) for text, b, i in word
    )


def _wrap_words(
    draw: Draw, words: list[Word], size: int, max_width: int
) -> list[list[Word]]:
    space = draw.textlength(" ", font=load_font(size))
    lines: list[list[Word]] = []
    line: list[Word] = []
    width = 0.0
    for word in words:
        extra = _word_width(draw, word, size) + (space if line else 0)
        if line and width + extra > max_width:
            lines.append(line)
            line, width = [word], _word_width(draw, word, size)
        else:
            line.append(word)
            width += extra
    if line:
        lines.append(line)
    return lines


def _words_fit(draw: Draw, lines, size: int, max_width: int, max_height: int) -> bool:
    space = draw.textlength(" ", font=load_font(size))
    for line in lines:
        width = sum(_word_width(draw, word, size) for word in line) + space * (
            len(line) - 1
        )
        if width > max_width:
            return False
    return _line_height(load_font(size)) * len(lines) <= max_height


def fit_words(
    draw: Draw,
    words: list[Word],
    max_width: int,
    max_height: int,
    max_size=120,
    min_size=12,
) -> tuple[int, list[list[Word]]]:
    """Pick the largest font size at which the wrapped words fit the box."""
    size = min_size
    lines = _wrap_words(draw, words, size, max_width)
    for size in range(max_size, min_size, -2):
        lines = _wrap_words(draw, words, size, max_width)
        if _words_fit(draw, lines, size, max_width, max_height):
            break
    return size, lines


def _draw_words(draw: Draw, lines: list[list[Word]], size: int, fill: str) -> None:
    space = draw.textlength(" ", font=load_font(size))
    step = _line_height(load_font(size))
    top = (SIZE - step * len(lines)) / 2
    for index, line in enumerate(lines):
        x = float(PADDING)
        for word in line:
            for text, bold, italic in word:
                font = _segment_font(size, bold, italic)
                draw.text((x, top + index * step), text, font=font, fill=fill)
                x += draw.textlength(text, font=font)
            x += space


def render_paragraph(runs: RichText) -> Image.Image:
    """A content slide: white background, left-aligned dark paragraph with markup."""
    image = Image.new("RGB", (SIZE, SIZE), WHITE)
    draw = ImageDraw.Draw(image)
    size, lines = fit_words(draw, to_words(runs), CONTENT, CONTENT)
    _draw_words(draw, lines, size, DARK)
    return image


# --- call to action ---------------------------------------------------------


def render_cta() -> Image.Image:
    """The closing call-to-action: a flat blue button with the journals icon."""
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    text_font = load_font(CTA_TEXT_SIZE, weight=600)
    icon_font = load_icon_font(CTA_ICON_SIZE)
    icon_width = draw.textlength(CTA_ICON, font=icon_font)
    text_width = draw.textlength(CTA_TEXT, font=text_font)
    content_width = icon_width + CTA_ICON_GAP + text_width
    ascent, descent = text_font.getmetrics()
    button_width = content_width + 2 * CTA_PADDING_X
    button_height = ascent + descent + 2 * CTA_PADDING_Y
    centre = SIZE / 2
    left = centre - button_width / 2
    box = (
        left,
        centre - button_height / 2,
        left + button_width,
        centre + button_height / 2,
    )
    draw.rounded_rectangle(
        box, radius=round(button_height * BUTTON_RADIUS_RATIO), fill=BLUE
    )
    content_left = centre - content_width / 2
    draw.text((content_left, centre), CTA_ICON, font=icon_font, fill=WHITE, anchor="lm")
    text_left = content_left + icon_width + CTA_ICON_GAP
    draw.text((text_left, centre), CTA_TEXT, font=text_font, fill=WHITE, anchor="lm")
    return image


def render_section(section: Section) -> list[Image.Image]:
    """Render the full carousel: intro, one slide per paragraph, then the CTA."""
    return [
        render_intro(section.title, section.heading),
        *(render_paragraph(paragraph) for paragraph in section.paragraphs),
        render_cta(),
    ]
