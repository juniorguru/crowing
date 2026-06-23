.PHONY: install test format build smoke demo verify clean

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

# Build the source distribution and the wheel.
build:
	uv build

# Quick smoke test: does the CLI start at all?
smoke:
	uv run crowing --help

# End-to-end demo against the live site, for eyeballing the images.
demo:
	uv run crowing "https://junior.guru/handbook/git/#reseni-problemu-s-gitem" --output-dir tmp

# Everything that needs to pass before a change is done.
verify: test build smoke

clean:
	rm -rf dist tmp
