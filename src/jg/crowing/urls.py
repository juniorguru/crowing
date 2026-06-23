"""Pure functions for validating and parsing handbook URLs."""

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


def parse_url(url: str) -> HandbookUrl:
    """Validate ``url`` and split it into a :class:`HandbookUrl`.

    Raises :class:`NotImplementedError` for non-handbook or non-junior.guru pages
    and :class:`InvalidInputError` when the anchor is missing.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if host != "junior.guru" and not host.endswith(".junior.guru"):
        raise NotImplementedError(f"Not a junior.guru page: {url}")
    if not parts.path.startswith("/handbook/"):
        raise NotImplementedError(f"Not a handbook page: {url}")
    if not parts.fragment:
        raise InvalidInputError(f"Missing anchor in URL: {url}")
    return HandbookUrl(path=parts.path, anchor=parts.fragment)
