"""End-to-end smoke test for the installed ``crowing`` command.

Runs the documented example against the live junior.guru site and checks the
tool starts, exposes ``--help``, and produces the expected images plus the PDF.
It uses only the standard library and the installed entry point, so running it
without the dev dependencies also guards against a runtime dependency
accidentally living in the dev group. Deeper checks of the images and the PDF
themselves are left to the unit and integration tests.

Run it with ``make smoke``.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


# Documented examples reachable without the Playwright browser (the event example
# needs a browser, so it is left to the integration tests).
EXAMPLES = [
    (
        "https://junior.guru/handbook/git/#reseni-problemu-s-gitem",
        Path("handbook-git") / "reseni-problemu-s-gitem",
    ),
    (
        "https://junior.guru/stories/simon-koreny/",
        Path("stories") / "simon-koreny",
    ),
]


def _crowing(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["crowing", *args], capture_output=True, text=True)


def check_help() -> None:
    result = _crowing("--help")
    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
    print("--help works")


def check_example(url: str, expected_dir: Path, output_dir: Path) -> None:
    result = _crowing(url, "--output-dir", str(output_dir))
    assert result.returncode == 0, result.stderr or result.stdout

    created = output_dir / expected_dir
    images = sorted(p.name for p in created.glob("*.png"))
    assert len(images) >= 3, f"expected at least intro + paragraph + CTA, got {images}"
    assert images == [f"{i:02d}.png" for i in range(1, len(images) + 1)], images
    assert (created / "carousel.pdf").exists(), "carousel.pdf was not created"
    reel = created / "reel.mp4"
    assert reel.exists() and reel.stat().st_size > 0, "reel.mp4 was not created"
    print(f"{url} produced {len(images)} images, carousel.pdf and reel.mp4")


def main() -> None:
    check_help()
    for url, expected_dir in EXAMPLES:
        with tempfile.TemporaryDirectory() as tmp:
            check_example(url, expected_dir, Path(tmp))
    print("smoke OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        sys.exit(f"smoke FAILED: {error}")
