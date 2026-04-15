# netdiagram

LLM-friendly network diagram tool. Describe network topologies in YAML/JSON, render to Draw.io today (D2 and Mermaid planned).

## Install

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and execution.

~~~bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync project dependencies (creates .venv and installs runtime + dev deps)
uv sync
~~~

`pygraphviz` requires graphviz system headers. On macOS: `brew install graphviz`. On Debian/Ubuntu: `apt-get install graphviz graphviz-dev`.

## Usage

Run the CLI via `uv run`, which ensures commands execute against the project virtualenv:

~~~bash
uv run netdiagram validate topology.yaml
uv run netdiagram render topology.yaml --format drawio --output network.drawio
uv run netdiagram schema
uv run netdiagram list-types
~~~

## Development

~~~bash
uv run pytest                      # run tests
uv run pytest tests/test_foo.py    # run one test file
uv run ruff check src tests        # lint
~~~

See `docs/superpowers/specs/` for the design spec.
