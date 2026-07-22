"""Pure functions for turning handbook HTML into a :class:`Section`."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import EventPage, RichText, Run, Section, Story


AVATAR_LINK_TEXT = "Stáhni fotku"  # download link junior.guru puts next to real photos
# e.g. "30.6.2026, 18:00" → day, month, optional time (the year is dropped)
DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*\d{4}(?:[,\s]+(\d{1,2}:\d{2}))?")

STORY_LEAD_SELECTOR = ".lead"  # the interview's introductory paragraph
STORY_IMAGE_SELECTOR = "img.article-image"  # the photo shown, circled, in the intro
STORY_SENTENCES_PER_SLIDE = 2  # each lead slide carries two sentences
# a sentence ends at ., ! ? or … (with any trailing closing quote/bracket) and a space
SENTENCE_END_RE = re.compile(r"[.!?…]+[\"”»)\]]*\s+")


def parse_story(html: str, base_url: str) -> Story:
    """Extract an interview's title, lead sentences and the ``.article-image`` URL.

    The H1 holds the interview title, ``.lead`` the introductory paragraph (split into
    one sentence per slide), and ``.article-image`` the photo shown in the intro corner;
    ``base_url`` resolves the image's relative link. Missing pieces are invalid input.
    """
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a.headerlink"):
        link.decompose()
    if not isinstance(h1 := soup.find("h1"), Tag):
        raise InvalidInputError("Story page contains no H1")
    if (lead := soup.select_one(STORY_LEAD_SELECTOR)) is None:
        raise InvalidInputError("Story page contains no lead")
    if not (sentences := _split_sentences(_runs(lead))):
        raise InvalidInputError("Story page has an empty lead")
    return Story(
        title=_plain_text(h1),
        paragraphs=_chunk_sentences(sentences, STORY_SENTENCES_PER_SLIDE),
        image_url=_find_article_image(soup, base_url),
    )


def _chunk_sentences(sentences: list[RichText], per_slide: int) -> list[RichText]:
    """Join every ``per_slide`` sentences into one slide's :class:`RichText`."""
    return [
        [
            run
            for index, sentence in enumerate(group)
            for run in ([Run(" "), *sentence] if index else sentence)
        ]
        for start in range(0, len(sentences), per_slide)
        if (group := sentences[start : start + per_slide])
    ]


def _find_article_image(soup: BeautifulSoup, base_url: str) -> str:
    image = soup.select_one(STORY_IMAGE_SELECTOR)
    if not isinstance(image, Tag) or not (src := image.get("src")):
        raise InvalidInputError("Story page has no .article-image")
    return urljoin(base_url, str(src))


def _split_sentences(runs: RichText) -> list[RichText]:
    """Split styled ``runs`` into one :class:`RichText` per sentence, keeping styling."""
    flat: list[StyledChar] = [
        (character, run.bold, run.italic, run.code)
        for run in runs
        for character in run.text
    ]
    text = "".join(character for character, *_ in flat)
    sentences: list[RichText] = []
    start = 0
    for match in SENTENCE_END_RE.finditer(text):
        sentences.append(_group(flat[start : match.end()]))
        start = match.end()
    if start < len(flat):
        sentences.append(_group(flat[start:]))
    return [stripped for sentence in sentences if (stripped := _strip_runs(sentence))]


def _strip_runs(runs: RichText) -> RichText:
    """Drop leading and trailing whitespace (a sentence's trailing gap) from ``runs``."""
    if not runs:
        return runs
    head, *_ = runs
    runs = [Run(head.text.lstrip(), head.bold, head.italic, head.code), *runs[1:]]
    *_, tail = runs
    runs = [*runs[:-1], Run(tail.text.rstrip(), tail.bold, tail.italic, tail.code)]
    return [run for run in runs if run.text]


def parse_event(html: str, base_url: str) -> EventPage:
    """Extract the event name and date, the speaker name, and the avatar URL, if any.

    The H1 reads ``speaker(s): event`` — the speaker is everything before the first
    colon, the event the rest. ``.article-details`` holds the date and the optional
    "Stáhni fotku" avatar link; ``base_url`` resolves the avatar's relative link.
    """
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a.headerlink"):
        link.decompose()
    if not isinstance(h1 := soup.find("h1"), Tag):
        raise InvalidInputError("Page contains no H1")
    speaker, colon, event = _plain_text(h1).partition(":")
    details = soup.select_one(".article-details")
    return EventPage(
        event_name=event.strip() if colon else "",
        speaker_name=speaker.strip(),
        event_date=_find_event_date(details),
        avatar_url=_find_avatar(details, base_url),
    )


def _find_event_date(details: Tag | None) -> str:
    """Day-month and time, no year, e.g. ``30.6. 18:00`` from ``.article-details``."""
    if details is None or not (match := DATE_RE.search(_plain_text(details))):
        return ""
    date = f"{match.group(1)}.{match.group(2)}."
    return f"{date} {match.group(3)}" if match.group(3) else date


def _find_avatar(details: Tag | None, base_url: str) -> str | None:
    if details is None:
        return None
    for link in details.select("a.article-details-link[href]"):
        if _plain_text(link) == AVATAR_LINK_TEXT:
            return urljoin(base_url, str(link["href"]))
    return None


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
