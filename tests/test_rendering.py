import pytest
from PIL import Image, ImageDraw

from jg.crowing.models import Run, Section
from jg.crowing.rendering import (
    BLUE,
    SIZE,
    WHITE,
    YELLOW,
    fit_intro,
    load_font,
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


def test_intro_heading_is_larger_than_title(draw):
    title_lines, heading_lines, title_font, heading_font = fit_intro(
        draw, "Git a GitHub:", "Řešení problémů s Gitem"
    )
    assert heading_font.size > title_font.size


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


def test_cta_has_blue_button_in_the_centre():
    image = render_cta()
    assert image.getpixel((SIZE // 2, SIZE // 2)) == hex_to_rgb(BLUE)


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
