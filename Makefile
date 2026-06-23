.PHONY: install test format assets build smoke demo verify clean

# Install dependencies into the project virtualenv.
install:
	uv sync

# Run the whole test suite (this also runs ruff lint, ruff format check
# and the cyclomatic complexity check via pytest-ruff).
test:
	uv run pytest

# Auto-fix lint issues and reformat the code.
format:
	uv run ruff check --fix
	uv run ruff format

# Regenerate raster assets from their vector sources (chick.png from chick-icon.svg).
assets:
	uv run --with cairosvg python -c "import cairosvg; cairosvg.svg2png(url='src/jg/crowing/assets/chick-icon.svg', write_to='src/jg/crowing/assets/chick.png', output_width=1080)"

# Build the source distribution and the wheel.
build:
	uv build

# End-to-end smoke test: runs the documented example with runtime deps only
# (no dev group), checking --help, the generated images and the PDF.
smoke:
	uv run --no-dev python tests/smoke.py

# End-to-end demo against the live site, for eyeballing the images.
demo:
	uv run crowing "https://junior.guru/handbook/git/#reseni-problemu-s-gitem" --output-dir tmp

# Everything that needs to pass before a change is done.
verify: test build smoke

clean:
	rm -rf dist tmp
