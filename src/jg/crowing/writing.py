"""Imperative shell: persist rendered images to disk."""

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from jg.crowing.errors import InvalidInputError
from jg.crowing.rendering import REEL_FPS, REEL_MAX_SECONDS, REEL_MUSIC
from jg.crowing.urls import HandbookUrl


# Slideshows of static slides compress well even at a fast x264 preset; this
# trades a little bitrate for several times less encoding time (see commit
# message / PR description for the measurements that justify the trade-off).
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


def write_reel(
    frames: list[Image.Image],
    output_dir: Path,
    durations: list[float],
    fps: int = REEL_FPS,
    music: str = REEL_MUSIC,
) -> Path:
    """Glue ``frames`` into a ``reel.mp4`` slideshow with music, ``durations`` seconds each."""
    total = sum(durations)
    if total >= REEL_MAX_SECONDS:
        raise InvalidInputError(
            f"The reel would be {round(total)}s long; keep it under {REEL_MAX_SECONDS}s "
            "by choosing a section with fewer or shorter paragraphs"
        )
    path = output_dir / "reel.mp4"
    silent = output_dir / ".reel-silent.mp4"
    with tempfile.TemporaryDirectory() as tmp_dir:
        _encode_silent(frames, durations, Path(tmp_dir), silent, fps)
    _mux_music(silent, music, path)
    silent.unlink()
    return path


def _encode_silent(
    frames: list[Image.Image],
    durations: list[float],
    tmp_dir: Path,
    silent: Path,
    fps: int,
) -> None:
    """Encode ``frames`` held for ``durations`` seconds each into a silent ``silent`` video.

    Each frame is written to disk once; ffmpeg loops each one for its own duration and
    concatenates the results, instead of Python piping every duplicated frame's raw
    pixels through ``imageio`` one append at a time, which is what made rendering slow.
    """
    paths = [tmp_dir / f"{index:03d}.png" for index in range(len(frames))]
    for frame, frame_path in zip(frames, paths):
        frame.save(frame_path)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    inputs = [
        arg
        for frame_path, duration in zip(paths, durations)
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
    streams = "".join(f"[{index}:v]" for index in range(len(frames)))
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            f"{streams}concat=n={len(frames)}:v=1:a=0[v]",
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
