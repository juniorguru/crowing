"""Imperative shell: the ``crowing`` command line interface."""

import asyncio
from io import BytesIO
from pathlib import Path

import click
from PIL import Image

from jg.crowing.errors import InvalidInputError
from jg.crowing.fetching import fetch_bytes, fetch_html
from jg.crowing.parsing import parse_event, parse_section, parse_story
from jg.crowing.rendering import (
    EVENT_CTA,
    REEL_WARN_SECONDS,
    circle_image,
    compose_square,
    event_reel_durations,
    fit_reel_durations,
    reel_durations,
    reel_total_seconds,
    render_cta,
    render_event_reel,
    render_intro,
    render_reel,
    render_section,
    render_story,
    render_story_reel,
    story_reel_durations,
)
from jg.crowing.screenshots import (
    capture_event,
    capture_story_blockquotes,
    capture_story_preview,
)
from jg.crowing.urls import EventUrl, HandbookUrl, StoryUrl, parse_url
from jg.crowing.writing import write_carousel, write_images, write_reel


EVENT_INTRO_LABEL = "Online akce"  # prefix before the date on an event's intro slide


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
    """Create Instagram-ready images from a junior.guru handbook, event or story URL."""
    try:
        output = asyncio.run(_run(url, output_dir))
    except InvalidInputError as error:
        raise click.BadParameter(str(error), param_hint="URL") from error
    click.echo(f"Created all assets in {output}")


async def _run(url: str, output_dir: Path) -> Path:
    parsed = parse_url(url)
    if isinstance(parsed, EventUrl):
        return await _run_event(parsed, url, output_dir)
    if isinstance(parsed, StoryUrl):
        return await _run_story(parsed, url, output_dir)
    return await _run_handbook(parsed, url, output_dir)


def _finalize_reel(durations: list[float]) -> list[float]:
    """Shorten the CTA if the reel is too long (raising if hopeless), and warn if long."""
    durations = fit_reel_durations(durations)
    total = reel_total_seconds(durations)
    if total >= REEL_WARN_SECONDS:
        click.echo(f"Warning: the reel is {round(total)}s long, getting long", err=True)
    return durations


async def _run_handbook(handbook_url: HandbookUrl, url: str, output_dir: Path) -> Path:
    html = await fetch_html(url)
    section = parse_section(html, handbook_url.anchor)
    durations = _finalize_reel(reel_durations(section))
    images = render_section(section)
    created = write_images(images, output_dir, handbook_url)
    write_carousel(images, created)
    write_reel(render_reel(section, intro=images[0]), created, durations)
    return created


async def _run_story(story_url: StoryUrl, url: str, output_dir: Path) -> Path:
    story = parse_story(await fetch_html(url), url)
    avatar = Image.open(BytesIO(await fetch_bytes(story.image_url)))
    corner = circle_image(avatar)
    preview = await capture_story_preview(url)
    blockquotes = await capture_story_blockquotes(url)
    durations = _finalize_reel(story_reel_durations(story, blockquotes))
    images = render_story(story, corner, preview, blockquotes)
    created = write_images(images, output_dir, story_url)
    write_carousel(images, created)
    write_reel(
        render_story_reel(
            story, intro=images[0], preview=preview, blockquotes=blockquotes
        ),
        created,
        durations,
    )
    return created


async def _run_event(event_url: EventUrl, url: str, output_dir: Path) -> Path:
    page = parse_event(await fetch_html(url), url)
    corner = None
    if page.avatar_url:
        avatar = Image.open(BytesIO(await fetch_bytes(page.avatar_url)))
        corner = circle_image(avatar)
    intro = render_intro(
        f"{EVENT_INTRO_LABEL}, {page.event_date}", page.event_name, corner_image=corner
    )
    shots = await capture_event(url)
    squares = [
        compose_square(shot.image, background=shot.background, sign=shot.sign)
        for shot in shots
    ]
    images = [intro, *squares, render_cta(content=EVENT_CTA)]
    created = write_images(images, output_dir, event_url)
    write_carousel(images, created)
    durations = _finalize_reel(event_reel_durations(shots))
    write_reel(render_event_reel([intro, *squares], EVENT_CTA), created, durations)
    return created
