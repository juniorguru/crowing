"""Imperative shell: persist rendered images to disk."""

import subprocess
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image

from jg.crowing.errors import InvalidInputError
from jg.crowing.rendering import REEL_FPS, REEL_MAX_SECONDS, REEL_MUSIC
from jg.crowing.urls import HandbookUrl


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
    counts = [round(seconds * fps) for seconds in durations]
    # macro_block_size=8 keeps the exact 1080x1920 size (both divisible by 8)
    writer = imageio.get_writer(silent, fps=fps, codec="libx264", macro_block_size=8)
    try:
        for frame, count in zip(frames, counts):
            pixels = np.asarray(frame.convert("RGB"))
            for _ in range(count):
                writer.append_data(pixels)
    finally:
        writer.close()
    _mux_music(silent, music, path)
    silent.unlink()
    return path


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
