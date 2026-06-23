"""Pure functions for turning handbook HTML into a :class:`Section`."""

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import RichText, Run, Section


HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
BOLD_TAGS = {"b", "strong"}
ITALIC_TAGS = {"i", "em"}

StyledChar = tuple[str, bool, bool]


def parse_section(html: str, anchor: str) -> Section:
    """Extract the title, heading and styled paragraphs of the section at ``anchor``."""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a.headerlink"):
        link.decompose()
    heading = soup.find(id=anchor)
    if not isinstance(heading, Tag) or heading.name not in HEADINGS:
        raise InvalidInputError(f"Anchor #{anchor} not found")
    return Section(
        title=_plain_text(soup.find("h1")),
        heading=_plain_text(heading),
        paragraphs=list(_iter_paragraphs(heading)),
        topics=_topics(soup),
    )


def _topics(soup: BeautifulSoup) -> list[str]:
    toc = soup.select_one(".document-toc")
    if toc is None:
        return []
    return [_plain_text(link) for link in toc.select("a")]


def _iter_paragraphs(heading: Tag):
    level = int(heading.name[1])
    for sibling in heading.find_next_siblings():
        if sibling.name in HEADINGS and int(sibling.name[1]) <= level:
            break
        if sibling.name == "p":
            runs = _runs(sibling)
            if runs:
                yield runs


def _runs(element: Tag) -> RichText:
    chars: list[StyledChar] = []
    _collect(element, bold=False, italic=False, in_link=False, out=chars)
    return _group(_collapse(chars))


def _collect(
    node: Tag, *, bold: bool, italic: bool, in_link: bool, out: list[StyledChar]
) -> None:
    for child in node.children:
        if isinstance(child, NavigableString):
            out.extend((character, bold, italic) for character in str(child))
        elif isinstance(child, Tag):
            linked = in_link or child.name == "a"
            _collect(
                child,
                bold=not linked and (bold or child.name in BOLD_TAGS),
                italic=not linked and (italic or child.name in ITALIC_TAGS),
                in_link=linked,
                out=out,
            )


def _collapse(chars: list[StyledChar]) -> list[StyledChar]:
    out: list[StyledChar] = []
    after_space = True
    for character, bold, italic in chars:
        if character.isspace():
            if not after_space:
                out.append((" ", bold, italic))
            after_space = True
        else:
            out.append((character, bold, italic))
            after_space = False
    while out and out[-1][0] == " ":
        out.pop()
    return out


def _group(chars: list[StyledChar]) -> RichText:
    runs: list[list] = []
    for character, bold, italic in chars:
        if runs and runs[-1][1] == bold and runs[-1][2] == italic:
            runs[-1][0] += character
        else:
            runs.append([character, bold, italic])
    return [Run(text, bold, italic) for text, bold, italic in runs]


def _plain_text(element: Tag | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", element.get_text()).strip()
