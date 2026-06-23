import pytest
from PIL import Image, ImageDraw

from jg.crowing.models import Run, Section
from jg.crowing.rendering import (
    BLUE,
    DARK,
    PADDING,
    SIZE,
    WHITE,
    YELLOW,
    fit_intro,
    glue_words,
    load_font,
    load_mono_font,
    render_cta,
    render_intro,
    render_paragraph,
    render_section,
    to_words,
    wrap_text,
)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


@pytest.fixture
def draw() -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(Image.new("RGB", (SIZE, SIZE)))


def test_wrap_text_keeps_all_words(draw):
    text = "one two three four five six seven eight nine ten"
    lines = wrap_text(draw, text, load_font(48), max_width=200)
    assert " ".join(lines).split() == text.split()


def test_wrap_text_respects_width(draw):
    text = "one two three four five six seven eight nine ten"
    font = load_font(48)
    lines = wrap_text(draw, text, font, max_width=200)
    assert len(lines) > 1
    assert all(draw.textlength(line, font=font) <= 200 for line in lines)


def test_load_mono_font_is_liberation_mono():
    assert load_mono_font(40).getname()[0] == "Liberation Mono"


def test_intro_heading_is_larger_than_title(draw):
    _, _, title_font, heading_font = fit_intro(
        draw, "Git a GitHub", "Řešení problémů s Gitem"
    )
    assert heading_font.size > title_font.size


def test_intro_title_is_monospace(draw):
    _, _, title_font, _ = fit_intro(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert title_font.getname()[0] == "Liberation Mono"


def test_intro_heading_uses_inter(draw):
    _, _, _, heading_font = fit_intro(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert heading_font.getname()[0] == "Inter"


def test_intro_heading_does_not_orphan_single_letter_word(draw):
    _, heading_lines, _, _ = fit_intro(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert all(line.split()[-1] != "s" for line in heading_lines)


def test_intro_text_is_left_aligned():
    image = render_intro("Git a GitHub", "Řešení problémů s Gitem")
    pixels = image.load()
    dark = hex_to_rgb(DARK)
    left_edge = min(x for x in range(SIZE) for y in range(SIZE) if pixels[x, y] == dark)
    assert left_edge < PADDING + 30


def test_to_words_groups_styled_segments():
    runs = [Run("hello wor"), Run("ld", bold=True), Run(" there", italic=True)]
    words = to_words(runs)
    assert [["".join(s[0] for s in w)] for w in words] == [
        ["hello"],
        ["world"],
        ["there"],
    ]
    # the middle word mixes plain and bold segments
    assert words[1] == [("wor", False, False), ("ld", True, False)]
    assert words[2] == [("there", False, True)]


def test_to_words_keeps_all_text_for_long_paragraph():
    runs = [Run("word " * 30)]
    words = to_words(runs)
    assert len(words) == 30


def test_glue_words_keeps_single_letter_word_with_next():
    words = to_words([Run("problémů s Gitem")])
    units = ["".join(segment[0] for segment in unit) for unit in glue_words(words)]
    assert "s Gitem" in units


def test_glue_words_preserves_styling_of_the_following_word():
    words = to_words([Run("a "), Run("Gitem", bold=True)])
    assert glue_words(words) == [[("a ", False, False), ("Gitem", True, False)]]


@pytest.mark.parametrize(
    "image, color",
    [
        (render_intro("Git a GitHub", "Řešení problémů"), YELLOW),
        (render_paragraph([Run("Nějaký odstavec textu.")]), WHITE),
        (render_cta(), YELLOW),
    ],
)
def test_background_color(image, color):
    assert image.size == (SIZE, SIZE)
    assert image.getpixel((5, 5)) == hex_to_rgb(color)


def _button_bbox(image) -> tuple[int, int, int, int]:
    blue = hex_to_rgb(BLUE)
    pixels = image.load()
    xs = [x for x in range(SIZE) for y in range(SIZE) if pixels[x, y] == blue]
    ys = [y for y in range(SIZE) for x in range(SIZE) if pixels[x, y] == blue]
    return min(xs), min(ys), max(xs), max(ys)


def test_cta_button_is_bootstrap_blue_with_white_glyphs():
    image = render_cta()
    pixels = image.load()
    blue, white = hex_to_rgb(BLUE), hex_to_rgb(WHITE)
    blues = sum(pixels[x, y] == blue for x in range(SIZE) for y in range(SIZE))
    whites = sum(pixels[x, y] == white for x in range(SIZE) for y in range(SIZE))
    assert blues > 20000  # a sizable blue button
    assert whites > 200  # the icon and the text are white


def test_cta_button_corners_are_subtly_rounded_not_a_pill():
    image = render_cta()
    pixels = image.load()
    blue = hex_to_rgb(BLUE)
    x0, y0, x1, y1 = _button_bbox(image)
    height = y1 - y0 + 1

    def width_at(y: int) -> int:
        row = [x for x in range(x0, x1 + 1) if pixels[x, y] == blue]
        return max(row) - min(row) + 1 if row else 0

    full = width_at((y0 + y1) // 2)
    # by 15 % down the corner is already full width (a pill would still be far from it)
    assert width_at(y0 + round(height * 0.15)) >= full - 2
    # but the very top row is inset by the small radius, so it is not a plain rectangle
    assert width_at(y0) < full


def test_cta_button_icon_sits_left_of_the_text():
    image = render_cta()
    pixels = image.load()
    white = hex_to_rgb(WHITE)
    x0, _, x1, _ = _button_bbox(image)
    white_xs = [
        x for x in range(x0, x1 + 1) for y in range(SIZE) if pixels[x, y] == white
    ]
    # leftmost white (icon) is clearly left of the button centre
    assert min(white_xs) < (x0 + x1) // 2


def test_render_paragraph_with_markup_draws_dark_text():
    runs = [
        Run("plain "),
        Run("bold", bold=True),
        Run(" and "),
        Run("italic", italic=True),
    ]
    image = render_paragraph(runs)
    colors = {image.getpixel((x, y)) for x in range(SIZE) for y in range(SIZE)}
    assert hex_to_rgb(WHITE) in colors
    assert any(sum(c) < 200 for c in colors)  # dark glyph pixels present


def test_render_section_counts_intro_paragraphs_and_cta():
    section = Section(
        title="T",
        heading="H",
        paragraphs=[[Run("a")], [Run("b")], [Run("c")]],
    )
    images = render_section(section)
    assert len(images) == 1 + 3 + 1
    assert images[0].getpixel((5, 5)) == hex_to_rgb(YELLOW)
    assert images[1].getpixel((5, 5)) == hex_to_rgb(WHITE)
    assert images[-1].getpixel((5, 5)) == hex_to_rgb(YELLOW)
