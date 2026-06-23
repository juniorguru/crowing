"""Imperative shell: the ``crowing`` command line interface."""

import asyncio
from pathlib import Path

import click

from jg.crowing.errors import InvalidInputError
from jg.crowing.fetching import fetch_html
from jg.crowing.parsing import parse_section
from jg.crowing.rendering import (
    REEL_MAX_SECONDS,
    reel_durations,
    render_reel,
    render_section,
)
from jg.crowing.urls import parse_url
from jg.crowing.writing import write_carousel, write_images, write_reel


@click.command()
@click.argument("url")
@click.option(
    "--output-dir",
    "-o",
    default=".",
    type=click.Path(file_okay=False, path_type=Path),
    help="Where to create the image subdirectories (defaults to the current directory).",
)
def main(url: str, output_dir: Path) -> None:
    """Create Instagram-ready images from a junior.guru handbook section URL."""
    try:
        output = asyncio.run(_run(url, output_dir))
    except InvalidInputError as error:
        raise click.BadParameter(str(error), param_hint="URL") from error
    click.echo(f"Created all assets in {output}")


async def _run(url: str, output_dir: Path) -> Path:
    handbook_url = parse_url(url)
    html = await fetch_html(url)
    section = parse_section(html, handbook_url.anchor)
    durations = reel_durations(section)
    total = sum(durations)
    if total >= REEL_MAX_SECONDS:
        raise InvalidInputError(
            f"The reel would be {round(total)}s long; keep it under {REEL_MAX_SECONDS}s "
            "by choosing a section with fewer or shorter paragraphs"
        )
    images = render_section(section)
    created = write_images(images, output_dir, handbook_url)
    write_carousel(images, created)
    write_reel(render_reel(section), created, durations)
    return created
