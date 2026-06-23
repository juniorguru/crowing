import pytest

from jg.crowing.errors import InvalidInputError
from jg.crowing.parsing import parse_section
from tests.conftest import load_fixture


@pytest.fixture
def edge_html():
    return load_fixture("section-edge-cases.html")


@pytest.fixture
def git_html():
    return load_fixture("handbook-git.html")


def test_title_strips_headerlink(edge_html):
    assert parse_section(edge_html, "target").title == "Page Title"


def test_heading_strips_headerlink(edge_html):
    assert parse_section(edge_html, "target").heading == "Cílová sekce"


def test_collects_only_plain_paragraphs(edge_html):
    paragraphs = parse_section(edge_html, "target").paragraphs
    assert paragraphs == [
        "Plain paragraph one with a link and bold.",
        "Plain paragraph two spread over several lines.",
        "Subsection paragraph still belongs to the target section.",
    ]


def test_does_not_leak_into_next_section(edge_html):
    paragraphs = parse_section(edge_html, "target").paragraphs
    assert all("next section" not in p for p in paragraphs)


def test_intro_heading_collects_its_own_paragraph(edge_html):
    section = parse_section(edge_html, "intro")
    assert section.heading == "Úvod"
    assert section.paragraphs == ["First intro paragraph."]


def test_missing_anchor_raises_invalid_input(edge_html):
    with pytest.raises(InvalidInputError):
        parse_section(edge_html, "does-not-exist")


def test_real_handbook_page(git_html):
    section = parse_section(git_html, "reseni-problemu-s-gitem")
    assert section.title == "Git a GitHub"
    assert section.heading == "Řešení problémů s Gitem"
    assert len(section.paragraphs) == 2
    assert section.paragraphs[0].startswith("Asi neexistuje člověk")
    assert section.paragraphs[1].startswith("Pokud se ti to stane")
