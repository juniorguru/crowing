import tomllib

import pytest

from jg.crowing.models import Post
from jg.crowing.parsing import parse_event, parse_section, parse_story
from jg.crowing.posts import prepare_post
from jg.crowing.writing import write_post
from tests.conftest import load_fixture


def test_story_post_keeps_full_lead():
    html = load_fixture("story.html")
    post = prepare_post(html, parse_story(html, "https://junior.guru/"))
    assert (
        post.title == "Příběh: Z barmana IT manažer. Teď mířím k roli firemního šamana"
    )
    assert post.text.startswith("Pětatřicetiletý Šimon")
    assert post.text.endswith("daleko nad rámec kódu.")
    assert "\n" not in post.text
    assert post.tags == []


def test_handbook_post_joins_all_extracted_paragraphs():
    html = load_fixture("section-edge-cases.html")
    section = parse_section(html, "target")
    post = prepare_post(html, section)
    assert post.title == "Příručka: Cílová sekce"
    assert post.text.split("\n\n") == [
        "".join(run.text for run in paragraph) for paragraph in section.paragraphs
    ]
    assert post.tags == []


def test_event_post_plain_text_and_icon_order():
    html = """
    <h1>Adina Fox: Focus v době AI<a class="headerlink">#</a></h1>
    <p class="lead">Lead <b>bold</b> and <a href="https://example.com">link</a>.</p>
    <ul class="note-explainer">
      <li><i class="bi bi-info-circle-fill"></i> Info</li>
      <li><i class="bi bi-star-fill"></i> Star</li>
      <li><i class="bi bi-piggy-bank-fill"></i> Free</li>
      <li><i class="bi bi-play-circle-fill"></i> Watch</li>
      <li><i class="bi bi-heart-fill"></i> Beginners</li>
    </ul>
    <h5 class="media-card-heading">Adina Fox</h5>
    <div class="media-card-meta">Head of Product Design</div>
    <div class="media-card-richtext"><p>Bio <a href="/">link</a>.</p><p>More bio.</p>
      <ul class="icon-links"><li>Discard social links</li></ul>
    </div>
    """
    post = prepare_post(html, parse_event(html, "https://junior.guru/"))
    assert post == Post(
        "Klubová akce: Focus v době AI",
        "Lead bold and link.\n\nℹ️ Info\n⭐ Star\n🐷 Free\n▶️ Watch\n❤️ Beginners"
        "\n\nAdina Fox\nHead of Product Design\n\nBio link.\n\nMore bio.",
    )


@pytest.mark.parametrize(
    "text", ['Quotes " and \\ paths\n\nPříběh ❤️', "\x00\b\f\t\r\x1f\x7f"]
)
def test_post_toml_round_trip(tmp_path, text):
    post = Post('Title "quoted"', text, ["python", "čeština"])
    path = write_post(post, tmp_path)
    assert path.name == "post.toml"
    assert tomllib.loads(path.read_text(encoding="utf-8")) == {
        "title": post.title,
        "text": text,
        "tags": post.tags,
    }
