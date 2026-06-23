"""Plain data structures shared across the functional core."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    """A handbook section ready to be turned into a carousel of images."""

    title: str
    heading: str
    paragraphs: list[str]

    @property
    def intro(self) -> str:
        """The intro slide text, e.g. ``Git a GitHub: Řešení problémů s Gitem``."""
        return f"{self.title}: {self.heading}"
