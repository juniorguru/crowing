"""Pure functions for validating and parsing junior.guru URLs."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from jg.crowing.errors import InvalidInputError


@dataclass(frozen=True)
class HandbookUrl:
    """A validated junior.guru handbook URL pointing at a section anchor."""

    path: str
    anchor: str

    @property
    def dir_name(self) -> str:
        """Slug joining the path segments, e.g. ``/handbook/git/`` → ``handbook-git``."""
        return "-".join(segment for segment in self.path.split("/") if segment)

    @property
    def name(self) -> str:
        """Subdirectory name for the assets: the section anchor."""
        return self.anchor


@dataclass(frozen=True)
class EventUrl:
    """A validated junior.guru event URL, e.g. ``/events/63/``."""

    path: str
    number: str

    @property
    def dir_name(self) -> str:
        """All events share a single ``events`` directory."""
        return "events"

    @property
    def name(self) -> str:
        """Subdirectory name for the assets: the event number."""
        return self.number


@dataclass(frozen=True)
class StoryUrl:
    """A validated junior.guru story URL, e.g. ``/stories/simon-koreny/``."""

    path: str
    slug: str

    @property
    def dir_name(self) -> str:
        """All stories share a single ``stories`` directory."""
        return "stories"

    @property
    def name(self) -> str:
        """Subdirectory name for the assets: the story slug."""
        return self.slug


Url = HandbookUrl | EventUrl | StoryUrl


def parse_url(url: str) -> Url:
    """Validate ``url`` and split it into a handbook, event or story URL.

    Raises :class:`NotImplementedError` for non-junior.guru pages and for pages in a
    namespace without documented behavior, and :class:`InvalidInputError` when a
    handbook anchor, an event number or a story slug is missing.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host != "junior.guru" and not host.endswith(".junior.guru"):
        raise NotImplementedError(f"Not a junior.guru page: {url}")
    if parts.path.startswith("/handbook/"):
        return _parse_handbook(parts.path, parts.fragment, url)
    if parts.path.startswith("/events/"):
        return _parse_event(parts.path, url)
    if parts.path.startswith("/stories/"):
        return _parse_story(parts.path, url)
    raise NotImplementedError(f"No documented behavior for this page: {url}")


def _parse_handbook(path: str, fragment: str, url: str) -> HandbookUrl:
    if not fragment:
        raise InvalidInputError(f"Missing anchor in URL: {url}")
    return HandbookUrl(path=path, anchor=fragment)


def _parse_event(path: str, url: str) -> EventUrl:
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2 or not segments[1]:
        raise InvalidInputError(f"Missing event number in URL: {url}")
    return EventUrl(path=path, number=segments[1])


def _parse_story(path: str, url: str) -> StoryUrl:
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2 or not segments[1]:
        raise InvalidInputError(f"Missing story slug in URL: {url}")
    return StoryUrl(path=path, slug=segments[1])
