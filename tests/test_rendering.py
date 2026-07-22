from unittest.mock import patch

import pytest
from PIL import Image, ImageChops, ImageDraw

from jg.crowing.errors import InvalidInputError
from jg.crowing.models import Run, Section, Shot, Story
from jg.crowing.rendering import (
    BLUE,
    CHICK_WIDTH,
    DARK,
    EVENT_CTA,
    PADDING,
    READING_WPM,
    REEL_CARD_HEIGHT,
    REEL_CTA_RESCUE_SECONDS,
    REEL_CTA_SECONDS,
    REEL_HEIGHT,
    REEL_HOOK_SECONDS,
    REEL_MAX_SECONDS,
    REEL_WIDTH,
    SIZE,
    STORY_CTA,
    WHITE,
    YELLOW,
    circle_image,
    compose_square,
    event_reel_durations,
    fit_intro,
    fit_reel_durations,
    glue_words,
    intro_layout,
    load_font,
    load_mono_font,
    reading_seconds,
    reel_durations,
    reel_total_seconds,
    render_cta,
    render_event_reel,
    render_intro,
    render_paragraph,
    render_reel,
    render_section,
    render_story,
    render_story_reel,
    story_reel_durations,
    to_reel_frame,
    to_words,
    transition_durations,
    wrap_text,
)


def _story(paragraphs: list[list[Run]]) -> Story:
    return Story(title="Rozhovor s někým", paragraphs=paragraphs, image_url="x.jpg")


CORNER = Image.new("RGBA", (CHICK_WIDTH, CHICK_WIDTH), (255, 0, 255, 255))
PREVIEW = Image.new("RGB", (400, 400), "#00ff00")  # a stand-in page-top screenshot


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


@pytest.fixture
def draw() -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(Image.new("RGB", (SIZE, SIZE)))


def test_wrap_text_keeps_all_words(draw):
    text = "one two three four five six seven eight nine ten"
    lines = wrap_text(draw, text, load_font(48), max_width=200)
    assert " ".join(lines).split() == text.split()


def test_wrap_text_respects_width(draw):
    text = "one two three four five six seven eight nine ten"
    font = load_font(48)
    lines = wrap_text(draw, text, font, max_width=200)
    assert len(lines) > 1
    assert all(draw.textlength(line, font=font) <= 200 for line in lines)


def test_load_mono_font_is_liberation_mono():
    assert load_mono_font(40).getname()[0] == "Liberation Mono"


def test_intro_heading_is_larger_than_title(draw):
    _, _, title_font, heading_font = fit_intro(
        draw, "Git a GitHub", "Řešení problémů s Gitem"
    )
    assert heading_font.size > title_font.size


