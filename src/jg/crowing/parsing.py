"""Pure functions for turning handbook HTML into a :class:`Section`."""

import re

from bs4 import BeautifulSoup, Tag

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import Section


HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")


def parse_section(html: str, anchor: str) -> Section:
    """Extract the title, heading and plain paragraphs of the section at ``anchor``."""
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(id=anchor)
    if not isinstance(heading, Tag) or heading.name not in HEADINGS:
        raise InvalidInputError(f"Anchor #{anchor} not found")
    return Section(
        title=_clean_text(soup.find("h1")),
        heading=_clean_text(heading),
        paragraphs=list(_iter_paragraphs(heading)),
    )


def _iter_paragraphs(heading: Tag):
    level = int(heading.name[1])
    for sibling in heading.find_next_siblings():
        if sibling.name in HEADINGS and int(sibling.name[1]) <= level:
            break
        if sibling.name == "p":
            text = _clean_text(sibling)
            if text:
                yield text


def _clean_text(element: Tag | None) -> str:
    if element is None:
        return ""
    for link in element.select("a.headerlink"):
        link.decompose()
    return re.sub(r"\s+", " ", element.get_text()).strip()
