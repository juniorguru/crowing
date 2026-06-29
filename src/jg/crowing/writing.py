"""Imperative shell: persist rendered images to disk."""

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from jg.crowing.errors import InvalidInputError
from jg.crowing.rendering import (
    REEL_FPS,
    REEL_MAX_SECONDS,
    REEL_MUSIC,
    REEL_TRANSITION_SECONDS,
    reel_total_seconds,
    transition_durations,
)
from jg.crowing.urls import HandbookUrl


# Slideshows of static slides compress well even at a fast x264 preset: on a
# 35s/1047-frame fixture, "veryfast" cut encoding from ~13.5s to ~9s while the
# output was, if anything, slightly smaller (394KB vs 468KB at "medium").
REEL_PRESET = "veryfast"


def write_images(images: list[Image.Image], base_dir: Path, url: HandbookUrl) -> Path:
    """Save ``images`` as ``01.png``, ``02.png`` … under ``base_dir/<dir>/<anchor>``."""
    output_dir = base_dir / url.dir_name / url.anchor
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, image in enumerate(images, start=1):
        image.save(output_dir / f"{index:02d}.png")
    return output_dir


def write_carousel(images: list[Image.Image], output_dir: Path) -> Path:
    """Glue ``images`` into a single ``carousel.pdf`` (one page each) for LinkedIn."""
    path = output_dir / "carousel.pdf"
    first, *rest = images
    first.save(path, format="PDF", save_all=True, append_images=rest)
    return path


REEL_TRANSITION = "slideleft"  # ffmpeg xfade transition style for the swipe cut


def write_reel(
    frames: list[Image.Image],
    output_dir: Path,
    durations: list[float],
    fps: int = REEL_FPS,
    music: str = REEL_MUSIC,
    transition_seconds: float = REEL_TRANSITION_SECONDS,
) -> Path:
    """Glue ``frames`` into a ``reel.mp4`` slideshow with music, ``durations`` seconds each.

    Consecutive slides swipe-cut into each other over ``transition_seconds``, instead
    of a hard cut.
    """
    total = reel_total_seconds(durations, transition_seconds)
    if total >= REEL_MAX_SECONDS:
        raise InvalidInputError(
            f"The reel would be {round(total)}s long; keep it under {REEL_MAX_SECONDS}s "
            "by choosing a section with fewer or shorter paragraphs"
        )
    path = output_dir / "reel.mp4"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        silent = tmp_path / "reel-silent.mp4"
        _encode_silent(frames, durations, tmp_path, silent, fps, transition_seconds)
        _mux_music(silent, music, path)
    return path


def _encode_silent(
    frames: list[Image.Image],
    durations: list[float],
    tmp_dir: Path,
    silent: Path,
    fps: int,
    transition_seconds: float,
) -> None:
    """Encode ``frames`` held for ``durations`` seconds each into a silent ``silent`` video.

    Each frame is written to disk once; ffmpeg loops each one for its own duration and
    splices the results together with ``xfade``, instead of Python compositing every
    transition frame and piping it through as a duplicated input.
    """
    paths = [tmp_dir / f"{index:03d}.png" for index in range(len(frames))]
    for frame, frame_path in zip(frames, paths, strict=True):
        frame.save(frame_path)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    inputs = [
        arg
        for frame_path, duration in zip(paths, durations, strict=True)
        for arg in (
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-t",
            str(duration),
            "-i",
            str(frame_path),
        )
    ]
    filter_complex = _xfade_filter(durations, transition_seconds)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-preset",
            REEL_PRESET,
            "-pix_fmt",
            "yuv420p",
            str(silent),
        ],
        check=True,
    )


def _xfade_filter(durations: list[float], transition_seconds: float) -> str:
    """Build a ``filter_complex`` chaining each slide into the next with ``xfade``.

    Each transition's ``offset`` is the point, on the running merged stream's own
    timeline, where the next slide starts swiping in: the time elapsed so far minus
    the transitions already subtracted from it (each one shortens the merged stream
    by its own duration).
    """
    if len(durations) == 1:
        return "[0:v]format=yuv420p[v]"
    transitions = transition_durations(durations, transition_seconds)
    elapsed = durations[0]
    label = "0:v"
    parts = []
    for index, (duration, transition) in enumerate(
        zip(durations[1:], transitions, strict=True), start=1
    ):
        out_label = "v" if index == len(durations) - 1 else f"v{index}"
        offset = elapsed - transition
        parts.append(
            f"[{label}][{index}:v]xfade=transition={REEL_TRANSITION}:"
            f"duration={transition}:offset={offset}[{out_label}]"
        )
        elapsed += duration - transition
        label = out_label
    return ";".join(parts)


def _mux_music(video: Path, music: str, output: Path) -> None:
    """Lay ``music`` over ``video``, cut to the video length (``-shortest``).

    The track is already AAC, so both streams are copied without re-encoding.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-i",
            music,
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-shortest",
            str(output),
        ],
        check=True,
    )
