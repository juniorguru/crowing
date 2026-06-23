# Crowing 📢

Creates marketing assets from a piece of junior.guru website.

## Usage and behavior

```
$ crowing "https://junior.guru/handbook/git/#reseni-problemu-s-gitem"
```

- Downloads the handbook page's HTML
- Finds the page's H1 title
- Finds the page's table of contents (always .document-toc)
- Finds the anchor (leads to a heading)
- Reads all plain paragraphs within the section
- Skips notes or cards, embedded videos, etc., takes just paragraphs
- In current working directory (or whatever path user passed in CLI option) creates new subdirectory `handbook-git` and inside another one, `reseni-problemu-s-gitem`
- Inside the subsubdirectory creates a set of assets

### Instagram post: Intro image

- Instagram-ready square image called 01.png
- #fffa72 background
- Contains the title of the page, new line, and the heading. E.g. "Git a GitHub" and "Řešení problémů s Gitem".
- The H1 text is monospace and smaller
- The heading is larger and more important
- The texts are aligned to left
- Contains an [illustration of a chick](./src/jg/crowing/assets/chick-icon.svg) in the bottom right corner
- Contains an [arrow right](https://icons.getbootstrap.com/icons/arrow-right-circle-fill/) in the bottom left corner
- The arrow fill is #1755d1 but the arrow itself is white
- The arrow is one third smaller than the chick, both with a bit of padding from the image border
- Padding consistent with all other Instagram post images
- Beautiful typography and composition, the text, arrow, or illustration must not collide

### Instagram post: Paragraph images

- Instagram-ready square images called 02.png, 03.png, etc.
- One image for each paragraph
- White background
- The text is aligned to left
- The size of the text is adjusted so that it's as large as possible, but it must fit the image, including some padding.
- Padding consistent with all other Instagram post images

### Instagram post: Call to action

- Instagram-ready square images called XX.png, where XX is the last number
- #fffa72 background
- Everything on the card is center-aligned (the default alignment for the call to action)
- At the top, the [junior.guru logo](./src/jg/crowing/assets/junior-guru.min.png) above the text
- Text: "Zajímá tě tohle téma? Otevři si příručku a čti dál!", smaller than the logo and topics
- Under the text, flat blue button with white text
- The button:
  - has a #1755d1 (Bootstrap primary blue) background
  - has only slightly rounded corners, _not_ a pill: the corner radius is about one tenth of the button's height (Bootstrap's `0.375rem`, i.e. roughly 6px on a 60px-tall button)
  - says "junior.guru/handbook"
  - has the white [Bootstrap "journals" icon](https://icons.getbootstrap.com/icons/journals/) right before the text
  - is large and has margin equal to the card's padding above and below it
- Under the button, a cloud of the topics built from the page's ToC
- Each topic is displayed without wrapping; topics on the same line are separated by a middot (·) with spaces
- The topics are dark gold #998c00 so they read like a watermark on the light yellow
- The cloud stretches over the full width and fills the bottom remaining height, not a condensed left block
- The whitespace between topics is proportionally larger than between words within a topic, so it reads as a teaser, not a blob
- Padding consistent with all other Instagram post images

### LinkedIn: carousel

- Takes all the images created for the Instagram posts and glues them into a single PDF, which LinkedIn accepts as a document/carousel post
- The PDF is called `carousel.pdf` and lives next to the images
- One image per page, in the same order as the images (`01.png` first, the call to action last)
- Pages stay 1080×1080 px (1:1), the size LinkedIn recommends and which most users see on mobile; no resizing or cropping, the images already match
- Because the carousel mirrors the Instagram post, it naturally stays in LinkedIn's sweet spot of a few focused slides (LinkedIn allows up to 300 pages and 100 MB, but short carousels perform best); the bottom-right arrow on the intro doubles as a "swipe through" cue
- Branding (colors, fonts, layout) is already consistent across pages because they are the very same images

### Reel

- Takes the same slides as the carousel and glues them into a slideshow video, `reel.mp4`, next to the images
- Vertical 9:16, 1080×1920px
- Each square slide is centered on the 9:16 canvas, padded above and below with that slide's own background colour, so it stays seamless and full-bleed
- The last call to action slide is slightly different though:
  - It is 2:3, with equal vertical gaps between the logo, the teaser text, the button and the topics cloud; the gaps absorb all slack so the content spans the card from top to bottom
  - It is then also centered on the 9:16 canvas, padded above and below
  - The logo and the text above the button are significantly larger
  - The topics block keeps the same side padding as the square Instagram images (no extra top/bottom padding beyond the gaps)
- H.264 video in an MP4 container, sRGB, 30 fps
- The first image (the hook) is on screen for 3s, each paragraph slide for as many seconds as needed for reading the text on screen with speed of reading 200wpm, and the call to action for a fixed 10s
- Plain cut transitions
- If the whole video would be a minute or longer, the tool raises an invalid input error, because that is too long for a reel
- A royalty-free background music track [`slideshow-moire-main-version-02-01-15390.m4a`](./src/jg/crowing/assets/slideshow-moire-main-version-02-01-15390.m4a) plays under the slides, encoded as AAC and cut to the length of the video

### Typography

- If text is on yellow or white, it's #343434
- If text is on blue, it's white
- The text in the images renders links as plain text, but preserves other inline markup, such as bold, italics, etc.
- The text never breaks after a single-letter word. E.g. "Řešení problémů s Gitem" must never break between "s" and "Gitem"
- We use "Inter" font for text, and for monospace text (if any) we use "Liberation Mono"

### Errors

- If page is not within junior.guru, it raises not implemented
- If page is not within /handbook/, it raises not implemented
- If link doesn't include anchor, it's invalid input error
- If target page doesn't contain H1, ToC, or the anchor, it's invalid input error
- If the reel would be a minute or longer (too many paragraphs), it's invalid input error
- Uses suitable [click exceptions](https://click.palletsprojects.com/en/stable/api/#exceptions) for the input errors

## Installation and contributing

This project uses [uv](https://docs.astral.sh/uv/):

- `git clone` this repository.
- Run `uv run crowing --help` to learn what this tool can do.
- Run `uv run pytest` to run tests and check code.
- Run `uv run ruff format` to format code.

## Design decisions

The project aims to be as consistent as possible with other [@juniorguru](https://github.com/juniorguru/) projects.

### Basic structure

- `src/jg/crowing` is the main package
- `tests` contains all tests
- `LICENSE`, `README.md`, `uv.lock`, `.github`, etc.

### General

- Albeit open source, the project isn't published to PyPI (yet), it's an internal tool used by just its author and it's okay if it needs to be git cloned and installed to be used
- When it comes to architecture, aim to achieve the [Clean Architecture](https://www.youtube.com/watch?v=DJtef410XaM) ([textual slides](https://rhodesmill.org/brandon/slides/2014-07-pyohio/clean-architecture/)) with "imperative shell" using a "functional core"
- Be `async` by default
- Use Python type hints everywhere
- Use `httpx` for HTTP requests, `click` for the specification of CLI

### Testing

- Always develop by red green TDD
- If working with remote HTML, download it as a fixture to the `tests` directory and perform tests on it
- If you find edge cases, have several HTML fixtures for each test case
- Aim for low cyclomatic complexity
- Use `@pytest.mark.parametrize` if suitable
- When it comes to testing, aim to have many fast unit tests for "functional core" and "few integration tests" for "imperative shell"
- Aim at having a single assert per descriptive test function, unless impractical (e.g. when comparing small bits of complex structures)
- Unit, integration, and e2e tests must never depend on network, time, etc. smoke e2e tests can access network, but must not be ran by default when someone runs just `pytest`, those must be ran explicitly on CI or as part of more thorough verification pipeline

### Packaging, dependencies, tools

- Let `uv` to manage virtual environments and dependencies and use it as the main entrypoint
- There is a primitive `Makefile` wrapping the commands one runs often (`make install`, `make test`, `make format`, `make build`, `make smoke`, `make demo`, `make verify`, `make clean`); prefer it over typing the underlying `uv` commands by hand. `make verify` runs everything that must pass before a change is done.
- `pyproject.toml` contains also config for Ruff, including isort rules, which are as consistent as possible with other @juniorguru projects
- Using `uv_build` as the build backend, with `module-name` set to `jg.crowing`
- Ruff target version must comply with the `requires-python`
- When running `pytest`, ruff check runs automatically as well through `pytest-ruff` and cyclomatic complexity is also checked
- walrus operators are great and pyupgrade is one of the tools we regularly run to keep the code nice and modern
- The `FUNDING.yml` and `dependabot.yml` files inside `.github` are as consistent as possible with other @juniorguru projects
- There is a GitHub Actions workflow which runs all the tests and checks, including an end-to-end smoke test (`tests/smoke.py`, also runnable via `make smoke`) which installs the tool with runtime dependencies only and runs the documented example, checking `--help`, that it doesn't crash, and that it produces the expected assets as documented
