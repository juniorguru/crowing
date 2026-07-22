"""Plain data structures shared across the functional core."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from PIL.Image import Image


@dataclass(frozen=True)
class Run:
    """A stretch of paragraph text with uniform inline styling."""

    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False


RichText = list[Run]


@dataclass(frozen=True)
class Section:
    """A handbook section ready to be turned into a carousel of images."""

    title: str
    heading: str
    paragraphs: list[RichText]
    topics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EventPage:
    """The rendered-intro data parsed from an event page's HTML.

    ``event_name`` and ``speaker_name`` come from the H1 (``speaker: event``),
    ``event_date`` is the day-and-month (no year) from ``.article-details``, and
    ``avatar_url`` is the speaker photo behind the "Stáhni fotku" link, if any.
    """

    event_name: str
    speaker_name: str
    event_date: str = ""
    avatar_url: str | None = None


@dataclass(frozen=True)
class Shot:
    """A screenshot of an event page element, with its reading time kept along.

    ``reading_seconds`` is how long the screenshotted text takes to read at 200 wpm;
    it isn't used by the MVP carousel yet, but travels with the image for later use.
    ``background`` is the colour its square should sit on (yellow for the lead).
    ``sign`` marks shots that get the JUNIOR.GURU signature (the lead and note
    explainer items, but not the featured media card).
    """

    image: "Image"
    reading_seconds: float = 0.0
    background: str = "#ffffff"
    sign: bool = False
