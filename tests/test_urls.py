import pytest

from jg.crowing.errors import InvalidInputError
from jg.crowing.urls import HandbookUrl, parse_url


def test_parse_url_returns_path_and_anchor():
    url = parse_url("https://junior.guru/handbook/git/#reseni-problemu-s-gitem")
    assert url == HandbookUrl(path="/handbook/git/", anchor="reseni-problemu-s-gitem")


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://junior.guru/handbook/git/#x", "handbook-git"),
        ("https://junior.guru/handbook/#x", "handbook"),
        ("https://junior.guru/handbook/soft-skills/cv/#x", "handbook-soft-skills-cv"),
    ],
)
def test_dir_name_joins_path_segments(url, expected):
    assert parse_url(url).dir_name == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/handbook/git/#x",
        "https://junior.guru.evil.com/handbook/git/#x",
        "http://google.com/handbook/#x",
    ],
)
def test_non_juniorguru_raises_not_implemented(url):
    with pytest.raises(NotImplementedError):
        parse_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://junior.guru/courses/#x",
        "https://junior.guru/#x",
        "https://junior.guru/club/#x",
    ],
)
def test_non_handbook_raises_not_implemented(url):
    with pytest.raises(NotImplementedError):
        parse_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://junior.guru/handbook/git/",
        "https://junior.guru/handbook/git/#",
    ],
)
def test_missing_anchor_raises_invalid_input(url):
    with pytest.raises(InvalidInputError):
        parse_url(url)


def test_www_subdomain_is_accepted():
    assert parse_url("https://www.junior.guru/handbook/git/#x").anchor == "x"
