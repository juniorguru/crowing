"""Imperative shell: persist rendered images to disk."""

from pathlib import Path

from PIL import Image

from jg.crowing.urls import HandbookUrl


def write_images(images: list[Image.Image], base_dir: Path, url: HandbookUrl) -> Path:
    """Save ``images`` as ``01.png``, ``02.png`` … under ``base_dir/<dir>/<anchor>``."""
    output_dir = base_dir / url.dir_name / url.anchor
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, image in enumerate(images, start=1):
        image.save(output_dir / f"{index:02d}.png")
    return output_dir
