"""Pure functions for turning handbook HTML into a :class:`Section`."""

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import RichText, Run, Section


HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
BOLD_TAGS = {"b", "strong"}
ITALIC_TAGS = {"i", "em"}
CODE_TAGS = {"code", "tt", "kbd", "samp"}

StyledChar = tuple[str, bool, bool, bool]


def parse_section(html: str, anchor: str) -> Section:
    """Extract the title, heading and styled paragraphs of the section at ``anchor``."""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a.headerlink"):
        link.decompose()
    if not isinstance(h1 := soup.find("h1"), Tag):
        raise InvalidInputError("Page contains no H1")
    if (toc := soup.select_one(".document-toc")) is None:
        raise InvalidInputError("Page contains no table of contents")
    heading = soup.find(id=anchor)
    if not isinstance(heading, Tag) or heading.name not in HEADINGS:
        raise InvalidInputError(f"Anchor #{anchor} not found")
    return Section(
        title=_plain_text(h1),
        heading=_plain_text(heading),
        paragraphs=list(_iter_paragraphs(heading)),
        topics=[_plain_text(link) for link in toc.select("a")],
    )


def _iter_paragraphs(heading: Tag):
    level = int(heading.name[1])
    for sibling in heading.find_next_siblings():
        if sibling.name in HEADINGS and int(sibling.name[1]) <= level:
            break
        yield from _paragraphs_from(sibling)


def _paragraphs_from(element: Tag):
    """Yield the paragraphs of a block: a ``<p>``, each ``<li>``, or a note's contents."""
    if element.name == "p" and "admonition-title" not in (element.get("class") or []):
        runs = _runs(element)
        if runs:
            following = element.find_next_sibling()
            if following is not None and following.name in ("ul", "ol"):
                runs = _colon_to_ellipsis(runs)  # a colon reads badly before a list
            yield runs
    elif element.name in ("ul", "ol"):
        for item in element.find_all("li", recursive=False):
            runs = _runs(item)
            if runs:
                yield runs
    elif element.name == "div" and _is_note(element):
        for child in element.children:
            if isinstance(child, Tag):
                yield from _paragraphs_from(child)


def _is_note(element: Tag) -> bool:
    classes = element.get("class") or []
    return "note" in classes or "admonition" in classes


def _colon_to_ellipsis(runs: RichText) -> RichText:
    *rest, last = runs
    if last.text.endswith(":"):
        last = Run(f"{last.text[:-1]}…", last.bold, last.italic)
    return [*rest, last]


def _runs(element: Tag) -> RichText:
    chars: list[StyledChar] = []
    _collect(element, bold=False, italic=False, code=False, in_link=False, out=chars)
    return _group(_collapse(chars))


def _collect(
    node: Tag,
    *,
    bold: bool,
    italic: bool,
    code: bool,
    in_link: bool,
    out: list[StyledChar],
) -> None:
    for child in node.children:
        if isinstance(child, NavigableString):
            out.extend((character, bold, italic, code) for character in str(child))
        elif isinstance(child, Tag):
            linked = in_link or child.name == "a"
            _collect(
                child,
                bold=not linked and (bold or child.name in BOLD_TAGS),
                italic=not linked and (italic or child.name in ITALIC_TAGS),
                code=code or child.name in CODE_TAGS,
                in_link=linked,
                out=out,
            )


def _collapse(chars: list[StyledChar]) -> list[StyledChar]:
    out: list[StyledChar] = []
    after_space = True
    for character, bold, italic, code in chars:
        if character.isspace():
            if not after_space:
                out.append((" ", bold, italic, code))
            after_space = True
        else:
            out.append((character, bold, italic, code))
            after_space = False
    while out and out[-1][0] == " ":
        out.pop()
    return out


def _group(chars: list[StyledChar]) -> RichText:
    runs: list[list] = []
    for character, bold, italic, code in chars:
        if runs and runs[-1][1:] == [bold, italic, code]:
            runs[-1][0] += character
        else:
            runs.append([character, bold, italic, code])
    return [Run(text, bold, italic, code) for text, bold, italic, code in runs]


def _plain_text(element: Tag | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", element.get_text()).strip()
