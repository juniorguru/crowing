"""Pure functions turning a :class:`Section` into Instagram-ready square images."""

import re
from collections.abc import Callable
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

CTA_MESSAGE = "Zaj\u00edm\u00e1 t\u011b tohle t\u00e9ma?\nOtev\u0159i si p\u0159\u00edru\u010dku a \u010dti d\u00e1l!"
CTA_MESSAGE_SIZE = 48  # smaller than the logo and topics
CTA_MESSAGE_WEIGHT = 600
CTA_TEXT = "junior.guru/handbook"
CTA_ICON = "\uf447"  # Bootstrap Icons "journals" (U+F447)
CTA_TEXT_SIZE = 56
CTA_ICON_SIZE = 60
CTA_ICON_GAP = 22
CTA_PADDING_X = 56
CTA_PADDING_Y = 34
CTA_LOGO_WIDTH = round(SIZE * 0.5)  # junior.guru wordmark above the message
CTA_GAP = 72  # vertical gap between logo, message, button and cloud
CTA_TOPICS_SIZE = 72
CTA_TOPICS_COLOR = "#998c00"  # dark gold watermark, readable on the light yellow
CTA_TOPICS_WEIGHT = 400  # regular weight for the prefix and topics, not bold
CTA_TOPICS_PREFIX = "Co tam najdeš?"  # dark lead-in before the topics
CTA_TOPICS_SEP = "·"  # middot between topics on the same line
CTA_MESSAGE_BUDGET = round(CONTENT * 0.42)
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
_LOGO_PATH = str(_ASSETS / "junior-guru.min.png")
_OPTICAL_SIZE_MAX = 32
CHICK_WIDTH = round(SIZE * 0.32)
ARROW_GLYPH = "\uf133"  # Bootstrap Icons "arrow-right-circle-fill" (U+F133)
ARROW_INSET_RATIO = 0.08  # shrink the white disc so the blue ring hides its edge
ARROW_RATIO = 2 / 3  # arrow is one third smaller than the chick

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
def load_logo(width: int) -> Image.Image:
    """Load the bundled junior.guru wordmark scaled to ``width`` pixels (keeps alpha)."""
    logo = Image.open(_LOGO_PATH).convert("RGBA")
    height = round(width * logo.height / logo.width)
    return logo.resize((width, height))


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

    Explicit newlines force a line break; a single-letter word never ends a line,
    it stays glued to the next word.
    """
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(_wrap_paragraph(draw, paragraph, font, max_width))
    return lines


def _wrap_paragraph(draw: Draw, text: str, font: Font, max_width: int) -> list[str]:
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


def _draw_center(
    draw: Draw, lines: list[str], font: Font, fill: str, top: float
) -> float:
    step = _line_height(font)
    for index, line in enumerate(lines):
        x = (SIZE - draw.textlength(line, font=font)) / 2
        draw.text((x, top + index * step), line, font=font, fill=fill)
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
    """Lay out the intro text above a bottom-right chick and bottom-left arrow."""
    chick = load_chick(CHICK_WIDTH)
    arrow = load_arrow(round(chick.height * ARROW_RATIO))  # one third smaller
    bottom = SIZE - PADDING
    chick_box = (
        SIZE - PADDING - chick.width,
        bottom - chick.height,
        SIZE - PADDING,
        bottom,
    )
    arrow_box = (PADDING, bottom - arrow.height, PADDING + arrow.width, bottom)
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


def _draw_words(
    draw: Draw, lines: list[list[Word]], size: int, fill: str, top: float
) -> None:
    space = draw.textlength(" ", font=load_font(size))
    step = _line_height(load_font(size))
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
    top = (SIZE - _line_height(load_font(size)) * len(lines)) / 2
    _draw_words(draw, lines, size, DARK, top)
    return image


# --- call to action ---------------------------------------------------------


def fit_plain(
    draw: Draw,
    text: str,
    max_width: int,
    max_height: float,
    max_size: int,
    make_font: Callable[[int], Font] = load_font,
    min_size: int = 12,
) -> tuple[Font, list[str]]:
    """Pick the largest plain-text size at which the wrapped lines fit the box."""
    font = make_font(min_size)
    lines = wrap_text(draw, text, font, max_width)
    for size in range(max_size, min_size, -2):
        font = make_font(size)
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


Chip = tuple[str, str, bool]  # text, fill colour, is a topic (gets middots around it)


def _cloud_chips(topics: list[str]) -> list[Chip]:
    """Dark prefix, then the gold topics, as one chip stream."""
    chips: list[Chip] = [(CTA_TOPICS_PREFIX, DARK, False)]
    chips += [(topic, CTA_TOPICS_COLOR, True) for topic in topics]
    return chips


def _cloud_lines(
    draw: Draw, chips: list[Chip], font: Font, gap: float, max_width: int
) -> list[list[Chip]]:
    lines: list[list[Chip]] = []
    line: list[Chip] = []
    width = 0.0
    for chip in chips:
        chip_width = draw.textlength(chip[0], font=font)
        extra = chip_width + (gap if line else 0.0)
        if line and width + extra > max_width:
            lines.append(line)
            line, width = [chip], chip_width
        else:
            line.append(chip)
            width += extra
    if line:
        lines.append(line)
    return lines


def _cloud_fits(draw, lines, font: Font, gap: float, max_width, max_height) -> bool:
    for line in lines:
        width = sum(draw.textlength(c[0], font=font) for c in line)
        width += gap * (len(line) - 1)
        if width > max_width:
            return False
    return _line_height(font) * len(lines) <= max_height


def fit_cloud(
    draw: Draw,
    chips: list[Chip],
    max_width: int,
    max_height: float,
    max_size: int = CTA_TOPICS_SIZE,
) -> tuple[Font, float, list[list[Chip]]]:
    """Pick the largest watermark size at which the spaced-out chips fill the box."""
    font = load_font(20, CTA_TOPICS_WEIGHT)
    gap = draw.textlength(f"   {CTA_TOPICS_SEP}   ", font=font)
    lines = _cloud_lines(draw, chips, font, gap, max_width)
    for size in range(max_size, 20, -2):
        font = load_font(size, CTA_TOPICS_WEIGHT)
        gap = draw.textlength(f"   {CTA_TOPICS_SEP}   ", font=font)
        lines = _cloud_lines(draw, chips, font, gap, max_width)
        if _cloud_fits(draw, lines, font, gap, max_width, max_height):
            break
    return font, gap, lines


def _draw_cloud_line(
    draw: Draw, line: list[Chip], font: Font, gap: float, sep_width: float, y: float
) -> None:
    """Draw one centered line of chips, with a middot between adjacent topics."""
    widths = [draw.textlength(chip[0], font=font) for chip in line]
    total = sum(widths) + gap * (len(line) - 1)
    x = (SIZE - total) / 2
    for position, ((text, fill, is_topic), chip_width) in enumerate(zip(line, widths)):
        draw.text((x, y), text, font=font, fill=fill)
        x += chip_width
        if position + 1 < len(line):
            if is_topic and line[position + 1][2]:  # middot between two topics
                draw.text(
                    (x + (gap - sep_width) / 2, y),
                    CTA_TOPICS_SEP,
                    font=font,
                    fill=CTA_TOPICS_COLOR,
                )
            x += gap


def _draw_cloud(
    draw: Draw, lines, font: Font, gap: float, region_top: float, region_height: float
) -> None:
    step = _line_height(font)
    band = region_height / len(lines)  # spread the lines across the whole region
    sep_width = draw.textlength(CTA_TOPICS_SEP, font=font)
    for index, line in enumerate(lines):
        y = region_top + band * (index + 0.5) - step / 2
        _draw_cloud_line(draw, line, font, gap, sep_width, y)


def fit_stacked_cloud(
    draw: Draw,
    topics: list[str],
    max_width: int,
    max_height: float,
    line_gap: float,
    max_size: int,
) -> tuple[Font, float, list[list[Chip]]]:
    """Like :func:`fit_cloud`, but reserving one extra line for the prefix above."""
    chips = [(topic, CTA_TOPICS_COLOR, True) for topic in topics]
    prefix = draw.textlength(CTA_TOPICS_PREFIX, font=load_font(20))
    font = load_font(20, CTA_TOPICS_WEIGHT)
    gap = draw.textlength(f"   {CTA_TOPICS_SEP}   ", font=font)
    lines = _cloud_lines(draw, chips, font, gap, max_width)
    for size in range(max_size, 20, -2):
        font = load_font(size, CTA_TOPICS_WEIGHT)
        gap = draw.textlength(f"   {CTA_TOPICS_SEP}   ", font=font)
        lines = _cloud_lines(draw, chips, font, gap, max_width)
        block = _line_height(font) * (len(lines) + 1) + line_gap
        fits = _cloud_fits(draw, lines, font, gap, max_width, max_height)
        if fits and block <= max_height and prefix <= max_width:
            break
    return font, gap, lines


def _draw_stacked_cloud(
    draw: Draw,
    topics: list[str],
    region_top: float,
    region_height: float,
    line_gap: float,
    max_size: int,
    max_width: int,
) -> None:
    """Prefix line, gap, then the topics cloud — centered in the region."""
    font, gap, lines = fit_stacked_cloud(
        draw, topics, max_width, region_height, line_gap, max_size
    )
    step = _line_height(font)
    sep_width = draw.textlength(CTA_TOPICS_SEP, font=font)
    block = step * (len(lines) + 1) + line_gap
    y = region_top + max(region_height - block, 0) / 2
    _draw_cloud_line(draw, [(CTA_TOPICS_PREFIX, DARK, False)], font, gap, sep_width, y)
    y += step + line_gap
    for line in lines:
        _draw_cloud_line(draw, line, font, gap, sep_width, y)
        y += step


def render_cta(
    topics: list[str] | None = None,
    height: int = SIZE,
    gap: float = CTA_GAP,
    logo_width: int = CTA_LOGO_WIDTH,
    message_size: int = CTA_MESSAGE_SIZE,
    topics_size: int = CTA_TOPICS_SIZE,
    stacked: bool = False,
    cloud_gap: float = CTA_GAP,
    cloud_width: int = CONTENT,
) -> Image.Image:
    """Centered logo, message and flat blue button, then a topics cloud filling the rest.

    ``height`` and ``gap`` default to the square card; the reel passes a taller
    canvas with wider gaps and a bigger logo, message and topics so the content
    stretches over the extra height. With ``stacked`` the cloud is laid out as a
    prefix line, then the topics below it, separated by ``cloud_gap``.
    """
    topics = topics or []
    image = Image.new("RGB", (SIZE, height), YELLOW)
    draw = ImageDraw.Draw(image)
    logo = load_logo(logo_width)
    text_font = load_font(CTA_TEXT_SIZE, weight=600)
    icon_font = load_icon_font(CTA_ICON_SIZE)
    button_width, button_height = _button_size(draw, text_font, icon_font)
    message_font, message_lines = fit_plain(
        draw,
        CTA_MESSAGE,
        CONTENT,
        CTA_MESSAGE_BUDGET,
        message_size,
        make_font=lambda size: load_font(size, CTA_MESSAGE_WEIGHT),
    )
    top = float(PADDING)
    image.paste(logo, (int((SIZE - logo.width) / 2), int(top)), logo)
    top += logo.height + gap  # same gap as below the message
    top = _draw_center(draw, message_lines, message_font, DARK, top)
    button_top = top + gap
    _draw_button(draw, (SIZE - button_width) / 2, button_top, text_font, icon_font)
    cloud_top = button_top + button_height + gap
    cloud_height = height - PADDING - cloud_top
    if topics and cloud_height > 0 and stacked:
        _draw_stacked_cloud(
            draw, topics, cloud_top, cloud_height, cloud_gap, topics_size, cloud_width
        )
    elif topics and cloud_height > 0:
        font, gap, lines = fit_cloud(
            draw, _cloud_chips(topics), cloud_width, cloud_height, max_size=topics_size
        )
        _draw_cloud(draw, lines, font, gap, cloud_top, cloud_height)
    return image


def render_section(section: Section) -> list[Image.Image]:
    """Render the full carousel: intro, one slide per paragraph, then the CTA."""
    return [
        render_intro(section.title, section.heading),
        *(render_paragraph(paragraph) for paragraph in section.paragraphs),
        render_cta(section.topics),
    ]


# --- reel (9:16 slideshow) --------------------------------------------------

REEL_WIDTH = 1080
REEL_HEIGHT = 1920  # 9:16 portrait, as Instagram/YouTube reels expect
REEL_FPS = 30  # Instagram Reels' native frame rate
REEL_HOOK_SECONDS = 3  # the intro hook stays on screen this long
REEL_CTA_SECONDS = 10  # the call to action stays a fixed time, regardless of text
READING_WPM = 200  # reading speed used to time the paragraph slides
REEL_MAX_SECONDS = 60  # a reel of a minute or longer is too long
REEL_CTA_HEIGHT = round(SIZE * 3 / 2)  # the reel call to action is 2:3, not square
REEL_CTA_GAP = 64  # wider gaps than the square card, but leaving the cloud room to grow
REEL_CTA_CLOUD_GAP = 28  # smaller gap inside the stacked cloud (prefix above topics)
# the topics block keeps half the padding of the square Instagram images
REEL_CTA_CLOUD_WIDTH = SIZE - 2 * (PADDING // 2)
REEL_CTA_LOGO_WIDTH = round(SIZE * 0.62)  # bigger logo on the reel card
REEL_CTA_MESSAGE_SIZE = 64  # bigger message on the reel card
REEL_CTA_TOPICS_SIZE = 112  # cap; the cloud grows to fill the room it is given
# Royalty-free background track, trimmed to a minute and stored as AAC (the codec
# the reel uses), so it muxes in by a plain stream copy; see assets/ for the licence.
REEL_MUSIC = str(_ASSETS / "slideshow-moire-main-version-02-01-15390.m4a")


def to_reel_frame(slide: Image.Image) -> Image.Image:
    """Center a slide on a 9:16 canvas padded with the slide's own background."""
    background = slide.getpixel((0, 0))
    frame = Image.new("RGB", (REEL_WIDTH, REEL_HEIGHT), background)
    frame.paste(
        slide, ((REEL_WIDTH - slide.width) // 2, (REEL_HEIGHT - slide.height) // 2)
    )
    return frame


def render_reel(section: Section) -> list[Image.Image]:
    """Render the carousel as 9:16 reel frames; the call to action is a taller 2:3 card."""
    slides = [
        render_intro(section.title, section.heading),
        *(render_paragraph(paragraph) for paragraph in section.paragraphs),
        render_cta(
            section.topics,
            height=REEL_CTA_HEIGHT,
            gap=REEL_CTA_GAP,
            logo_width=REEL_CTA_LOGO_WIDTH,
            message_size=REEL_CTA_MESSAGE_SIZE,
            topics_size=REEL_CTA_TOPICS_SIZE,
            stacked=True,
            cloud_gap=REEL_CTA_CLOUD_GAP,
            cloud_width=REEL_CTA_CLOUD_WIDTH,
        ),
    ]
    return [to_reel_frame(slide) for slide in slides]


def reading_seconds(text: str, wpm: int = READING_WPM) -> float:
    """How long it takes to read ``text`` at ``wpm`` words per minute."""
    return len(text.split()) / wpm * 60


def reel_durations(section: Section) -> list[float]:
    """Seconds per reel slide: a fixed hook, paragraphs by reading speed, a fixed CTA."""
    paragraphs = [
        "".join(run.text for run in paragraph) for paragraph in section.paragraphs
    ]
    return [
        float(REEL_HOOK_SECONDS),
        *(reading_seconds(paragraph) for paragraph in paragraphs),
        float(REEL_CTA_SECONDS),
    ]
