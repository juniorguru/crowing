import pytest
from PIL import Image
from pypdf import PdfReader

from jg.crowing.rendering import SIZE
from jg.crowing.writing import write_carousel


@pytest.fixture
def images() -> list[Image.Image]:
    colors = ["#fffa72", "#ffffff", "#fffa72"]
    return [Image.new("RGB", (SIZE, SIZE), color) for color in colors]


def test_write_carousel_is_named_carousel_pdf(images, tmp_path):
    assert write_carousel(images, tmp_path) == tmp_path / "carousel.pdf"


def test_write_carousel_has_one_page_per_image(images, tmp_path):
    path = write_carousel(images, tmp_path)
    assert len(PdfReader(path).pages) == len(images)


def test_write_carousel_pages_are_square(images, tmp_path):
    path = write_carousel(images, tmp_path)
    page = PdfReader(path).pages[0]
    assert round(page.mediabox.width) == round(page.mediabox.height) == SIZE
