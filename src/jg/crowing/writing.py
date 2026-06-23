"""Imperative shell: persist rendered images to disk."""

from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from jg.crowing.rendering import REEL_FPS, reel_frame_counts
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
    fps: int = REEL_FPS,
) -> Path:
    """Glue ``frames`` into a ``reel.mp4`` slideshow: a short intro, then 5s per slide."""
    path = output_dir / "reel.mp4"
    counts = reel_frame_counts(len(frames), fps)
    # macro_block_size=8 keeps the exact 1080x1920 size (both divisible by 8)
    writer = imageio.get_writer(path, fps=fps, codec="libx264", macro_block_size=8)
    try:
        for frame, count in zip(frames, counts):
            pixels = np.asarray(frame.convert("RGB"))
            for _ in range(count):
                writer.append_data(pixels)
    finally:
        writer.close()
    return path
