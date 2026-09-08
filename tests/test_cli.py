import tomllib
from io import BytesIO
from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from jg.crowing import cli
from jg.crowing.errors import InvalidInputError
from jg.crowing.models import Shot
from tests.conftest import load_fixture


@pytest.fixture
def fake_fetch(monkeypatch):
    html = load_fixture("handbook-git.html")

    async def _fetch(url, **kwargs):
        return html

    # Skip the (slow) ffmpeg reel encode: drop a placeholder so the CLI still produces
    # a reel.mp4, while the real encoding stays covered by test_writing and the smoke.
    def _fake_write_reel(frames, output_dir, durations, **kwargs):
        path = output_dir / "reel.mp4"
        path.write_bytes(b"")
        return path

    monkeypatch.setattr(cli, "fetch_html", _fetch)
    monkeypatch.setattr(cli, "render_reel", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "write_reel", _fake_write_reel)
    return html


def _png_bytes(color) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (100, 100), color).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def fake_event(monkeypatch):
    """Fake an event without an avatar: fetch the fixture HTML, fake the screenshots."""
    html = load_fixture("event-no-avatar.html")
    shots = [
        Shot(
            Image.new("RGB", (800, 400), "#1755d1"), reading_seconds=4.0
        ),  # media card
        Shot(Image.new("RGB", (700, 300), "#1755d1"), reading_seconds=2.0),  # lead
        Shot(Image.new("RGB", (300, 500), "#1755d1"), reading_seconds=1.0),  # note item
    ]

    async def _fetch(url, **kwargs):
        return html

    async def _capture(url, **kwargs):
        if "/events/999/" in url:  # a page with none of the expected elements
            raise InvalidInputError("Event page has none of the expected elements")
        return shots

    # Skip the (slow) ffmpeg reel encode, as the handbook fixture does.
    def _fake_write_reel(frames, output_dir, durations, **kwargs):
        (output_dir / "reel.mp4").write_bytes(b"")
        return output_dir / "reel.mp4"

    monkeypatch.setattr(cli, "fetch_html", _fetch)
    monkeypatch.setattr(cli, "capture_event", _capture)
    monkeypatch.setattr(cli, "render_event_reel", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "write_reel", _fake_write_reel)
    return shots


@pytest.fixture
def fake_story(monkeypatch):
    """Fake a story: fetch the fixture HTML and a stand-in avatar, skip the reel encode."""
    html = load_fixture("story.html")

    async def _fetch(url, **kwargs):
        return html

    async def _fetch_bytes(url, **kwargs):
        return _png_bytes((255, 0, 255))  # a magenta stand-in for the .article-image

    async def _capture_preview(url, **kwargs):
        return Image.new("RGB", (800, 1422), "#00ff00")  # a 9:16 green stand-in shot

    async def _capture_blockquotes(url, **kwargs):
        return []  # the simon-koreny fixture has no blockquotes

    def _fake_write_reel(frames, output_dir, durations, **kwargs):
        (output_dir / "reel.mp4").write_bytes(b"")
        return output_dir / "reel.mp4"

    monkeypatch.setattr(cli, "fetch_html", _fetch)
    monkeypatch.setattr(cli, "fetch_bytes", _fetch_bytes)
    monkeypatch.setattr(cli, "capture_story_preview", _capture_preview)
    monkeypatch.setattr(cli, "capture_story_blockquotes", _capture_blockquotes)
    monkeypatch.setattr(cli, "render_story_reel", lambda *args, **kwargs: [])
    monkeypatch.setattr(cli, "write_reel", _fake_write_reel)
    return html


def test_cli_creates_story_images_intro_paragraphs_preview_and_cta(fake_story):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, ["https://junior.guru/stories/simon-koreny/"])
        assert result.exit_code == 0, result.output
        out = Path("stories") / "simon-koreny"
        post = tomllib.loads((out / "post.toml").read_text())
        assert post["title"].startswith("Příběh: ")
        assert post["tags"] == []
        files = sorted(p.name for p in out.glob("*.png"))
        # 01 intro, one per lead slide (4 sentences -> 2 slides), preview, then the cta
        assert files == ["01.png", "02.png", "03.png", "04.png", "05.png"]


def test_cli_inserts_blockquote_slides_before_the_preview(fake_story, monkeypatch):
    async def _capture_blockquotes(url, **kwargs):
        return [Shot(Image.new("RGB", (500, 300), "#ff8800"), reading_seconds=2.0)]

    monkeypatch.setattr(cli, "capture_story_blockquotes", _capture_blockquotes)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, ["https://junior.guru/stories/simon-koreny/"])
        assert result.exit_code == 0, result.output
        out = Path("stories") / "simon-koreny"
        files = sorted(p.name for p in out.glob("*.png"))
        # intro + 2 lead + 1 blockquote + preview + cta
        assert files == ["01.png", "02.png", "03.png", "04.png", "05.png", "06.png"]


def test_cli_story_intro_is_the_yellow_rendered_slide(fake_story):
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli.main, ["https://junior.guru/stories/simon-koreny/"])
        with Image.open(Path("stories") / "simon-koreny" / "01.png") as image:
            assert image.getpixel((5, 5)) == (255, 250, 114)  # #fffa72 intro background


def test_cli_story_puts_the_article_image_in_the_intro(fake_story):
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli.main, ["https://junior.guru/stories/simon-koreny/"])
        with Image.open(Path("stories") / "simon-koreny" / "01.png") as intro:
            pixels = intro.convert("RGB").load()
            region = [(x, y) for x in range(540, 1080) for y in range(540, 1080)]
            assert any(pixels[x, y] == (255, 0, 255) for x, y in region)


