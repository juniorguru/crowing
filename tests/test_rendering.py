import pytest
from PIL import ImageDraw

from jg.crowing.models import Section
from jg.crowing.rendering import (
    BLUE,
    SIZE,
    WHITE,
    YELLOW,
    fit_text,
    load_font,
    render_cta,
    render_intro,
    render_paragraph,
    render_section,
    wrap_text,
)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


@pytest.fixture
def draw():
    from PIL import Image

    return ImageDraw.Draw(Image.new("RGB", (SIZE, SIZE)))


def test_wrap_text_keeps_all_words(draw):
    text = "one two three four five six seven eight nine ten"
    font = load_font(48)
    lines = wrap_text(draw, text, font, max_width=200)
    assert " ".join(lines).split() == text.split()


def test_wrap_text_respects_width(draw):
    text = "one two three four five six seven eight nine ten"
    font = load_font(48)
    max_width = 200
    lines = wrap_text(draw, text, font, max_width)
    assert len(lines) > 1
    assert all(draw.textlength(line, font=font) <= max_width for line in lines)


def test_fit_text_picks_largest_that_fits(draw):
    box = (SIZE - 200, SIZE - 200)
    short_font, _ = fit_text(draw, "Short", *box)
    long_font, _ = fit_text(draw, "word " * 80, *box)
    assert long_font.size < short_font.size


def test_fit_text_result_fits_the_box(draw):
    box = (600, 600)
    font, lines = fit_text(draw, "word " * 40, *box)
    widest = max(draw.textlength(line, font=font) for line in lines)
    assert widest <= box[0]


@pytest.mark.parametrize(
    "image, color",
    [
        (render_intro("Git a GitHub: Řešení problémů"), YELLOW),
        (render_paragraph("Nějaký odstavec textu."), WHITE),
        (render_cta(), YELLOW),
    ],
)
def test_background_color(image, color):
    assert image.size == (SIZE, SIZE)
    assert image.getpixel((5, 5)) == hex_to_rgb(color)


def test_cta_has_blue_button_in_the_centre():
    image = render_cta()
    assert image.getpixel((SIZE // 2, SIZE // 2)) == hex_to_rgb(BLUE)


def test_render_section_counts_intro_paragraphs_and_cta():
    section = Section(title="T", heading="H", paragraphs=["a", "b", "c"])
    images = render_section(section)
    assert len(images) == 1 + 3 + 1
    assert images[0].getpixel((5, 5)) == hex_to_rgb(YELLOW)
    assert images[1].getpixel((5, 5)) == hex_to_rgb(WHITE)
    assert images[-1].getpixel((5, 5)) == hex_to_rgb(YELLOW)
