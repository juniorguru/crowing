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


def write_carousel(images: list[Image.Image], output_dir: Path) -> Path:
    """Glue ``images`` into a single ``carousel.pdf`` (one page each) for LinkedIn."""
    path = output_dir / "carousel.pdf"
    first, *rest = images
    first.save(path, format="PDF", save_all=True, append_images=rest)
    return path
