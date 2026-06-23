"""Imperative shell: the ``crowing`` command line interface."""

import asyncio
from pathlib import Path

import click

from jg.crowing.errors import InvalidInputError
from jg.crowing.fetching import fetch_html
from jg.crowing.parsing import parse_section
from jg.crowing.rendering import render_section
from jg.crowing.urls import parse_url
from jg.crowing.writing import write_carousel, write_images


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
    click.echo(f"Created images and carousel.pdf in {output}")


async def _run(url: str, output_dir: Path) -> Path:
    handbook_url = parse_url(url)
    html = await fetch_html(url)
    section = parse_section(html, handbook_url.anchor)
    images = render_section(section)
    created = write_images(images, output_dir, handbook_url)
    write_carousel(images, created)
    return created
