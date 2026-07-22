# Crowing 📢

Creates the following marketing assets from a piece of junior.guru website:

- Series of square images for an Instagram post
- LinkedIn carousel PDF
- Reel video

## Creating story content

```
$ crowing "https://junior.guru/stories/simon-koreny/"
```

- In current working directory (or whatever path user passed in CLI option) creates new subdirectory `stories` and inside another one, `simon-koreny`
- Splits the `.lead` into sentences and pairs them up, keeping along each slide's reading time calculated given speed of reading 200wpm
- Inside the subsubdirectory creates a set of assets

### Preparation: Intro image

- Contains "Rozhovor". Then new line, and the title of the interview. E.g. "Rozhovor" and then "Z barmana IT manažer. Teď mířím k roli firemního šamana, říká Šimon".
- The intro image contains image from .article-image in the bottom right corner, rounded to circle

### Preparation: Paragraph images

- Instagram-ready square images called 02.png, 03.png, etc.
- One image for every two sentences inside the .lead element
- White background
- The text is aligned to left
- The size of the text is adjusted so that it's as large as possible, but it must fit the image, including some padding.
- Each image has #1755d1 monospace text JUNIOR.GURU in right bottom corner, small and thin, but readable
- Padding consistent with all other Instagram post images

### Preparation: Call to action image

