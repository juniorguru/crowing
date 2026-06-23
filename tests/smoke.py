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


URL = "https://junior.guru/handbook/git/#reseni-problemu-s-gitem"
EXPECTED_DIR = Path("handbook-git") / "reseni-problemu-s-gitem"


def _crowing(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["crowing", *args], capture_output=True, text=True)


def check_help() -> None:
    result = _crowing("--help")
    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
    print("--help works")


def check_example(output_dir: Path) -> None:
    result = _crowing(URL, "--output-dir", str(output_dir))
    assert result.returncode == 0, result.stderr or result.stdout

    created = output_dir / EXPECTED_DIR
    images = sorted(p.name for p in created.glob("*.png"))
    assert len(images) >= 3, f"expected at least intro + paragraph + CTA, got {images}"
    assert images == [f"{i:02d}.png" for i in range(1, len(images) + 1)], images
    assert (created / "carousel.pdf").exists(), "carousel.pdf was not created"
    print(f"example produced {len(images)} images and carousel.pdf")


def main() -> None:
    check_help()
    with tempfile.TemporaryDirectory() as tmp:
        check_example(Path(tmp))
    print("smoke OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        sys.exit(f"smoke FAILED: {error}")
