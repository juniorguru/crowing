import subprocess

import imageio.v2 as imageio
import imageio_ffmpeg
import pytest
from PIL import Image
from pypdf import PdfReader

from jg.crowing.errors import InvalidInputError
from jg.crowing.rendering import REEL_HEIGHT, REEL_WIDTH, SIZE
from jg.crowing.writing import write_carousel, write_reel


@pytest.fixture
def images() -> list[Image.Image]:
    colors = ["#fffa72", "#ffffff", "#fffa72"]
    return [Image.new("RGB", (SIZE, SIZE), color) for color in colors]


@pytest.fixture
def frames() -> list[Image.Image]:
    colors = ["#fffa72", "#ffffff", "#fffa72"]
    return [Image.new("RGB", (REEL_WIDTH, REEL_HEIGHT), color) for color in colors]


def test_write_carousel_is_named_carousel_pdf(images, tmp_path):
    assert write_carousel(images, tmp_path) == tmp_path / "carousel.pdf"


def test_write_carousel_has_one_page_per_image(images, tmp_path):
    path = write_carousel(images, tmp_path)
    assert len(PdfReader(path).pages) == len(images)


def test_write_carousel_pages_are_square(images, tmp_path):
    path = write_carousel(images, tmp_path)
    page = PdfReader(path).pages[0]
    assert round(page.mediabox.width) == round(page.mediabox.height) == SIZE


def test_write_reel_is_named_reel_mp4(frames, tmp_path):
    assert write_reel(frames, tmp_path, [3, 4, 4], fps=5) == tmp_path / "reel.mp4"


def test_write_reel_lasts_the_sum_of_its_durations(frames, tmp_path):
    path = write_reel(frames, tmp_path, [3, 4, 4], fps=5)
    reader = imageio.get_reader(path)
    duration = reader.count_frames() / reader.get_meta_data()["fps"]
    assert duration == pytest.approx(3 + 4 + 4, abs=1)


def test_write_reel_rejects_a_too_long_video(frames, tmp_path):
    with pytest.raises(InvalidInputError):
        write_reel(frames, tmp_path, [10, 40, 45], fps=5)  # 95s, over the 90s limit


def test_write_reel_frames_are_9_by_16(frames, tmp_path):
    path = write_reel(frames, tmp_path, [3, 4, 4], fps=5)
    first = imageio.get_reader(path).get_data(0)
    assert (first.shape[1], first.shape[0]) == (REEL_WIDTH, REEL_HEIGHT)


def test_write_reel_carries_a_music_track(frames, tmp_path):
    path = write_reel(frames, tmp_path, [3, 4, 4], fps=5)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    streams = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    assert "Audio: aac" in streams.stderr
