from pathlib import Path

import pytest
from click.testing import CliRunner

from jg.crowing import cli
from tests.conftest import load_fixture


@pytest.fixture
def fake_fetch(monkeypatch):
    html = load_fixture("handbook-git.html")

    async def _fetch(url, **kwargs):
        return html

    monkeypatch.setattr(cli, "fetch_html", _fetch)
    return html


def test_cli_creates_nested_image_files(fake_fetch):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli.main,
            ["https://junior.guru/handbook/git/#reseni-problemu-s-gitem"],
        )
        assert result.exit_code == 0, result.output
        out = Path("handbook-git") / "reseni-problemu-s-gitem"
        files = sorted(p.name for p in out.glob("*.png"))
        assert files == ["01.png", "02.png", "03.png", "04.png"]


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
