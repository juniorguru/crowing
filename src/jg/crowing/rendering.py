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
BLUE = "#0f62fe"

CTA_TEXT = "junior.guru/handbook"

# Inter is bundled under the SIL Open Font License 1.1 (see assets/Inter-LICENSE).
_ASSETS = files("jg.crowing") / "assets"
_FONT_PATHS = {
    False: str(_ASSETS / "Inter.ttf"),
    True: str(_ASSETS / "Inter-Italic.ttf"),
}
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


def _line_height(size: int) -> float:
    ascent, descent = load_font(size).getmetrics()
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
    """Pick the largest heading size (title scaled down) at which the intro fits."""
    title_font = load_font(min_size, 400)
    heading_font = load_font(min_size, 700)
    title_lines = wrap_text(draw, title, title_font, CONTENT)
    heading_lines = wrap_text(draw, heading, heading_font, CONTENT)
    for size in range(max_size, min_size, -2):
        title_font = load_font(int(size * INTRO_TITLE_RATIO), 400)
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
    title_block = _line_height(title_font.size) * len(title_lines)
    heading_block = _line_height(heading_font.size) * len(heading_lines)
    gap = _line_height(heading_font.size) * INTRO_GAP_RATIO
    return title_block + gap + heading_block


def _draw_centered(
    draw: Draw, lines: list[str], font: Font, fill: str, top: float
) -> float:
    step = _line_height(font.size)
    for index, line in enumerate(lines):
        x = (SIZE - draw.textlength(line, font=font)) / 2
        draw.text((x, top + index * step), line, font=font, fill=fill)
    return top + step * len(lines)


def render_intro(title: str, heading: str) -> Image.Image:
    """The opening slide: small title, a line break, then the larger heading."""
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    title_lines, heading_lines, title_font, heading_font = fit_intro(
        draw, f"{title}:", heading
    )
    height = _intro_height(title_lines, title_font, heading_lines, heading_font)
    top = (SIZE - height) / 2
    top = _draw_centered(draw, title_lines, title_font, DARK, top)
    top += _line_height(heading_font.size) * INTRO_GAP_RATIO
    _draw_centered(draw, heading_lines, heading_font, DARK, top)
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
    return _line_height(size) * len(lines) <= max_height


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
    step = _line_height(size)
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
    """The closing call-to-action slide with a flat blue button."""
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    font = load_font(56, weight=600)
    half_w = draw.textlength(CTA_TEXT, font=font) / 2 + 64
    half_h = _line_height(56) / LINE_SPACING / 2 + 40
    centre = SIZE / 2
    box = (centre - half_w, centre - half_h, centre + half_w, centre + half_h)
    draw.rounded_rectangle(box, radius=int(half_h), fill=BLUE)
    draw.text((centre, centre), CTA_TEXT, font=font, fill=WHITE, anchor="mm")
    return image


def render_section(section: Section) -> list[Image.Image]:
    """Render the full carousel: intro, one slide per paragraph, then the CTA."""
    return [
        render_intro(section.title, section.heading),
        *(render_paragraph(paragraph) for paragraph in section.paragraphs),
        render_cta(),
    ]