def test_cli_creates_story_reel_and_carousel(fake_story):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, ["https://junior.guru/stories/simon-koreny/"])
        assert result.exit_code == 0, result.output
        assert (Path("stories") / "simon-koreny" / "reel.mp4").exists()
        assert (Path("stories") / "simon-koreny" / "carousel.pdf").exists()


def test_cli_rejects_story_without_article_image(fake_story, monkeypatch):
    async def _fetch(url, **kwargs):
        return load_fixture("story-no-image.html")

    monkeypatch.setattr(cli, "fetch_html", _fetch)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["https://junior.guru/stories/simon-koreny/"])
    assert result.exit_code != 0


def test_cli_creates_nested_image_files(fake_fetch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli.main,
            ["https://junior.guru/handbook/git/#reseni-problemu-s-gitem"],
        )
        assert result.exit_code == 0, result.output
        out = Path("handbook-git") / "reseni-problemu-s-gitem"
        post = tomllib.loads((out / "post.toml").read_text())
        assert post["title"] == "Příručka: Řešení problémů s Gitem"
        assert "\n\n" in post["text"]
        files = sorted(p.name for p in out.glob("*.png"))
        assert files == ["01.png", "02.png", "03.png", "04.png"]


def test_cli_creates_a_reel_next_to_images(fake_fetch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli.main,
            ["https://junior.guru/handbook/git/#reseni-problemu-s-gitem"],
        )
        assert result.exit_code == 0, result.output
        assert (Path("handbook-git") / "reseni-problemu-s-gitem" / "reel.mp4").exists()


def test_cli_creates_carousel_pdf_next_to_images(fake_fetch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli.main,
            ["https://junior.guru/handbook/git/#reseni-problemu-s-gitem"],
        )
        assert result.exit_code == 0, result.output
        assert (
            Path("handbook-git") / "reseni-problemu-s-gitem" / "carousel.pdf"
        ).exists()


def test_cli_respects_output_dir(fake_fetch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli.main,
            [
                "https://junior.guru/handbook/git/#reseni-problemu-s-gitem",
                "--output-dir",
                "assets",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (
            Path("assets") / "handbook-git" / "reseni-problemu-s-gitem" / "01.png"
        ).exists()


def test_cli_rejects_missing_anchor(fake_fetch):
    runner = CliRunner()
    result = runner.invoke(cli.main, ["https://junior.guru/handbook/git/"])
    assert result.exit_code != 0


def test_cli_rejects_non_handbook_page(fake_fetch):
    runner = CliRunner()
    result = runner.invoke(cli.main, ["https://junior.guru/club/#x"])
    assert result.exit_code != 0


def test_cli_creates_event_images_with_an_intro_first(fake_event):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, ["https://junior.guru/events/63/"])
        assert result.exit_code == 0, result.output
        post = tomllib.loads((Path("events") / "63" / "post.toml").read_text())
        assert post["title"].startswith("Klubová akce: ")
        assert post["tags"] == []
        files = sorted(p.name for p in (Path("events") / "63").glob("*.png"))
        # 01 intro, one image per screenshot (3), then the call to action last
        assert files == ["01.png", "02.png", "03.png", "04.png", "05.png"]


def test_cli_event_intro_is_the_yellow_rendered_slide(fake_event):
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli.main, ["https://junior.guru/events/63/"])
        with Image.open(Path("events") / "63" / "01.png") as image:
            assert image.getpixel((5, 5)) == (255, 250, 114)  # #fffa72 intro background


def test_cli_event_last_image_is_the_yellow_call_to_action(fake_event):
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli.main, ["https://junior.guru/events/63/"])
        with Image.open(Path("events") / "63" / "05.png") as image:
            assert image.getpixel((5, 5)) == (255, 250, 114)  # #fffa72 CTA background


def test_cli_creates_an_event_reel_next_to_images(fake_event):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, ["https://junior.guru/events/63/"])
        assert result.exit_code == 0, result.output
        assert (Path("events") / "63" / "reel.mp4").exists()


def test_cli_creates_event_carousel_pdf(fake_event):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, ["https://junior.guru/events/63/"])
        assert result.exit_code == 0, result.output
        assert (Path("events") / "63" / "carousel.pdf").exists()


def test_cli_event_images_are_square(fake_event):
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli.main, ["https://junior.guru/events/63/"])
        with Image.open(Path("events") / "63" / "02.png") as image:
            assert image.size == (1080, 1080)


def test_cli_rejects_event_page_without_expected_elements(fake_event):
    runner = CliRunner()
    result = runner.invoke(cli.main, ["https://junior.guru/events/999/"])
    assert result.exit_code != 0


def test_cli_event_puts_the_speaker_avatar_in_the_intro(fake_event, monkeypatch):
    html = load_fixture("event.html")  # this fixture has a "Stáhni fotku" link

    async def _fetch(url, **kwargs):
        return html

    async def _fetch_bytes(url, **kwargs):
        return _png_bytes((255, 0, 255))  # a magenta stand-in for the avatar

    monkeypatch.setattr(cli, "fetch_html", _fetch)
    monkeypatch.setattr(cli, "fetch_bytes", _fetch_bytes)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli.main, ["https://junior.guru/events/63/"])
        assert result.exit_code == 0, result.output
        with Image.open(Path("events") / "63" / "01.png") as intro:
            pixels = intro.convert("RGB").load()
            region = [
                (x, y) for x in range(540, 1080) for y in range(540, 1080)
            ]  # bottom-right, where the avatar sits
            assert any(pixels[x, y] == (255, 0, 255) for x, y in region)
