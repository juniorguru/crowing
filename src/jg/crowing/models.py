"""Plain data structures shared across the functional core."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Run:
    """A stretch of paragraph text with uniform inline styling."""

    text: str
    bold: bool = False
    italic: bool = False


RichText = list[Run]


@dataclass(frozen=True)
class Section:
    """A handbook section ready to be turned into a carousel of images."""

    title: str
    heading: str
    paragraphs: list[RichText]
