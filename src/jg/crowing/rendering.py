"""Pure functions turning a :class:`Section` into Instagram-ready square images."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from itertools import pairwise
from typing import NamedTuple

from PIL import Image, ImageChops, ImageDraw, ImageFont

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import RichText, Run, Section, Shot, Story


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

CTA_MESSAGE_SIZE = 48  # smaller than the logo and topics
CTA_MESSAGE_WEIGHT = 600
CTA_TEXT_SIZE = 56
CTA_ICON_SIZE = 60
CTA_ICON_GAP = 22
CTA_PADDING_X = 56
CTA_PADDING_Y = 34
CTA_LOGO_WIDTH = round(SIZE * 0.5)  # junior.guru wordmark above the message
CTA_GAP = 72  # vertical gap between logo, message, button and cloud
CTA_TOPICS_SIZE = 72
CTA_TOPICS_COLOR = "#998c00"  # dark gold watermark, readable on the light yellow
CTA_TOPICS_WEIGHT = 400  # regular weight for the topics, not bold
CTA_TOPICS_SEP = "·"  # middot between topics on the same line
CTA_MESSAGE_BUDGET = round(CONTENT * 0.42)
BUTTON_RADIUS_RATIO = 0.1  # only slightly rounded corners, not a pill
WORDMARK = "JUNIOR.GURU"  # small blue monospace signature on paragraph and shot slides
WORDMARK_SIZE = 30


@dataclass(frozen=True)
class CtaContent:
    """The text, button label and icon that vary between call-to-action cards."""

    message: str
    button_text: str
    icon: str


HANDBOOK_CTA = CtaContent(
    message="Zajímá tě tohle téma?\nOtevři si příručku a čti dál!",
    button_text="junior.guru/handbook",
    icon="",  # Bootstrap Icons "journals"
)
EVENT_CTA = CtaContent(
    message="Zajímá tě tahle online akce?\nPohlídej si ji!",
    button_text="junior.guru/events",
    icon="",  # Bootstrap Icons "play-circle-fill"
)

STORY_CTA = CtaContent(
    message="Pravdivě o kariéře v IT.\nPřečti si celý rozhovor!",
    button_text="junior.guru/stories",
    icon="",  # Bootstrap Icons "file-text"
)

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

Segment = tuple[str, bool, bool, bool]  # text, bold, italic, code
Word = list[Segment]
Box = tuple[float, float, float, float]
Font = ImageFont.FreeTypeFont
Draw = ImageDraw.ImageDraw


@cache
def load_font(size: int, weight: int = 400, italic: bool = False) -> Font:
    """Load Inter at ``size`` pixels with the given weight and slant."""
    font = ImageFont.truetype(_FONT_PATHS[italic], size)
    font.set_variation_by_axes([min(size, _OPTICAL_SIZE_MAX), weight])
    return font


def _segment_font(size: int, bold: bool, italic: bool, code: bool = False) -> Font:
    if code:
        return load_mono_font(size)
    return load_font(size, 700 if bold else 400, italic)


@cache
def load_icon_font(size: int) -> Font:
    """Load the bundled Bootstrap Icons font at ``size`` pixels."""
    return ImageFont.truetype(_ICON_PATH, size)


@cache
def load_mono_font(size: int) -> Font:
    """Load the bundled Liberation Mono font at ``size`` pixels (for monospace text)."""
    return ImageFont.truetype(_MONO_PATH, size)


@cache
def load_chick(width: int) -> Image.Image:
    """Load the bundled chick illustration scaled to ``width`` pixels (keeps alpha)."""
    chick = Image.open(_CHICK_PATH).convert("RGBA")
    height = round(width * chick.height / chick.width)
    return chick.resize((width, height))


@cache
def load_logo(width: int) -> Image.Image:
    """Load the bundled junior.guru wordmark scaled to ``width`` pixels (keeps alpha)."""
    logo = Image.open(_LOGO_PATH).convert("RGBA")
    height = round(width * logo.height / logo.width)
    return logo.resize((width, height))


@cache
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


def _sticks_back(text: str) -> bool:
    """A two-letter all-caps word (e.g. "AI") never starts a line: it glues backwards."""
    core = text.rstrip(".,:;!?")
    return len(core) == 2 and core.isalpha() and core.isupper()


def _glue_text(words: list[str]) -> list[str]:
    """Glue single-letter words to the next word and two-letter all-caps to the previous."""
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
    glued: list[str] = []
    for unit in units:
        if glued and _sticks_back(unit):
            glued[-1] = f"{glued[-1]} {unit}"
        else:
            glued.append(unit)
    return glued


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


def intro_layout(
    draw: Draw, title: str, heading: str, corner: Image.Image | None = None
) -> IntroLayout:
    """Lay out the intro text above a bottom-right image and bottom-left arrow.

    ``corner`` overrides the default chick illustration in the bottom-right corner
    (e.g. an event's circular speaker avatar).
    """
    chick = corner if corner is not None else load_chick(CHICK_WIDTH)
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


def render_intro(
    title: str, heading: str, corner_image: Image.Image | None = None
) -> Image.Image:
    """Intro slide: monospace title, heading, arrow bottom-left, image bottom-right.

    The bottom-right image is the chick illustration by default, or ``corner_image``
    (e.g. an event's circular speaker avatar) when given.
    """
    image = Image.new("RGB", (SIZE, SIZE), YELLOW)
    draw = ImageDraw.Draw(image)
    layout = intro_layout(draw, title, heading, corner_image)
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
            current.append((part, run.bold, run.italic, run.code))
    return current


def glue_words(words: list[Word]) -> list[Word]:
    """Glue single-letter words to the next word and two-letter all-caps to the previous."""
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
    glued: list[Word] = []
    for unit in units:
        if glued and _sticks_back(_word_text(unit)):
            glued[-1] = _with_trailing_space(glued[-1]) + unit
        else:
            glued.append(unit)
    return glued


def _word_length(word: Word) -> int:
    return sum(len(text) for text, *_ in word)


def _word_text(word: Word) -> str:
    return "".join(text for text, *_ in word)


def _with_trailing_space(word: Word) -> Word:
    text, bold, italic, code = word[-1]
    return word[:-1] + [(f"{text} ", bold, italic, code)]


def _word_width(draw: Draw, word: Word, size: int) -> float:
    return sum(
        draw.textlength(text, font=_segment_font(size, b, i, c))
        for text, b, i, c in word
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
            for text, bold, italic, code in word:
                font = _segment_font(size, bold, italic, code)
                draw.text(
                    (x, top + index * step),
                    text,
                    font=font,
                    fill=BLUE if code else fill,
                )
                x += draw.textlength(text, font=font)
            x += space


def render_paragraph(
    runs: RichText, height: int = SIZE, wordmark_size: int = WORDMARK_SIZE
) -> Image.Image:
    """A content slide: white background, left-aligned dark paragraph with markup.

    ``height`` defaults to the square image; the reel passes the taller 2:3 height so
    the JUNIOR.GURU signature sits at the bottom of the 2:3 canvas (and a bit larger).
    """
    image = Image.new("RGB", (SIZE, height), WHITE)
    draw = ImageDraw.Draw(image)
    size, lines = fit_words(draw, glue_words(to_words(runs)), CONTENT, CONTENT)
    top = (height - _line_height(load_font(size)) * len(lines)) / 2
    _draw_words(draw, lines, size, DARK, top)
    draw_wordmark(image, wordmark_size)
    return image


def draw_wordmark(image: Image.Image, size: int = WORDMARK_SIZE) -> None:
    """Draw the small, thin blue JUNIOR.GURU monospace signature in the bottom-right corner."""
    draw = ImageDraw.Draw(image)
    draw.text(
        (image.width - PADDING, image.height - PADDING),
        WORDMARK,
        font=load_mono_font(size),
        fill=BLUE,
        anchor="rs",
    )


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


def _button_size(
    draw: Draw, text_font: Font, icon_font: Font, content: CtaContent
) -> tuple[float, float]:
    icon_width = draw.textlength(content.icon, font=icon_font)
    text_width = draw.textlength(content.button_text, font=text_font)
    ascent, descent = text_font.getmetrics()
    width = icon_width + CTA_ICON_GAP + text_width + 2 * CTA_PADDING_X
    height = ascent + descent + 2 * CTA_PADDING_Y
    return width, height


def _draw_button(
    draw: Draw,
    left: float,
    top: float,
    text_font: Font,
    icon_font: Font,
    content: CtaContent,
) -> None:
    width, height = _button_size(draw, text_font, icon_font, content)
    box = (left, top, left + width, top + height)
    draw.rounded_rectangle(box, radius=round(height * BUTTON_RADIUS_RATIO), fill=BLUE)
    icon_width = draw.textlength(content.icon, font=icon_font)
    content_left = left + CTA_PADDING_X
    middle = top + height / 2
    draw.text(
        (content_left, middle), content.icon, font=icon_font, fill=WHITE, anchor="lm"
    )
    text_left = content_left + icon_width + CTA_ICON_GAP
    draw.text(
        (text_left, middle),
        content.button_text,
        font=text_font,
        fill=WHITE,
        anchor="lm",
    )


Chip = tuple[str, str, bool]  # text, fill colour, is a topic (gets middots around it)


def _cloud_chips(topics: list[str]) -> list[Chip]:
    """The gold topics as one chip stream."""
    return [(topic, CTA_TOPICS_COLOR, True) for topic in topics]


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


def render_cta(
    topics: list[str] | None = None,
    height: int = SIZE,
    gap: float = CTA_GAP,
    logo_width: int = CTA_LOGO_WIDTH,
    message_size: int = CTA_MESSAGE_SIZE,
    topics_size: int = CTA_TOPICS_SIZE,
    cloud_width: int = CONTENT,
    stretch: bool = False,
    content: CtaContent = HANDBOOK_CTA,
) -> Image.Image:
    """Centered logo, message and flat blue button, then a topics cloud filling the rest.

    ``content`` supplies the message, button label and icon that differ per context
    (handbook vs event); pass no ``topics`` for a card without the topics cloud.
    ``height``/``gap`` default to the square card. With ``stretch`` the gaps between
    the four elements are equal and absorb all slack, so the content spans the card
    top to bottom (used by the taller 2:3 reel call to action).
    """
    topics = topics or []
    image = Image.new("RGB", (SIZE, height), YELLOW)
    draw = ImageDraw.Draw(image)
    logo = load_logo(logo_width)
    text_font = load_font(CTA_TEXT_SIZE, weight=600)
    icon_font = load_icon_font(CTA_ICON_SIZE)
    button = _button_size(draw, text_font, icon_font, content)
    message_font, message_lines = fit_plain(
        draw,
        content.message,
        CONTENT,
        CTA_MESSAGE_BUDGET,
        message_size,
        make_font=lambda size: load_font(size, CTA_MESSAGE_WEIGHT),
    )
    args = (
        draw,
        image,
        logo,
        message_font,
        message_lines,
        button,
        text_font,
        icon_font,
        content,
    )
    # Stretching only makes sense with a topics cloud to absorb the slack; without one
    # it would push the button to the very bottom, so fall back to the centered stack.
    if stretch and topics:
        _draw_cta_stretched(*args, topics, topics_size, cloud_width, height)
    else:
        _draw_cta_stacked(*args, topics, topics_size, cloud_width, height, gap)
    return image


def _logo_visible_span(logo: Image.Image) -> tuple[int, int]:
    """Top offset and height of the logo's visible ink within its (padded) image.

    The logo PNG's alpha isn't tight, so the ink is measured by compositing on white.
    """
    on_card = Image.new("RGB", logo.size, YELLOW)
    on_card.paste(logo, (0, 0), logo)
    diff = ImageChops.difference(on_card, Image.new("RGB", logo.size, YELLOW))
    ink = diff.convert("L").point(lambda value: 255 if value > 16 else 0)
    box = ink.getbbox()
    return box[1], box[3] - box[1]


def _draw_cta_stacked(
    draw,
    image,
    logo,
    message_font,
    message_lines,
    button,
    text_font,
    icon_font,
    content,
    topics,
    topics_size,
    cloud_width,
    height,
    gap,
):
    """Fixed ``gap`` between elements; the cloud fills the rest, or the block centers.

    With topics the cloud stretches to the bottom (so the block already spans the card),
    otherwise the logo/message/button block is centered vertically so it isn't top-heavy.
    """
    button_width, button_height = button
    message_height = _line_height(message_font) * len(message_lines)
    # the logo PNG has some built-in vertical padding; center on its visible bounds
    logo_top, logo_visible = _logo_visible_span(logo)
    if topics:
        logo_y = float(PADDING)
        content_top = logo_y + logo.height
    else:
        block = logo_visible + gap + message_height + gap + button_height
        logo_y = (height - block) / 2 - logo_top
        content_top = logo_y + logo_top + logo_visible
    image.paste(logo, (int((SIZE - logo.width) / 2), int(logo_y)), logo)
    top = content_top + gap
    top = _draw_center(draw, message_lines, message_font, DARK, top)
    button_top = top + gap
    _draw_button(
        draw, (SIZE - button_width) / 2, button_top, text_font, icon_font, content
    )
    cloud_top = button_top + button_height + gap
    cloud_height = height - PADDING - cloud_top
    if topics and cloud_height > 0:
        font, cloud_gap, lines = fit_cloud(
            draw, _cloud_chips(topics), cloud_width, cloud_height, max_size=topics_size
        )
        _draw_cloud(draw, lines, font, cloud_gap, cloud_top, cloud_height)


def _draw_cta_stretched(
    draw,
    image,
    logo,
    message_font,
    message_lines,
    button,
    text_font,
    icon_font,
    content,
    topics,
    topics_size,
    cloud_width,
    height,
):
    """Equal gaps between the four elements, absorbing all slack top to bottom."""
    button_width, button_height = button
    message_height = _line_height(message_font) * len(message_lines)
    available = height - 2 * PADDING
    fixed = logo.height + message_height + button_height
    font = cloud_gap = lines = None
    cloud_height = 0.0
    if topics and available - fixed > 0:
        font, cloud_gap, lines = fit_cloud(
            draw,
            _cloud_chips(topics),
            cloud_width,
            available - fixed,
            max_size=topics_size,
        )
        cloud_height = _line_height(font) * len(lines)
    step = max((available - fixed - cloud_height) / (3 if lines else 2), 0)
    top = float(PADDING)
    image.paste(logo, (int((SIZE - logo.width) / 2), int(top)), logo)
    top += logo.height + step
    top = _draw_center(draw, message_lines, message_font, DARK, top) + step
    _draw_button(draw, (SIZE - button_width) / 2, top, text_font, icon_font, content)
    top += button_height + step
    if lines:
        _draw_cloud(draw, lines, font, cloud_gap, top, cloud_height)


# --- event screenshots (composing onto squares) -----------------------------


def circle_image(image: Image.Image, width: int = CHICK_WIDTH) -> Image.Image:
    """Center-crop ``image`` to a circle of ``width`` pixels with a transparent outside.

    Used for an event's speaker avatar in the intro's bottom-right corner. The mask is
    drawn at 4x and downscaled so the circle's edge stays smooth.
    """
    side = min(image.width, image.height)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    square = (
        image.convert("RGBA")
        .crop((left, top, left + side, top + side))
        .resize((width, width), Image.Resampling.LANCZOS)
    )
    scale = 4
    mask = Image.new("L", (width * scale, width * scale), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, width * scale, width * scale), fill=255)
    square.putalpha(mask.resize((width, width), Image.Resampling.LANCZOS))
    return square


def compose_card(
    screenshot: Image.Image,
    canvas_width: int = SIZE,
    canvas_height: int = SIZE,
    padding: int = PADDING,
    background: str = WHITE,
    sign: bool = False,
    wordmark_size: int = WORDMARK_SIZE,
) -> Image.Image:
    """Fit ``screenshot`` onto a ``background`` card, keeping its aspect ratio, centered.

    The screenshot is scaled to fit inside the padded box and centered, so cards sharing
    a padding never let it touch the borders. With ``sign`` the JUNIOR.GURU signature is
    added to the bottom-right corner (of the whole card, whatever its shape).
    """
    canvas = Image.new("RGB", (canvas_width, canvas_height), background)
    box_width = canvas_width - 2 * padding
    box_height = canvas_height - 2 * padding
    scale = min(box_width / screenshot.width, box_height / screenshot.height)
    width = max(1, round(screenshot.width * scale))
    height = max(1, round(screenshot.height * scale))
    resized = screenshot.convert("RGB").resize(
        (width, height), Image.Resampling.LANCZOS
    )
    canvas.paste(resized, ((canvas_width - width) // 2, (canvas_height - height) // 2))
    if sign:
        draw_wordmark(canvas, wordmark_size)
    return canvas


def compose_square(
    screenshot: Image.Image,
    size: int = SIZE,
    padding: int = PADDING,
    background: str = WHITE,
    sign: bool = False,
) -> Image.Image:
    """Fit ``screenshot`` onto a ``background`` square (a square :func:`compose_card`)."""
    return compose_card(screenshot, size, size, padding, background, sign)


def render_section(section: Section) -> list[Image.Image]:
    """Render the full carousel: intro, one slide per paragraph, then the CTA."""
    return [
        render_intro(section.title, section.heading),
        *(render_paragraph(paragraph) for paragraph in section.paragraphs),
        render_cta(section.topics),
    ]


STORY_INTRO_LABEL = "Rozhovor"  # small monospace prefix on a story's intro slide
STORY_PREVIEW_GRADIENT_RATIO = 0.28  # bottom band that fades the hard crop into white


def _fade_bottom(image: Image.Image, band_ratio: float = STORY_PREVIEW_GRADIENT_RATIO):
    """Blend ``image``'s bottom band into white, transparent at the top of the band.

    Softens the preview's hard bottom crop so it doesn't end in a sharp cut-off line.
    """
    image = image.convert("RGB")
    width, height = image.size
    band = max(1, round(height * band_ratio))
    ramp = Image.new("L", (1, band))
    ramp.putdata(
        [round(255 * y / (band - 1)) for y in range(band)] if band > 1 else [0]
    )
    mask = ramp.resize((width, band))
    region = image.crop((0, height - band, width, height))
    white = Image.new("RGB", (width, band), WHITE)
    image.paste(Image.composite(white, region, mask), (0, height - band))
    return image


def _fill(screenshot: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale ``screenshot`` to exactly ``size``, full-bleed (the preview has no padding)."""
    return screenshot.convert("RGB").resize(size, Image.Resampling.LANCZOS)


def render_story_preview(preview: Image.Image) -> Image.Image:
    """The square carousel preview: the top square of the shot, full-bleed, faded bottom."""
    width = preview.width
    square = preview.crop((0, 0, width, width))
    return _fade_bottom(_fill(square, (SIZE, SIZE)))


def _blockquote_square(shot: Shot) -> Image.Image:
    """Compose a blockquote screenshot onto its signed white square (the carousel slide)."""
    return compose_square(shot.image, background=shot.background, sign=shot.sign)


def render_story(
    story: Story,
    corner_image: Image.Image,
    preview: Image.Image,
    blockquotes: list[Shot],
) -> list[Image.Image]:
    """Render the full story carousel: intro, lead slides, blockquotes, preview, then CTA.

    ``corner_image`` is the story's circled ``.article-image`` photo, shown in the
    intro's bottom-right corner in place of the chick. ``blockquotes`` are the quote
    screenshots, each composed onto a signed white square. ``preview`` is the 9:16
    page-top screenshot; its top square is placed full-bleed (no padding, unlike the rest).
    """
    return [
        render_intro(STORY_INTRO_LABEL, story.title, corner_image=corner_image),
        *(render_paragraph(paragraph) for paragraph in story.paragraphs),
        *(_blockquote_square(blockquote) for blockquote in blockquotes),
        render_story_preview(preview),
        render_cta(content=STORY_CTA),
    ]


# --- reel (9:16 slideshow) --------------------------------------------------

REEL_WIDTH = 1080
REEL_HEIGHT = 1920  # 9:16 portrait, as Instagram/YouTube reels expect
REEL_FPS = 30  # Instagram Reels' native frame rate
REEL_HOOK_SECONDS = 3  # the intro hook stays on screen this long
REEL_CTA_SECONDS = 10  # the call to action stays a fixed time, regardless of text
READING_WPM = 200  # reading speed used to time the paragraph slides
REEL_MAX_SECONDS = 90  # a reel this long or longer is rejected
REEL_WARN_SECONDS = 60  # past this the reel is getting long, warn the user
REEL_CARD_HEIGHT = round(
    SIZE * 3 / 2
)  # reel paragraph and CTA cards are 2:3, not square
REEL_WORDMARK_SIZE = 44  # the signature is larger on the reel's white slides
# the topics block keeps the same side padding as the square Instagram images
REEL_CTA_CLOUD_WIDTH = CONTENT
REEL_CTA_LOGO_WIDTH = round(SIZE * 0.62)  # bigger logo on the reel card
REEL_CTA_MESSAGE_SIZE = 64  # bigger message on the reel card
REEL_CTA_TOPICS_SIZE = 44  # cap for the reel topics, a touch smaller than before
# Royalty-free background track, stored as low-bitrate mono AAC (the codec the reel
# uses) so it muxes in by a plain stream copy; longer than any reel, so -shortest
# trims it to the video. See assets/ for the licence.
REEL_MUSIC = str(_ASSETS / "Kicking It - Dyalla.m4a")


def to_reel_frame(slide: Image.Image) -> Image.Image:
    """Center a slide on a 9:16 canvas padded with the slide's own background."""
    background = slide.getpixel((0, 0))
    frame = Image.new("RGB", (REEL_WIDTH, REEL_HEIGHT), background)
    frame.paste(
        slide, ((REEL_WIDTH - slide.width) // 2, (REEL_HEIGHT - slide.height) // 2)
    )
    return frame


def render_reel(
    section: Section, intro: Image.Image | None = None
) -> list[Image.Image]:
    """Render the carousel as 9:16 reel frames; the call to action is a taller 2:3 card.

    ``intro`` lets the caller pass in the square intro slide already rendered for the
    carousel, since it's identical here and re-rendering it would repeat the same
    font-fitting work for no visual difference.
    """
    slides = [
        intro if intro is not None else render_intro(section.title, section.heading),
        *(
            render_paragraph(
                paragraph, height=REEL_CARD_HEIGHT, wordmark_size=REEL_WORDMARK_SIZE
            )
            for paragraph in section.paragraphs
        ),
        render_cta(
            section.topics,
            height=REEL_CARD_HEIGHT,
            logo_width=REEL_CTA_LOGO_WIDTH,
            message_size=REEL_CTA_MESSAGE_SIZE,
            topics_size=REEL_CTA_TOPICS_SIZE,
            cloud_width=REEL_CTA_CLOUD_WIDTH,
            stretch=True,
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


REEL_TRANSITION_SECONDS = 0.25  # quick swipe cut between slides, not a hard cut


def transition_durations(
    durations: list[float], transition_seconds: float = REEL_TRANSITION_SECONDS
) -> list[float]:
    """Per-gap crossfade duration, clamped so a transition never outlasts either slide it joins.

    The two transitions touching an interior slide are also scaled down together so
    they never add up to more than that slide's own duration — otherwise the slide
    would vanish into a three-way blend instead of getting any standalone time.
    """
    gaps = [min(transition_seconds, a, b) for a, b in pairwise(durations)]
    changed = True
    while changed:
        changed = False
        for index in range(1, len(gaps)):
            slide = durations[index]
            total = gaps[index - 1] + gaps[index]
            if total > slide:
                scale = slide / total
                gaps[index - 1] *= scale
                gaps[index] *= scale
                changed = True
    return gaps


def reel_total_seconds(
    durations: list[float], transition_seconds: float = REEL_TRANSITION_SECONDS
) -> float:
    """Total reel length once consecutive slides overlap by their transition duration."""
    return sum(durations) - sum(transition_durations(durations, transition_seconds))


REEL_CTA_RESCUE_SECONDS = 5  # if the reel is too long, first try a shorter CTA
REEL_SLIDE_MAX_SECONDS = 10  # however long its text, no slide stays on screen longer


def fit_reel_durations(
    durations: list[float], transition_seconds: float = REEL_TRANSITION_SECONDS
) -> list[float]:
    """Cap every slide at :data:`REEL_SLIDE_MAX_SECONDS`, then keep the reel under the limit.

    A slide with a lot of text would otherwise linger; past ten seconds the viewer has
    either read it or scrolled on. If the reel is still too long, the CTA is shortened to
    the rescue length, and :class:`InvalidInputError` is raised if even that can't bring
    the reel under :data:`REEL_MAX_SECONDS`.
    """
    durations = [min(duration, float(REEL_SLIDE_MAX_SECONDS)) for duration in durations]
    if reel_total_seconds(durations, transition_seconds) < REEL_MAX_SECONDS:
        return durations
    rescued = [*durations[:-1], min(durations[-1], float(REEL_CTA_RESCUE_SECONDS))]
    total = reel_total_seconds(rescued, transition_seconds)
    if total >= REEL_MAX_SECONDS:
        raise InvalidInputError(
            f"The reel would be {round(total)}s long; keep it under {REEL_MAX_SECONDS}s "
            "by choosing a page with fewer or shorter paragraphs"
        )
    return rescued


def event_reel_durations(shots: list[Shot]) -> list[float]:
    """Seconds per event reel slide: a fixed hook, screenshots by reading speed, fixed CTA."""
    return [
        float(REEL_HOOK_SECONDS),
        *(shot.reading_seconds for shot in shots),
        float(REEL_CTA_SECONDS),
    ]


REEL_PREVIEW_SECONDS = 3  # the wordless page preview is a brief visual beat


def story_reel_durations(story: Story, blockquotes: list[Shot]) -> list[float]:
    """Seconds per story reel slide: hook, lead + blockquotes by reading, preview, CTA."""
    paragraphs = [
        "".join(run.text for run in paragraph) for paragraph in story.paragraphs
    ]
    return [
        float(REEL_HOOK_SECONDS),
        *(reading_seconds(paragraph) for paragraph in paragraphs),
        *(shot.reading_seconds for shot in blockquotes),
        float(REEL_PREVIEW_SECONDS),
        float(REEL_CTA_SECONDS),
    ]


def render_story_preview_frame(preview: Image.Image) -> Image.Image:
    """The 9:16 reel preview: the whole shot filled full-bleed to the frame, faded bottom."""
    return _fade_bottom(_fill(preview, (REEL_WIDTH, REEL_HEIGHT)))


def _shot_reel_slide(shot: Shot) -> Image.Image:
    """Lay a screenshot out for the reel: on the taller 2:3 card, or on the square.

    ``reel_card`` shots (the event's media card, a story's blockquotes) are composed onto
    the 2:3 canvas, so they fill the portrait frame instead of being shrunk to a square;
    their JUNIOR.GURU signature then sits at the bottom-right of that 2:3 card, larger.
    The rest keep the same square as the carousel, padded onto the frame.
    """
    if not shot.reel_card:
        return compose_square(shot.image, background=shot.background, sign=shot.sign)
    return compose_card(
        shot.image,
        SIZE,
        REEL_CARD_HEIGHT,
        background=shot.background,
        sign=shot.sign,
        wordmark_size=REEL_WORDMARK_SIZE,
    )


def render_story_reel(
    story: Story,
    intro: Image.Image,
    preview: Image.Image,
    blockquotes: list[Shot],
) -> list[Image.Image]:
    """Render the story carousel as 9:16 reel frames; the CTA becomes a taller 2:3 card.

    ``intro`` is the square intro slide already rendered for the carousel, reused here
    unchanged. ``blockquotes`` are the quote squares, each centered on a 9:16 frame.
    ``preview`` is the 9:16 page-top screenshot, shown full-bleed.
    """
    slides = [
        intro,
        *(
            render_paragraph(
                paragraph, height=REEL_CARD_HEIGHT, wordmark_size=REEL_WORDMARK_SIZE
            )
            for paragraph in story.paragraphs
        ),
        *(_shot_reel_slide(blockquote) for blockquote in blockquotes),
    ]
    frames = [to_reel_frame(slide) for slide in slides]
    frames.append(render_story_preview_frame(preview))
    frames.append(
        to_reel_frame(
            render_cta(
                height=REEL_CARD_HEIGHT,
                logo_width=REEL_CTA_LOGO_WIDTH,
                message_size=REEL_CTA_MESSAGE_SIZE,
                stretch=True,
                content=STORY_CTA,
            )
        )
    )
    return frames


def render_event_reel(
    intro: Image.Image, shots: list[Shot], content: CtaContent
) -> list[Image.Image]:
    """Render the event carousel as 9:16 reel frames; the CTA becomes a taller 2:3 card.

    ``intro`` is the square intro slide already rendered for the carousel. The ``shots``
    are laid out by :func:`_shot_reel_slide` — the media card fills the taller 2:3 canvas,
    the lead and note items keep their carousel square — and each is then centered on the
    9:16 canvas padded with its own background, while the call to action is re-rendered as
    a stretched 2:3 card so its text fills the taller frame.
    """
    cta = render_cta(
        height=REEL_CARD_HEIGHT,
        logo_width=REEL_CTA_LOGO_WIDTH,
        message_size=REEL_CTA_MESSAGE_SIZE,
        stretch=True,
        content=content,
    )
    slides = [intro, *(_shot_reel_slide(shot) for shot in shots), cta]
    return [to_reel_frame(slide) for slide in slides]
