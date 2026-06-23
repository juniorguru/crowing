# Crowing 📢

Creates marketing assets from a piece of junior.guru website.

## Usage and behavior

```
$ crowing "https://junior.guru/handbook/git/#reseni-problemu-s-gitem"
```

- Downloads the handbook page's HTML
- Finds the page's H1 title
- Finds the anchor (leads to a heading)
- Reads all plain paragraphs within the section
- Skips notes or cards, embedded videos, etc., takes just paragraphs
- In current working directory (or whatever path user passed in CLI option) creates new subdirectory `handbook-git` and inside another one, `reseni-problemu-s-gitem`
- Inside the subsubdirectory creates a set of Instagram-ready square images
- The images are sorted by filename: 01.png, 02.png, etc.
- First image is intro. It has #fffa72 background and #343434 text. It contains the title of the page, new line, and the heading. In this case "Git a GitHub" and "Řešení problémů s Gitem". The H1 text is monospace and smaller. The heading is larger and more important. The texts are aligned to left. Beautiful typography and composition.
- Then there is one image for each paragraph. It has white background and #343434 text. The text is aligned to left. The size of the text is adjusted so that it's as large as possible, but it must fit the image, including some padding. The padding is consistent across all images.
- The text in the images renders links as plain text, but preserves other inline markup, such as bold, italics, etc.
- The text never breaks after a single-letter word. E.g. "Řešení problémů s Gitem" must never break between "s" and "Gitem"
- Last image is call to action. It has #fffa72 background and a flat button with white text. The button:
  - has a #1755d1 (Bootstrap primary blue) background
  - has only slightly rounded corners, _not_ a pill: the corner radius is about one tenth of the button's height (Bootstrap's `0.375rem`, i.e. roughly 6px on a 60px-tall button)
  - says "junior.guru/handbook"
  - has the white [Bootstrap "journals" icon](https://icons.getbootstrap.com/icons/journals/) right before the text
- We use "Inter" font for text, and for monospace text (if any) we use "Liberation Mono".

### Errors

- If page is not within junior.guru, it raises not implemented
- If page is not within /handbook/, it raises not implemented
- If link doesn't include anchor, it's invalid input error
- If target anchor doesn't exist, it's invalid input error
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

### Packaging, dependencies, tools

- Let `uv` to manage virtual environments and dependencies and use it as the main entrypoint
- There is a primitive `Makefile` wrapping the commands one runs often (`make install`, `make test`, `make format`, `make build`, `make smoke`, `make demo`, `make verify`, `make clean`); prefer it over typing the underlying `uv` commands by hand. `make verify` runs everything that must pass before a change is done.
- `pyproject.toml` contains also config for Ruff, including isort rules, which are as consistent as possible with other @juniorguru projects
- Using `uv_build` as the build backend, with `module-name` set to `jg.crowing`
- Ruff target version must comply with the `requires-python`
- When running `pytest`, ruff check runs automatically as well through `pytest-ruff` and cyclomatic complexity is also checked
- The `FUNDING.yml` and `dependabot.yml` files inside `.github` are as consistent as possible with other @juniorguru projects
- There is a GitHub Actions workflow which runs all the tests and checks, including a smoke test which installs the tool and tries if running it with `--help` works or crashes
