import pytest

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import Run
from jg.crowing.parsing import parse_event, parse_section, parse_story
from tests.conftest import load_fixture


STORY_URL = "https://junior.guru/stories/simon-koreny/"


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


def test_collects_paragraphs_notes_and_list_items(edge_html):
    paragraphs = parse_section(edge_html, "target").paragraphs
    assert [text_of(p) for p in paragraphs] == [
        "Plain paragraph one with a link, bold and italics.",
        "Plain paragraph two spread over several lines.",
        "Inline git status code.",
        "Note paragraph kept as a regular paragraph.",
        "The list intro ends with a colon…",
        "First list item as a paragraph.",
        "Second list item as a paragraph.",
        "Subsection paragraph still belongs to the target section.",
    ]


def test_preserves_inline_code_as_a_code_run(edge_html):
    paragraph = parse_section(edge_html, "target").paragraphs[2]
    assert Run("git status", code=True) in paragraph


def test_colon_before_a_list_becomes_an_ellipsis(edge_html):
    texts = [text_of(p) for p in parse_section(edge_html, "target").paragraphs]
    assert "The list intro ends with a colon…" in texts
    assert "The list intro ends with a colon:" not in texts


def test_skips_cards_videos_and_admonition_titles(edge_html):
    texts = [text_of(p) for p in parse_section(edge_html, "target").paragraphs]
    assert "Card paragraph must be skipped." not in texts
    assert "Poznámka" not in texts


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


def test_parse_event_splits_speaker_and_event_from_h1():
    page = parse_event(load_fixture("event.html"), "https://junior.guru/events/63/")
    assert (page.speaker_name, page.event_name) == ("Adina Fox", "Focus v době AI")


def test_parse_event_reads_the_date_and_time_without_year_from_article_details():
    page = parse_event(load_fixture("event.html"), "https://junior.guru/events/63/")
    assert page.event_date == "30.6. 18:00"


def test_parse_event_resolves_avatar_url_from_stahni_fotku_link():
    page = parse_event(load_fixture("event.html"), "https://junior.guru/events/63/")
    assert page.avatar_url == (
        "https://junior.guru/static/avatars-participants/adina.png"
    )


def test_parse_event_without_stahni_fotku_link_has_no_avatar():
    page = parse_event(
        load_fixture("event-no-avatar.html"), "https://junior.guru/events/63/"
    )
    assert page.avatar_url is None


@pytest.fixture
def story_html():
    return load_fixture("story.html")


def test_parse_story_reads_the_title_from_the_h1(story_html):
    story = parse_story(story_html, STORY_URL)
    assert story.title == (
        "Z barmana IT manažer. Teď mířím k roli firemního šamana, říká Šimon"
    )


def test_parse_story_groups_two_sentences_per_slide(story_html):
    paragraphs = [text_of(p) for p in parse_story(story_html, STORY_URL).paragraphs]
    assert paragraphs == [
        "Pětatřicetiletý Šimon Kořený se živil v gastru až do pandemie, "
        "která definitivně završila jeho vyčerpanost. "
        "Dnes to vnímá jako vyhoření, které ještě ani nepřestalo doutnat.",
        "Ani ne za třičtvrtě roku už podepisoval smlouvu v softwarové firmě. "
        "Své poučení z chyb chce sdílet a propojovat světy daleko nad rámec kódu.",
    ]


def test_parse_story_keeps_inline_markup_within_a_slide(story_html):
    first = parse_story(story_html, STORY_URL).paragraphs[0]
    assert Run("vyhoření", bold=True) in first


def test_parse_story_flattens_links_within_a_slide(story_html):
    second = parse_story(story_html, STORY_URL).paragraphs[1]
    assert "softwarové firmě" in text_of(second)
    assert all(not run.code for run in second)  # a link is plain, not code


def test_parse_story_resolves_the_article_image_url(story_html):
    story = parse_story(story_html, STORY_URL)
    assert story.image_url == (
        "https://junior.guru/static/avatars-participants/simon-koreny.jpg"
    )


def test_parse_story_without_article_image_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        parse_story(load_fixture("story-no-image.html"), STORY_URL)


def test_parse_story_without_h1_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        parse_story(
            "<html><body><div class='lead'><p>A.</p></div></body></html>", STORY_URL
        )


def test_parse_story_without_lead_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        parse_story("<html><body><h1>Title</h1></body></html>", STORY_URL)
