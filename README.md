# netdiagram

LLM-friendly network diagram tool. Describe network topologies in YAML/JSON, render to Draw.io or D2 (Mermaid planned).

Also ships as an **MCP server** (`netdiagram-mcp`) so LLMs can validate, lay out, and render diagrams directly in conversation. See `docs/mcp-integration.md`.

## Install

**Quick install** (requires [uv](https://docs.astral.sh/uv/) + graphviz headers):

~~~bash
brew install graphviz                 # macOS — required for pygraphviz
uv tool install git+https://github.com/dxterslab/netdiagram
~~~

After install, `netdiagram` and `netdiagram-mcp` are available globally. See [docs/installation.md](docs/installation.md) for pip/pipx install, local dev setup, MCP client configuration, and troubleshooting.

## Usage

Run the CLI via `uv run`, which ensures commands execute against the project virtualenv:

~~~bash
uv run netdiagram validate topology.yaml
uv run netdiagram render topology.yaml --format drawio --output network.drawio
uv run netdiagram render topology.yaml --format d2 --output network.d2
uv run netdiagram schema
uv run netdiagram list-types
uv run netdiagram-mcp                         # start the MCP server on stdio
~~~

## Development

~~~bash
uv run pytest                      # run tests
uv run pytest tests/test_foo.py    # run one test file
uv run ruff check src tests        # lint
~~~

## Documentation

- [Installation Guide](docs/installation.md) — prerequisites, install methods, MCP config, troubleshooting
- [CLI Usage Guide](docs/cli-usage.md) — commands, examples, link styles, tips
- [MCP + LLM Workflow](docs/mcp-llm-workflow.md) — how to use an LLM to build diagrams from raw network data
- [MCP Integration](docs/mcp-integration.md) — client configuration, tool reference, debugging
- [Design Spec](docs/superpowers/specs/2026-04-14-network-diagram-design.md) — architecture decisions and rationale

## Examples

Ready-to-render example topologies in `examples/`:

```bash
uv run netdiagram render examples/small-office.yaml --format drawio --output small-office.drawio
uv run netdiagram render examples/mlag-fabric.yaml --format d2 --output mlag-fabric.d2
```
