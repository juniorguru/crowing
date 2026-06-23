import pytest

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import Run
from jg.crowing.parsing import parse_section
from tests.conftest import load_fixture


def text_of(runs: list[Run]) -> str:
    return "".join(run.text for run in runs)


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
    assert [text_of(p) for p in paragraphs] == [
        "Plain paragraph one with a link, bold and italics.",
        "Plain paragraph two spread over several lines.",
        "Subsection paragraph still belongs to the target section.",
    ]


def test_preserves_bold_and_italic_and_flattens_links(edge_html):
    first = parse_section(edge_html, "target").paragraphs[0]
    assert first == [
        Run("Plain paragraph one with a link, "),
        Run("bold", bold=True),
        Run(" and "),
        Run("italics", italic=True),
        Run("."),
    ]


def test_does_not_leak_into_next_section(edge_html):
    paragraphs = parse_section(edge_html, "target").paragraphs
    assert all("next section" not in text_of(p) for p in paragraphs)


def test_intro_heading_collects_its_own_paragraph(edge_html):
    section = parse_section(edge_html, "intro")
    assert section.heading == "Úvod"
    assert [text_of(p) for p in section.paragraphs] == ["First intro paragraph."]


def test_missing_anchor_raises_invalid_input(edge_html):
    with pytest.raises(InvalidInputError):
        parse_section(edge_html, "does-not-exist")


def test_collects_topics_from_table_of_contents(git_html):
    assert parse_section(git_html, "reseni-problemu-s-gitem").topics == [
        "Co je Git",
        "Jak se učit Git",
        "Ovládání Gitu",
        "Řešení problémů s Gitem",
        "Co je GitHub",
        "Jak se učit GitHub",
        "Dávej kód na GitHub",
        "Čti kód na GitHubu",
        "GitHub a pohovory",
    ]


def test_missing_h1_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        parse_section(load_fixture("section-no-h1.html"), "target")


def test_missing_table_of_contents_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        parse_section(load_fixture("section-no-toc.html"), "target")


def test_real_handbook_page(git_html):
    section = parse_section(git_html, "reseni-problemu-s-gitem")
    assert section.title == "Git a GitHub"
    assert section.heading == "Řešení problémů s Gitem"
    assert len(section.paragraphs) == 2
    assert text_of(section.paragraphs[0]).startswith("Asi neexistuje člověk")
    assert text_of(section.paragraphs[1]).startswith("Pokud se ti to stane")
