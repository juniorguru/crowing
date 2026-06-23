"""Pure functions turning a :class:`Section` into Instagram-ready square images."""

import re
from functools import lru_cache
from importlib.resources import files
from typing import NamedTuple

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

CTA_MESSAGE = "V\u00edce o tomto t\u00e9matu najde\u0161 v p\u0159\u00edru\u010dce"
CTA_MESSAGE_SIZE = 64
CTA_MESSAGE_WEIGHT = 600
CTA_TEXT = "junior.guru/handbook"
CTA_ICON = "\uf447"  # Bootstrap Icons "journals" (U+F447)
CTA_TEXT_SIZE = 46
CTA_ICON_SIZE = 50
CTA_ICON_GAP = 18
CTA_PADDING_X = 42
CTA_PADDING_Y = 26
CTA_GAP = 56  # space between the message and the button
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
# chick.png is rasterized from chick-icon.svg (junior.guru mascot); see `make assets`.
_CHICK_PATH = str(_ASSETS / "chick.png")
_OPTICAL_SIZE_MAX = 32
CHICK_WIDTH = round(SIZE * 0.32)
ARROW_GLYPH = "\uf133"  # Bootstrap Icons "arrow-right-circle-fill" (U+F133)
ARROW_SIZE = round(SIZE * 0.13)
ARROW_INSET_RATIO = 0.08  # shrink the white disc so the blue ring hides its edge

Segment = tuple[str, bool, bool]
Word = list[Segment]
Box = tuple[float, float, float, float]
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


@lru_cache(maxsize=None)
def load_chick(width: int) -> Image.Image:
    """Load the bundled chick illustration scaled to ``width`` pixels (keeps alpha)."""
    chick = Image.open(_CHICK_PATH).convert("RGBA")
    height = round(width * chick.height / chick.width)
    return chick.resize((width, height))


@lru_cache(maxsize=None)
def load_arrow(size: int) -> Image.Image:
    """Render the arrow-right-circle-fill icon as a blue disc with a white arrow."""
    font = load_icon_font(size)
    left, top, right, bottom = font.getbbox(ARROW_GLYPH)
    width, height = right - left, bottom - top
    tile = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    inset = round(width * ARROW_INSET_RATIO)
    draw.ellipse((inset, inset, width - inset, height - inset), fill=WHITE)
    draw.text((-left, -top), ARROW_GLYPH, font=font, fill=BLUE)
    return tile


def _line_height(font: Font) -> float:
    ascent, descent = font.getmetrics()
    return (ascent + descent) * LINE_SPACING


# --- plain text (intro) -----------------------------------------------------


def wrap_text(draw: Draw, text: str, font: Font, max_width: int) -> list[str]:
    """Greedily wrap ``text`` so that each line fits within ``max_width``.

    A single-letter word never ends a line; it stays glued to the next word.
    """
    lines: list[str] = []
    current = ""
    for unit in _glue_text(text.split()):
        candidate = f"{current} {unit}".strip()
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = unit
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _glue_text(words: list[str]) -> list[str]:
    """Merge each single-letter word with the following word into one wrap unit."""
    units: list[str] = []
    prefix = ""
    for word in words:
        if len(word) == 1:
            prefix = f"{prefix}{word} "
        else:
            units.append(f"{prefix}{word}")
            prefix = ""
    if prefix:
        units.append(prefix.rstrip())
    return units


def _block_fits(draw: Draw, lines: list[str], font: Font, max_width: int) -> bool:
    return all(draw.textlength(line, font=font) <= max_width for line in lines)


def fit_intro(
    draw: Draw,
    title: str,
    heading: str,
    max_size: int = 130,
    min_size: int = 20,
    max_height: int = CONTENT,
) -> tuple[list[str], list[str], Font, Font]:
    """Pick the largest heading size (monospace title scaled down) that fits the box."""
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
        if widths_ok and height <= max_height:
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


class IntroLayout(NamedTuple):
    title_lines: list[str]
    heading_lines: list[str]
    title_font: Font
    heading_font: Font
    top: float
    chick: Image.Image
    chick_box: Box
    arrow: Image.Image
    arrow_box: Box
    text_box: Box


def intro_layout(draw: Draw, title: str, heading: str) -> IntroLayout:
    """Lay out the intro text above a bottom-left chick and bottom-right arrow."""
    chick = load_chick(CHICK_WIDTH)
    arrow = load_arrow(ARROW_SIZE)
    bottom = SIZE - PADDING
    chick_box = (PADDING, bottom - chick.height, PADDING + chick.width, bottom)
    arrow_box = (
        SIZE - PADDING - arrow.width,
        bottom - arrow.height,
        SIZE - PADDING,
        bottom,
    )
    text_height_budget = min(chick_box[1], arrow_box[1]) - PADDING
    lines = fit_intro(draw, title, heading, max_height=text_height_budget)
    title_lines, heading_lines, title_font, heading_font = lines
    text_height = _intro_height(title_lines, title_font, heading_lines, heading_font)
    text_width = _intro_width(
        draw, title_lines, title_font, heading_lines, heading_font
    )
    top = PADDING + (text_height_budget - text_height) / 2
    text_box = (PADDING, top, PADDING + text_width, top + text_height)
    return IntroLayout(
        title_lines,
        heading_lines,
        title_font,
        heading_font,
        top,
        chick,
        chick_box,
        arrow,
        arrow_box,
        text_box,
    )


