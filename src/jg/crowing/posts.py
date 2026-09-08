"""Prepare the plain social post independently of slide formatting."""

import re

from bs4 import BeautifulSoup

from jg.crowing.models import EventPage, Post, Section, Story
from jg.crowing.parsing import _plain_text


ICON_EMOJI = {
    "bi-info-circle-fill": "ℹ️",
    "bi-star-fill": "⭐",
    "bi-piggy-bank-fill": "🐷",
    "bi-play-circle-fill": "▶️",
    "bi-heart-fill": "❤️",
}


def prepare_post(html: str, page: Section | Story | EventPage) -> Post:
    """Extract the documented title and body for each supported page type."""
    if isinstance(page, Section):
        return Post(
            title=f"Příručka: {page.heading}",
            text="\n\n".join(
                "".join(run.text for run in paragraph) for paragraph in page.paragraphs
            ),
        )
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select(".headerlink, .icon-links"):
        link.decompose()
    if isinstance(page, Story):
        title = re.split(r",\s*říká\b", page.title, maxsplit=1)[0]
        return Post(f"Příběh: {title}", _plain_text(soup.select_one(".lead")))
    return _event_post(soup, page)


def _event_post(soup: BeautifulSoup, page: EventPage) -> Post:
    speaker = _plain_text(soup.select_one(".media-card-heading"))
    title = _plain_text(soup.find("h1"))
    if speaker and title.startswith(f"{speaker}:"):
        title = title[len(speaker) + 1 :].strip()
    else:
        title = page.event_name or title
    bio = soup.select_one(".media-card-richtext")
    bio_paragraphs = bio.find_all("p") if bio else []
    parts = [
        _plain_text(soup.select_one(".lead")),
        "\n".join(
            _explainer_item(item) for item in soup.select(".note-explainer > li")
        ),
        "\n".join(
            filter(None, [speaker, _plain_text(soup.select_one(".media-card-meta"))])
        ),
        "\n\n".join(_plain_text(p) for p in bio_paragraphs)
        if bio_paragraphs
        else _plain_text(bio),
    ]
    return Post(f"Klubová akce: {title}", "\n\n".join(filter(None, parts)))


def _explainer_item(item) -> str:
    classes = {name for icon in item.select(".bi") for name in icon.get("class", [])}
    emoji = next((emoji for name, emoji in ICON_EMOJI.items() if name in classes), "•")
    return f"{emoji} {_plain_text(item)}"