- Text: "Pravdivě o kariéře v IT. Přečti si celý rozhovor!"
- Button icon: [file-text](https://icons.getbootstrap.com/icons/file-text/)
- Button text: "junior.guru/stories"

### Instagram post

- Instagram-ready 1080×1080px square images called 01.png, 02.png, etc., by default with white background
- First image is the intro
- A series of lead paragraph images follows, in their original order
- The last image is the call to action image

### Errors

- If the link to /stories/ page doesn't include any of the expected elements, it's invalid input error
- Missing .article-image image is invalid input error

## Creating event content

```
$ crowing "https://junior.guru/events/63/"
```

- In current working directory (or whatever path user passed in CLI option) creates new subdirectory `events` and inside another one, `63`
- Prepare a few screenshots (see below) and for each screenshot, also keep along info about a reading time calculated for the screenshot given speed of reading 200wpm
- Inside the subsubdirectory creates a set of assets

### Preparation: Media card screenshot

- Opens the page in headless browser
- Sets the browser viewport to be 400px wide
- Scrolls down to the featured .media-card element
- Removes the .media-card-button call to action element
- Removes the .media-card-badge badge
- Removes underline from all links in the text
- Changes color of links to the color of their parent text, except for .icon-links which can stay blue as they are
- Takes a screenshot of the featured media card, so that it is completely visible

### Preparation: Lead screenshot

- Opens the page in headless browser
- Sets the browser viewport to be 400px wide
- Scrolls down to the .lead paragraph element
- Changes the background to #f4f8fe
- Removes underline from all links in the .lead text
- Changes color of links to the color of their parent text
- Takes a separate screenshot of each paragraph inside .lead, each must be completely visible on its screenshot

### Preparation: Note explainer screenshot

- Opens the page in headless browser
- Sets the browser viewport to be 300px wide
- Scrolls down to the .note-explainer element
- Removes underline from all links in the .note-explainer text
- Changes color of links to the color of their parent text
- Takes a separate screenshot of each .note-explainer-item, each item must be completely visible on its screenshot

### Preparation: Intro image

- Contains "Online akce" with the date and time of the event, but without year. Then new line, and the name of the event. E.g. "Online akce, 30.6. 18:00" and then "Focus v době AI".
- The page's .article-details contain the date of the event
- The page's H1 has the name of the speaker(s) as all text before the first `:`, the rest is the name of the event
- If the page's .article-details contain "Stáhni fotku" link, which leads to the speaker avatar, the intro image contains this image in the bottom right corner, rounded to circle
- The texts never break after a single-letter word or before uppercase two-letter word. E.g. "Řešení problémů s Gitem" must never break between "s" and "Gitem". "Život v době AI" must never break between "v" and "době" or between "době" and "AI".

### Preparation: Call to action image

- Text: "Zajímá tě tahle online akce? Pohlídej si ji!"
- Button icon: [play-circle-fill](https://icons.getbootstrap.com/icons/play-circle-fill/)
- Button text: "junior.guru/events"

### Instagram post

- Instagram-ready 1080×1080px square images called 01.png, 02.png, etc., by default with white background
- All contain the prepared screenshots, each resized so that it fits the square while keeping its aspect ratio, and with some padding added so that it doesn't touch the square borders and the result is aestethically pleasing. This padding is the same accross all the squares
- First image contains the media card
- A series of images with #f4f8fe background follows, each containing a single lead paragraph item, with their original order
- A series of images with white background follows, each containing a single note explainer item, with their original order preserved.
- Each lead and note explainer image has #1755d1 monospace text JUNIOR.GURU in right bottom corner, small and thin, but readable
- The last image is the call to action image

### Errors

- If the link to /events/ page doesn't include any of the expected elements, it's invalid input error

## Creating handbook content

```
$ crowing "https://junior.guru/handbook/git/#reseni-problemu-s-gitem"
```

- Downloads the handbook page's HTML
- Finds the page's H1 title
- Finds the page's table of contents (always .document-toc)
- Finds the anchor (leads to a heading)
- Reads the section's text content: plain paragraphs, notes (treated as regular paragraphs), and list items (each `<li>` becomes its own paragraph)
- If a sentence ends with `:` and is followed by list items, change the `:` to `…`, as colon doesn't work well in carousels, reels, etc.
- Skips cards, embedded videos, figures, etc.
- In current working directory (or whatever path user passed in CLI option) creates new subdirectory `handbook-git` and inside another one, `reseni-problemu-s-gitem`
- Inside the subsubdirectory creates a set of assets

### Preparation: Intro image

- Contains the title of the page, new line, and the heading. E.g. "Git a GitHub" and "Řešení problémů s Gitem".

### Preparation: Paragraph images

- Instagram-ready square images called 02.png, 03.png, etc.
- One image for each paragraph
- White background
- The text is aligned to left
- The size of the text is adjusted so that it's as large as possible, but it must fit the image, including some padding.
- Each image has #1755d1 monospace text JUNIOR.GURU in right bottom corner, small and thin, but readable
- Padding consistent with all other Instagram post images

### Preparation: Call to action

- Text: "Zajímá tě tohle téma? Otevři si příručku a čti dál!"
- Button icon: [journals](https://icons.getbootstrap.com/icons/journals/)
- Button text: "junior.guru/handbook"
- Under the button, a cloud of the topics built from the page's ToC
- Each topic is displayed without wrapping; topics on the same line are separated by a middot (·) with spaces
- The topics are dark gold #998c00 so they read like a watermark on the light yellow
- The cloud stretches over the full width and fills the bottom remaining height, not a condensed left block
- The whitespace between topics is proportionally larger than between words within a topic, so it reads as a teaser, not a blob

### Instagram post

- Instagram-ready 1080×1080px square images called 01.png, 02.png, etc., by default with white background
- First image is the intro image
- A series of paragraph images follows
- The last image is the call to action image

### Reel

- The topics block at the last call to action slide keeps the same side padding as the square Instagram images (no extra top/bottom padding beyond the gaps)
- White slides are the same except that the JUNIOR.GURU text is larger and it's positioned right bottom related to an imaginary 2:3 canvas, not to an imaginary 1:1 square canvas

### Errors

- If link to /handbook/ page doesn't include anchor, it's invalid input error
- If target /handbook/ page doesn't contain H1, ToC, or the anchor, it's invalid input error

## Behavior common to any given URLs

### Screenshots

- Use free and open source browser for the screenshots, such as Firefox or Chromium

### Intro images

- Instagram-ready square image called 01.png
- #fffa72 background
- Contains smaller text, new line, and larger text
- The smaller text is monospace
- The larger text is more important
- The texts are aligned to left
- Contains an [illustration of a chick](./src/jg/crowing/assets/chick-icon.svg) in the bottom right corner unless specified otherwise
- Contains an [arrow right](https://icons.getbootstrap.com/icons/arrow-right-circle-fill/) in the bottom left corner
- The arrow fill is #1755d1 but the arrow itself is white
- The arrow is one third smaller than the chick, both with a bit of padding from the image border
- Padding consistent with all other Instagram post images
- Beautiful typography and composition, the text, arrow, or illustration must not collide

### Call to action images

- Instagram-ready square image called XX.png, where XX is the last number
- #fffa72 background
- Everything on the card is center-aligned (the default alignment for the call to action)
- At the top, the [junior.guru logo](./src/jg/crowing/assets/junior-guru.min.png) above the text
- Text follows, smaller than the logo
- Under the text, flat blue button with white text
- The button:
  - has a #1755d1 (Bootstrap primary blue) background
  - has only slightly rounded corners, _not_ a pill: the corner radius is about one tenth of the button's height (Bootstrap's `0.375rem`, i.e. roughly 6px on a 60px-tall button)
  - has a text
  - has a white [Bootstrap icon](https://icons.getbootstrap.com/icons/journals/) right before the text
  - is large and has margin equal to the card's padding above and below it
- Padding consistent with all other Instagram post images

### Typography guidelines for assembled images (not those made of screenshots)

- If text is on yellow or white, it's #343434
- If text is on blue, it's white
- The text in the images renders links as plain text, but preserves other inline markup, such as bold, italics, etc.
- The texts never break after a single-letter word or before uppercase two-letter word. E.g. "Řešení problémů s Gitem" must never break between "s" and "Gitem". "Život v době AI" must never break between "v" and "době" or between "době" and "AI".
- We use "Inter" font for text, and for monospace text (if any) we use "Liberation Mono"

### LinkedIn carousel

- Takes all the images created for the Instagram post and glues them into a single PDF, which LinkedIn accepts as a document/carousel post
- The PDF is called `carousel.pdf` and lives next to the images
- One 1080×1080px image per page, in the same order as the images

### Reel

- Takes the square images and glues them into a slideshow video, `reel.mp4`, next to the images
- Vertical 9:16, 1080×1920px
- Each square slide is centered on the 9:16 canvas, padded above and below with that slide's own background colour, so it stays seamless and full-bleed
- The last call to action image is slightly different:
  - It is 2:3, with equal vertical gaps between the logo, the teaser text, and the button (and any other subsequent blocks, if present); the gaps absorb all slack so the content spans the card from top to bottom
  - It is then also centered on the 9:16 canvas, padded above and below
  - The logo and the text above the button are significantly larger
- H.264 video in an MP4 container, sRGB, 30 fps
- The first image (the intro hook) is on screen for 3s, each subsequent slide for as many seconds as needed for reading the text on screen with speed of reading 200wpm, and the call to action for a fixed 10s
- If the whole video would be 90s or longer, the tool first tries to save the situation by showing call to action only for 5s, and if that doesn't help, it raises an invalid input error, because 90s is too long for a reel
- If it is 60s or longer (but under 90s), it still renders but prints a warning that the video is getting long
- A royalty-free background music track [`Kicking It - Dyalla.m4a`](./src/jg/crowing/assets/Kicking%20It%20-%20Dyalla.m4a) plays under the slides, encoded as AAC and cut to the length of the video; the source track has a long intro, so it is trimmed to leave 3s of intro before the beat drops (aligning the drop with the end of the 3s hook) with a 1s fade-in at the start

### Video cuts

- Consecutive slides swipe into each other with a quick left slide transition (~0.25s), not a hard cut
- Each transition is clamped so it never outlasts either slide it joins
- The two transitions around a short interior slide are scaled down together, so the slide still gets some standalone time instead of vanishing into a three-way blend
- Overlapping transitions shorten the total video length accordingly

### Errors

- If page is not within junior.guru, it raises not implemented
- If page is not within a namespace which has behavior documented in this README, it raises not implemented - e.g. /handbook/ passes, but /wisdom/ raises
- If the reel would be 90s or longer (too many paragraphs), it's invalid input error
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