def _intro_width(
    draw: Draw, title_lines, title_font: Font, heading_lines, heading_font: Font
) -> float:
    title = (draw.textlength(line, font=title_font) for line in title_lines)
    heading = (draw.textlength(line, font=heading_font) for line in heading_lines)
    return max(*title, *heading)


def render_intro(title: str, heading: str) -> Image.Image:
    """Intro slide: monospace title, heading, chick bottom-left, arrow bottom-right."""
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    layout = intro_layout(draw, title, heading)
    top = _draw_left(draw, layout.title_lines, layout.title_font, DARK, layout.top)
    top += _line_height(layout.heading_font) * INTRO_GAP_RATIO
    _draw_left(draw, layout.heading_lines, layout.heading_font, DARK, top)
    image.paste(
        layout.chick, (int(layout.chick_box[0]), int(layout.chick_box[1])), layout.chick
    )
    image.paste(
        layout.arrow, (int(layout.arrow_box[0]), int(layout.arrow_box[1])), layout.arrow
    )
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


def glue_words(words: list[Word]) -> list[Word]:
    """Merge each single-letter word with the following word into one wrap unit."""
    units: list[Word] = []
    prefix: Word = []
    for word in words:
        if _word_length(word) == 1:
            prefix = _with_trailing_space(prefix + word)
        else:
            units.append(prefix + word)
            prefix = []
    if prefix:
        units.append(prefix)
    return units


def _word_length(word: Word) -> int:
    return sum(len(text) for text, _, _ in word)


def _with_trailing_space(word: Word) -> Word:
    text, bold, italic = word[-1]
    return word[:-1] + [(f"{text} ", bold, italic)]


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
    size, lines = fit_words(draw, glue_words(to_words(runs)), CONTENT, CONTENT)
    _draw_words(draw, lines, size, DARK)
    return image


# --- call to action ---------------------------------------------------------


def fit_plain(
    draw: Draw,
    text: str,
    max_width: int,
    max_height: float,
    max_size: int,
    weight: int = 400,
    min_size: int = 12,
) -> tuple[Font, list[str]]:
    """Pick the largest plain-text size at which the wrapped lines fit the box."""
    font = load_font(min_size, weight)
    lines = wrap_text(draw, text, font, max_width)
    for size in range(max_size, min_size, -2):
        font = load_font(size, weight)
        lines = wrap_text(draw, text, font, max_width)
        if _block_fits(draw, lines, font, max_width):
            if _line_height(font) * len(lines) <= max_height:
                break
    return font, lines


def _button_size(draw: Draw, text_font: Font, icon_font: Font) -> tuple[float, float]:
    icon_width = draw.textlength(CTA_ICON, font=icon_font)
    text_width = draw.textlength(CTA_TEXT, font=text_font)
    ascent, descent = text_font.getmetrics()
    width = icon_width + CTA_ICON_GAP + text_width + 2 * CTA_PADDING_X
    height = ascent + descent + 2 * CTA_PADDING_Y
    return width, height


def _draw_button(
    draw: Draw, left: float, top: float, text_font: Font, icon_font: Font
) -> None:
    width, height = _button_size(draw, text_font, icon_font)
    box = (left, top, left + width, top + height)
    draw.rounded_rectangle(box, radius=round(height * BUTTON_RADIUS_RATIO), fill=BLUE)
    icon_width = draw.textlength(CTA_ICON, font=icon_font)
    content_left = left + CTA_PADDING_X
    middle = top + height / 2
    draw.text((content_left, middle), CTA_ICON, font=icon_font, fill=WHITE, anchor="lm")
    text_left = content_left + icon_width + CTA_ICON_GAP
    draw.text((text_left, middle), CTA_TEXT, font=text_font, fill=WHITE, anchor="lm")


def render_cta() -> Image.Image:
    """The closing call-to-action: a message above a flat blue journals button."""
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    text_font = load_font(CTA_TEXT_SIZE, weight=600)
    icon_font = load_icon_font(CTA_ICON_SIZE)
    _, button_height = _button_size(draw, text_font, icon_font)
    budget = CONTENT - button_height - CTA_GAP
    message_font, message_lines = fit_plain(
        draw, CTA_MESSAGE, CONTENT, budget, CTA_MESSAGE_SIZE, weight=CTA_MESSAGE_WEIGHT
    )
    message_height = _line_height(message_font) * len(message_lines)
    top = (SIZE - (message_height + CTA_GAP + button_height)) / 2
    top = _draw_left(draw, message_lines, message_font, DARK, top)
    _draw_button(draw, PADDING, top + CTA_GAP, text_font, icon_font)
    return image


def render_section(section: Section) -> list[Image.Image]:
    """Render the full carousel: intro, one slide per paragraph, then the CTA."""
    return [
        render_intro(section.title, section.heading),
        *(render_paragraph(paragraph) for paragraph in section.paragraphs),
        render_cta(),
    ]