def test_intro_title_is_monospace(draw):
    _, _, title_font, _ = fit_intro(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert title_font.getname()[0] == "Liberation Mono"


def test_intro_heading_uses_inter(draw):
    _, _, _, heading_font = fit_intro(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert heading_font.getname()[0] == "Inter"


def test_intro_heading_does_not_orphan_single_letter_word(draw):
    _, heading_lines, _, _ = fit_intro(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert all(line.split()[-1] != "s" for line in heading_lines)


def _boxes_overlap(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def test_intro_has_chick_in_bottom_right(draw):
    x0, y0, x1, y1 = intro_layout(
        draw, "Git a GitHub", "Řešení problémů s Gitem"
    ).chick_box
    assert (
        x1 == SIZE - PADDING
        and y1 == SIZE - PADDING
        and x0 > SIZE // 2
        and y0 > SIZE // 2
    )


def test_intro_has_arrow_in_bottom_left(draw):
    x0, y0, x1, y1 = intro_layout(
        draw, "Git a GitHub", "Řešení problémů s Gitem"
    ).arrow_box
    assert x0 == PADDING and y1 == SIZE - PADDING and x1 < SIZE // 2 and y0 > SIZE // 2


def test_intro_arrow_is_one_third_smaller_than_chick(draw):
    layout = intro_layout(draw, "Git a GitHub", "Řešení problémů s Gitem")
    chick_height = layout.chick_box[3] - layout.chick_box[1]
    arrow_height = layout.arrow_box[3] - layout.arrow_box[1]
    assert arrow_height == pytest.approx(chick_height * 2 / 3, abs=4)


def test_intro_arrow_is_blue_circle_with_white_arrow():
    image = render_intro("Git a GitHub", "Řešení problémů s Gitem")
    pixels = image.load()
    region = [(x, y) for x in range(0, SIZE // 2) for y in range(SIZE // 2, SIZE)]
    has_blue = any(pixels[x, y] == hex_to_rgb(BLUE) for x, y in region)
    has_white = any(pixels[x, y] == hex_to_rgb(WHITE) for x, y in region)
    assert has_blue and has_white


def test_intro_text_does_not_collide_with_chick(draw):
    layout = intro_layout(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert not _boxes_overlap(layout.text_box, layout.chick_box)


def test_intro_text_does_not_collide_with_arrow(draw):
    layout = intro_layout(draw, "Git a GitHub", "Řešení problémů s Gitem")
    assert not _boxes_overlap(layout.text_box, layout.arrow_box)


def test_intro_text_is_left_aligned():
    image = render_intro("Git a GitHub", "Řešení problémů s Gitem")
    pixels = image.load()
    dark = hex_to_rgb(DARK)
    left_edge = min(x for x in range(SIZE) for y in range(SIZE) if pixels[x, y] == dark)
    assert left_edge < PADDING + 30


def test_to_words_groups_styled_segments():
    runs = [Run("hello wor"), Run("ld", bold=True), Run(" there", italic=True)]
    words = to_words(runs)
    assert [["".join(s[0] for s in w)] for w in words] == [
        ["hello"],
        ["world"],
        ["there"],
    ]
    # the middle word mixes plain and bold segments
    assert words[1] == [("wor", False, False, False), ("ld", True, False, False)]
    assert words[2] == [("there", False, True, False)]


def test_to_words_keeps_all_text_for_long_paragraph():
    runs = [Run("word " * 30)]
    words = to_words(runs)
    assert len(words) == 30


def test_glue_words_keeps_single_letter_word_with_next():
    words = to_words([Run("problémů s Gitem")])
    units = ["".join(segment[0] for segment in unit) for unit in glue_words(words)]
    assert "s Gitem" in units


def test_glue_words_preserves_styling_of_the_following_word():
    words = to_words([Run("a "), Run("Gitem", bold=True)])
    assert glue_words(words) == [
        [("a ", False, False, False), ("Gitem", True, False, False)]
    ]


@pytest.mark.parametrize(
    "image, color",
    [
        (render_intro("Git a GitHub", "Řešení problémů"), YELLOW),
        (render_paragraph([Run("Nějaký odstavec textu.")]), WHITE),
        (render_cta(), YELLOW),
    ],
)
def test_background_color(image, color):
    assert image.size == (SIZE, SIZE)
    assert image.getpixel((5, 5)) == hex_to_rgb(color)


def _button_bbox(image) -> tuple[int, int, int, int]:
    blue = hex_to_rgb(BLUE)
    pixels = image.load()
    xs = [x for x in range(SIZE) for y in range(SIZE) if pixels[x, y] == blue]
    ys = [y for y in range(SIZE) for x in range(SIZE) if pixels[x, y] == blue]
    return min(xs), min(ys), max(xs), max(ys)


def test_cta_has_dark_message_above_the_button():
    image = render_cta()
    pixels = image.load()
    dark = hex_to_rgb(DARK)
    _, button_top, _, _ = _button_bbox(image)
    assert any(pixels[x, y] == dark for x in range(SIZE) for y in range(button_top))


def test_cta_topics_cloud_is_a_watermark_below_the_button():
    topics = ["Co je Git", "Ovládání Gitu", "Co je GitHub", "GitHub a pohovory"]
    image = render_cta(topics)
    pixels = image.load()
    watermark = hex_to_rgb("#998c00")
    _, _, _, button_bottom = _button_bbox(image)
    assert any(
        pixels[x, y] == watermark
        for x in range(SIZE)
        for y in range(button_bottom, SIZE)
    )


def test_render_cta_button_reflects_the_given_content():
    # the event card's button label/icon differ from the handbook's, so its blue
    # button spans a different width than the default handbook one
    assert _button_bbox(render_cta()) != _button_bbox(render_cta(content=EVENT_CTA))


def test_render_cta_without_topics_is_vertically_centered():
    image = render_cta(content=EVENT_CTA)  # no topics ⇒ centered, not top-heavy
    # bounding box of everything that isn't the yellow background
    diff = ImageChops.difference(image, Image.new("RGB", image.size, YELLOW))
    _, top, _, bottom = diff.convert("L").getbbox()
    assert (top + bottom) // 2 == pytest.approx(SIZE // 2, abs=8)


def test_render_event_cta_has_no_topics_cloud():
    image = render_cta(content=EVENT_CTA)  # events pass no topics
    pixels = image.load()
    gold = hex_to_rgb("#998c00")
    assert not any(pixels[x, y] == gold for x in range(SIZE) for y in range(SIZE))


def test_cta_button_is_bootstrap_blue_with_white_glyphs():
    image = render_cta()
    pixels = image.load()
    blue, white = hex_to_rgb(BLUE), hex_to_rgb(WHITE)
    blues = sum(pixels[x, y] == blue for x in range(SIZE) for y in range(SIZE))
    whites = sum(pixels[x, y] == white for x in range(SIZE) for y in range(SIZE))
    assert blues > 20000  # a sizable blue button
    assert whites > 200  # the icon and the text are white


def test_cta_button_corners_are_subtly_rounded_not_a_pill():
    image = render_cta()
    pixels = image.load()
    blue = hex_to_rgb(BLUE)
    x0, y0, x1, y1 = _button_bbox(image)
    height = y1 - y0 + 1

    def width_at(y: int) -> int:
        row = [x for x in range(x0, x1 + 1) if pixels[x, y] == blue]
        return max(row) - min(row) + 1 if row else 0

    full = width_at((y0 + y1) // 2)
    # by 15 % down the corner is already full width (a pill would still be far from it)
    assert width_at(y0 + round(height * 0.15)) >= full - 2
    # but the very top row is inset by the small radius, so it is not a plain rectangle
    assert width_at(y0) < full


def test_cta_button_icon_sits_left_of_the_text():
    image = render_cta()
    pixels = image.load()
    white = hex_to_rgb(WHITE)
    x0, _, x1, _ = _button_bbox(image)
    white_xs = [
        x for x in range(x0, x1 + 1) for y in range(SIZE) if pixels[x, y] == white
    ]
    # leftmost white (icon) is clearly left of the button centre
    assert min(white_xs) < (x0 + x1) // 2


def test_render_paragraph_with_markup_draws_dark_text():
    runs = [
        Run("plain "),
        Run("bold", bold=True),
        Run(" and "),
        Run("italic", italic=True),
    ]
    image = render_paragraph(runs)
    colors = {image.getpixel((x, y)) for x in range(SIZE) for y in range(SIZE)}
    assert hex_to_rgb(WHITE) in colors
    assert any(sum(c) < 200 for c in colors)  # dark glyph pixels present


def test_render_paragraph_has_blue_wordmark_bottom_right():
    image = render_paragraph([Run("Nějaký odstavec.")])
    pixels = image.load()
    region = [(x, y) for x in range(SIZE // 2, SIZE) for y in range(SIZE // 2, SIZE)]
    assert any(pixels[x, y] == hex_to_rgb(BLUE) for x, y in region)


def test_render_paragraph_renders_inline_code_in_blue():
    image = render_paragraph([Run("git status", code=True), Run(" je příkaz.")])
    pixels = image.load()
    # the wordmark is on the right; blue in the left half must be the code run
    assert any(
        pixels[x, y] == hex_to_rgb(BLUE) for x in range(SIZE // 2) for y in range(SIZE)
    )


def test_render_section_counts_intro_paragraphs_and_cta():
    section = Section(
        title="T",
        heading="H",
        paragraphs=[[Run("a")], [Run("b")], [Run("c")]],
    )
    images = render_section(section)
    assert len(images) == 1 + 3 + 1
    assert images[0].getpixel((5, 5)) == hex_to_rgb(YELLOW)
    assert images[1].getpixel((5, 5)) == hex_to_rgb(WHITE)
    assert images[-1].getpixel((5, 5)) == hex_to_rgb(YELLOW)


def test_render_story_counts_intro_paragraphs_preview_and_cta():
    images = render_story(_story([[Run("a")], [Run("b")], [Run("c")]]), CORNER, PREVIEW)
    assert len(images) == 1 + 3 + 1 + 1  # intro + paragraphs + preview + cta
    assert images[0].getpixel((5, 5)) == hex_to_rgb(YELLOW)  # intro
    assert images[1].getpixel((5, 5)) == hex_to_rgb(WHITE)  # paragraph
    assert images[-1].getpixel((5, 5)) == hex_to_rgb(YELLOW)  # cta


def test_render_story_intro_shows_the_corner_image():
    intro = render_story(_story([[Run("a")]]), CORNER, PREVIEW)[0]
    pixels = intro.load()
    region = [(x, y) for x in range(SIZE // 2, SIZE) for y in range(SIZE // 2, SIZE)]
    assert any(pixels[x, y] == (255, 0, 255) for x, y in region)


def test_render_story_preview_slide_precedes_the_cta():
    images = render_story(_story([[Run("a")]]), CORNER, PREVIEW)
    preview = images[-2]  # second to last, right before the cta
    pixels = preview.load()
    # the green stand-in screenshot sits centered on the square
    assert pixels[SIZE // 2, SIZE // 2] == (0, 255, 0)
    assert preview.getpixel((5, 5)) == hex_to_rgb(WHITE)  # white padding around it


def test_render_story_cta_has_no_topics_cloud():
    cta = render_story(_story([[Run("a")]]), CORNER, PREVIEW)[-1]
    pixels = cta.load()
    gold = hex_to_rgb("#998c00")
    assert not any(pixels[x, y] == gold for x in range(SIZE) for y in range(SIZE))


def test_story_reel_durations_hook_readings_and_cta():
    durations = story_reel_durations(_story([[Run("word " * 100)]]))
    assert len(durations) == 1 + 1 + 1
    assert durations[0] == REEL_HOOK_SECONDS
    assert durations[1] == pytest.approx(100 / READING_WPM * 60)
    assert durations[-1] == REEL_CTA_SECONDS


def test_render_story_reel_is_one_portrait_frame_per_slide():
    story = _story([[Run("a")], [Run("b")]])
    intro = Image.new("RGB", (SIZE, SIZE), hex_to_rgb(YELLOW))
    frames = render_story_reel(story, intro=intro)
    assert len(frames) == 1 + 2 + 1  # intro + paragraphs + cta
    assert all(frame.size == (REEL_WIDTH, REEL_HEIGHT) for frame in frames)


def test_render_cta_button_reflects_the_story_content():
    assert _button_bbox(render_cta()) != _button_bbox(render_cta(content=STORY_CTA))


def test_reel_frame_is_9_by_16_portrait():
    frame = to_reel_frame(Image.new("RGB", (SIZE, SIZE), hex_to_rgb(YELLOW)))
    assert frame.size == (REEL_WIDTH, REEL_HEIGHT)
    assert REEL_HEIGHT * 9 == REEL_WIDTH * 16


def test_reel_frame_pads_with_the_slide_background():
    frame = to_reel_frame(Image.new("RGB", (SIZE, SIZE), hex_to_rgb(YELLOW)))
    assert frame.getpixel((5, 5)) == hex_to_rgb(YELLOW)
    assert frame.getpixel((REEL_WIDTH // 2, REEL_HEIGHT - 5)) == hex_to_rgb(YELLOW)


def test_reel_frame_keeps_the_square_content_centered():
    frame = to_reel_frame(Image.new("RGB", (SIZE, SIZE), hex_to_rgb(WHITE)))
    assert frame.getpixel((REEL_WIDTH // 2, REEL_HEIGHT // 2)) == hex_to_rgb(WHITE)


def test_render_reel_is_one_portrait_frame_per_slide():
    section = Section(title="T", heading="H", paragraphs=[[Run("a")], [Run("b")]])
    frames = render_reel(section)
    assert len(frames) == len(render_section(section))
    assert all(frame.size == (REEL_WIDTH, REEL_HEIGHT) for frame in frames)


def test_render_reel_reuses_a_given_intro_instead_of_rendering_one():
    section = Section(title="T", heading="H", paragraphs=[[Run("a")]])
    intro = Image.new("RGB", (SIZE, SIZE), hex_to_rgb(YELLOW))
    with patch("jg.crowing.rendering.render_intro") as render_intro_mock:
        frames = render_reel(section, intro=intro)
    render_intro_mock.assert_not_called()
    assert frames[0].getpixel((5, 5)) == hex_to_rgb(YELLOW)


def test_render_cta_can_be_a_taller_two_by_three_card():
    card = render_cta(["Co je Git"], height=REEL_CARD_HEIGHT, stretch=True)
    assert card.size == (SIZE, REEL_CARD_HEIGHT)
    assert REEL_CARD_HEIGHT * 2 == SIZE * 3  # 2:3 portrait


def test_render_cta_without_topics_keeps_the_button_out_of_the_very_bottom():
    # on a taller card with no cloud, the button clusters in the lower third rather
    # than being stretched down to the bottom padding
    card = render_cta(content=EVENT_CTA, height=REEL_CARD_HEIGHT, stretch=True)
    blue = hex_to_rgb(BLUE)
    pixels = card.load()
    button_bottom = max(
        y
        for x in range(0, SIZE, 8)
        for y in range(REEL_CARD_HEIGHT)
        if pixels[x, y] == blue
    )
    assert (
        button_bottom < REEL_CARD_HEIGHT - 2 * PADDING
    )  # not jammed against the bottom


def test_reading_seconds_scales_with_word_count():
    assert reading_seconds("word " * 200, wpm=200) == pytest.approx(60)
    assert reading_seconds("word " * 100, wpm=200) == pytest.approx(30)


def test_reel_durations_fixed_hook_reading_paragraphs_fixed_cta():
    section = Section(
        title="T",
        heading="H",
        paragraphs=[[Run("word " * 100)]],  # 100 words -> 30s at 200 wpm
        topics=["Co je Git"],
    )
    durations = reel_durations(section)
    assert len(durations) == 1 + 1 + 1  # hook + paragraph + cta
    assert durations[0] == REEL_HOOK_SECONDS
    assert durations[1] == pytest.approx(100 / READING_WPM * 60)
    assert durations[-1] == REEL_CTA_SECONDS


def test_transition_durations_one_per_gap():
    durations = [3.0, 4.0, 4.0]
    assert transition_durations(durations, transition_seconds=0.25) == [0.25, 0.25]


def test_transition_durations_clamped_to_the_shorter_neighbor():
    durations = [3.0, 0.1, 4.0]
    assert transition_durations(durations, transition_seconds=0.25) == [0.05, 0.05]


def test_transition_durations_never_exceed_an_interior_slides_own_duration():
    # both gaps independently clamp to 0.2 (the middle slide's own length), but
    # together they'd consume it twice over, leaving it no standalone time at all
    durations = [3.0, 0.2, 4.0]
    gaps = transition_durations(durations, transition_seconds=0.25)
    assert sum(gaps) == pytest.approx(0.2)
    assert gaps == [pytest.approx(0.1), pytest.approx(0.1)]


def test_reel_total_seconds_subtracts_the_overlaps():
    durations = [3.0, 4.0, 4.0]
    assert reel_total_seconds(durations, transition_seconds=0.25) == pytest.approx(
        3.0 + 4.0 + 4.0 - 2 * 0.25
    )


def test_reel_total_seconds_with_a_single_slide():
    assert reel_total_seconds([3.0], transition_seconds=0.25) == 3.0


def test_compose_square_is_a_square_of_the_given_size():
    composed = compose_square(Image.new("RGB", (800, 400), BLUE))
    assert composed.size == (SIZE, SIZE)


def test_compose_square_keeps_the_aspect_ratio_within_the_padded_box():
    composed = compose_square(Image.new("RGB", (800, 400), BLUE))
    box = SIZE - 2 * PADDING
    # a 2:1 screenshot is width-constrained: it spans the whole box wide, half as tall
    left, top, right, bottom = _color_bbox(composed, hex_to_rgb(BLUE))
    assert (left, right) == (PADDING, PADDING + box)
    assert (bottom - top) == pytest.approx(box // 2, abs=2)
    assert (top + bottom) // 2 == pytest.approx(SIZE // 2, abs=1)  # vertically centered


def test_compose_square_pads_with_white():
    composed = compose_square(Image.new("RGB", (800, 400), BLUE))
    assert composed.getpixel((0, 0)) == hex_to_rgb(WHITE)


def test_compose_square_pads_with_the_given_background():
    composed = compose_square(Image.new("RGB", (800, 400), BLUE), background=YELLOW)
    assert composed.getpixel((0, 0)) == hex_to_rgb(YELLOW)


def test_compose_square_without_sign_has_no_wordmark():
    composed = compose_square(Image.new("RGB", (400, 400), WHITE))
    region = [(x, y) for x in range(SIZE // 2, SIZE) for y in range(SIZE // 2, SIZE)]
    assert not any(composed.getpixel((x, y)) == hex_to_rgb(BLUE) for x, y in region)


def test_compose_square_with_sign_has_blue_wordmark_bottom_right():
    composed = compose_square(Image.new("RGB", (400, 400), WHITE), sign=True)
    region = [(x, y) for x in range(SIZE // 2, SIZE) for y in range(SIZE // 2, SIZE)]
    assert any(composed.getpixel((x, y)) == hex_to_rgb(BLUE) for x, y in region)


def _color_bbox(image: Image.Image, color: tuple[int, int, int]):
    """Bounding box of the pixels matching ``color`` as ``(left, top, right, bottom)``."""
    diff = ImageChops.difference(
        image.convert("RGB"), Image.new("RGB", image.size, color)
    )
    mask = diff.convert("L").point(lambda value: 255 if value == 0 else 0)
    return mask.getbbox()


def test_circle_image_is_a_square_of_the_requested_width():
    circled = circle_image(Image.new("RGB", (200, 120), BLUE), width=80)
    assert circled.size == (80, 80)


def test_circle_image_keeps_the_center_and_clears_the_corners():
    circled = circle_image(Image.new("RGB", (200, 120), BLUE), width=80)
    assert circled.getpixel((40, 40))[3] == 255  # opaque in the middle
    assert circled.getpixel((0, 0))[3] == 0  # transparent in the corner


def test_render_intro_uses_the_corner_image_instead_of_the_chick():
    avatar = Image.new("RGBA", (CHICK_WIDTH, CHICK_WIDTH), (255, 0, 255, 255))
    image = render_intro("Focus v době AI", "Adina Fox", corner_image=avatar)
    pixels = image.load()
    region = [(x, y) for x in range(SIZE // 2, SIZE) for y in range(SIZE // 2, SIZE)]
    assert any(pixels[x, y] == (255, 0, 255) for x, y in region)


def test_wrap_text_keeps_two_letter_caps_with_previous_word(draw):
    lines = wrap_text(draw, "Život v době AI", load_font(200), max_width=300)
    assert not any(line.strip() == "AI" for line in lines)  # "AI" never starts a line
    assert any("době AI" in line for line in lines)


def test_glue_words_keeps_two_letter_caps_with_previous_word():
    words = to_words([Run("v době AI")])
    units = ["".join(segment[0] for segment in unit) for unit in glue_words(words)]
    assert "AI" not in units
    assert "v době AI" in units


def test_event_reel_durations_hook_readings_and_cta():
    shots = [
        Shot(Image.new("RGB", (10, 10)), reading_seconds=5.0),
        Shot(Image.new("RGB", (10, 10)), reading_seconds=2.5),
    ]
    assert event_reel_durations(shots) == [
        float(REEL_HOOK_SECONDS),
        5.0,
        2.5,
        float(REEL_CTA_SECONDS),
    ]


def test_render_event_reel_has_one_frame_per_slide_plus_cta():
    squares = [Image.new("RGB", (SIZE, SIZE), YELLOW) for _ in range(3)]
    frames = render_event_reel(squares, EVENT_CTA)
    assert len(frames) == len(squares) + 1  # the CTA is appended


def test_render_event_reel_frames_are_9_by_16():
    frames = render_event_reel([Image.new("RGB", (SIZE, SIZE), WHITE)], EVENT_CTA)
    assert all(frame.size == (REEL_WIDTH, REEL_HEIGHT) for frame in frames)


def test_fit_reel_durations_leaves_a_short_reel_untouched():
    durations = [3.0, 4.0, 10.0]
    assert fit_reel_durations(durations) == durations


def test_fit_reel_durations_shortens_the_cta_to_rescue_a_long_reel():
    durations = [3.0, 80.0, 10.0]  # 92s with the full CTA, 87s with the 5s rescue
    assert fit_reel_durations(durations)[-1] == float(REEL_CTA_RESCUE_SECONDS)


def test_fit_reel_durations_raises_when_even_a_short_cta_cannot_help():
    with pytest.raises(InvalidInputError):
        fit_reel_durations([3.0, float(REEL_MAX_SECONDS), 10.0])
