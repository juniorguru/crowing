"""Prepare the plain social post independently of slide formatting."""

import re

from bs4 import BeautifulSoup

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import EventPage, Post, Section, Story
from jg.crowing.parsing import _plain_text


# Emojis say what the point means, not what its icon looks like (no 🐷 for "free").
# An icon missing here fails loudly, so a new one gets a deliberately chosen emoji.
ICON_EMOJI = {
    "bi-info-circle-fill": "📅",  # when, where and how long
    "bi-star-fill": "🙋‍♀️",  # members watch live and ask questions
    "bi-piggy-bank-fill": "🤗",  # free to join, 14-day trial
    "bi-play-circle-fill": "👉",  # where to go on Discord
    "bi-heart-fill": "😵‍💫",  # for beginners, no unexplained jargon
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
    icons = [
        name
        for icon in item.select(".bi")
        for name in icon.get("class", [])
        if name.startswith("bi-")
    ]
    if len(icons) != 1 or icons[0] not in ICON_EMOJI:
        raise InvalidInputError(
            f"No emoji for note explainer icon {icons or '(none)'}, "
            f"add it to ICON_EMOJI in jg.crowing.posts: {_plain_text(item)!r}"
        )
    return f"{ICON_EMOJI[icons[0]]} {_plain_text(item)}"
