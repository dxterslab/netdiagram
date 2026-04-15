# MCP Server — Phase 2a Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the netdiagram pipeline as an MCP server so LLMs can validate, layout, and render diagrams in-conversation.

**Architecture:** A thin `FastMCP` wrapper over the existing core (`netdiagram.ir`, `netdiagram.layout`, `netdiagram.renderers`). Five tools: `get_schema`, `list_types`, `validate_diagram`, `render_diagram`, `preview_layout`. A new console script `netdiagram-mcp` launches the server on stdio. No changes to the Phase 1 core — this is pure addition.

**Tech Stack:** Python 3.11+, `mcp` (official Anthropic MCP SDK — `mcp.server.fastmcp.FastMCP`), existing stack (Pydantic, Typer, networkx, pygraphviz, lxml).

**Spec reference:** `docs/superpowers/specs/2026-04-14-network-diagram-design.md` (§Interfaces → MCP Server)

---

## File Structure

```
src/netdiagram/
  mcp_server.py         # FastMCP app + tool implementations (new)
tests/
  test_mcp_server.py    # Unit tests for each tool (new)
  test_mcp_integration.py  # End-to-end stdio smoke test (new)
docs/
  mcp-integration.md    # How to configure Claude Desktop / Codex to use this server (new)
pyproject.toml          # Add mcp dep + netdiagram-mcp console script
CLAUDE.md               # Add a short pointer to the MCP docs
```

**Why `mcp_server.py` is self-contained:** The tool functions are small and call directly into existing modules. Splitting into a separate `mcp_tools.py` would be premature and force callers to know about two files. Tests import the tool functions directly from `mcp_server.py`.

**Why a separate integration test file:** stdio subprocess testing has different setup/teardown from pure unit tests. Keeping it in its own file avoids polluting the fast test suite — developers can skip it during rapid iteration.

---

## Task 1: Add `mcp` dependency + stub server module

**Files:**
- Modify: `pyproject.toml`
- Create: `src/netdiagram/mcp_server.py`
- Run: `uv lock`

- [ ] **Step 1: Add `mcp>=1.0` to runtime dependencies**

Edit `pyproject.toml`. In the `[project] dependencies = [...]` list, add `"mcp>=1.0"` at the end so it looks like:

```toml
dependencies = [
  "pydantic>=2.6",
  "typer>=0.12",
  "PyYAML>=6.0",
  "networkx>=3.2",
  "pygraphviz>=1.12",
  "lxml>=5.0",
  "mcp>=1.0",
]
```

Also add a console script entry for the MCP server. Under `[project.scripts]`, add the new entry so it reads:

```toml
[project.scripts]
netdiagram = "netdiagram.cli:app"
netdiagram-mcp = "netdiagram.mcp_server:main"
```

- [ ] **Step 2: Create stub `src/netdiagram/mcp_server.py`**

```python
"""MCP server exposing the netdiagram pipeline to LLMs.

Launch via the `netdiagram-mcp` console script (stdio transport). The server
registers five tools:
    - get_schema: JSON Schema for the Diagram IR
    - list_types: supported node/group type literals
    - validate_diagram: validate an IR dict, return structured errors
    - render_diagram: full pipeline IR -> layout -> backend output
    - preview_layout: IR -> layout only, returns computed positions
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

app = FastMCP("netdiagram")


def main() -> None:
    """Entry point for the `netdiagram-mcp` console script."""
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Lock and verify**

Run:
```bash
uv lock
uv sync
uv run python -c "from netdiagram.mcp_server import app; print(app.name)"
```

Expected output (last line): `netdiagram`

If the import fails with `ModuleNotFoundError: No module named 'mcp'`, confirm `mcp>=1.0` was added to `[project]` and re-run `uv sync`. If it fails with an ImportError on `FastMCP`, check that the installed `mcp` version is ≥1.0 (`uv pip list | grep mcp`).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock src/netdiagram/mcp_server.py
git commit -m "feat(mcp): scaffold FastMCP server with netdiagram-mcp console script"
```

---

## Task 2: MCP tool — `get_schema`

**Files:**
- Modify: `src/netdiagram/mcp_server.py` (add tool)
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_server.py`:

```python
"""Unit tests for MCP server tool functions.

Tools are plain Python functions after FastMCP decoration, so tests call
them directly rather than going through the MCP protocol.
"""

from netdiagram.mcp_server import get_schema


def test_get_schema_returns_diagram_schema():
    s = get_schema()
    assert s["title"] == "Diagram"
    assert s["$schema"].startswith("https://json-schema.org/")
    assert "properties" in s
    assert "nodes" in s["properties"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: `ImportError: cannot import name 'get_schema' from 'netdiagram.mcp_server'`

- [ ] **Step 3: Implement the tool**

Edit `src/netdiagram/mcp_server.py`. Add the import and the tool function after the `app = FastMCP(...)` line:

```python
from netdiagram.ir.schema import diagram_json_schema


@app.tool()
def get_schema() -> dict:
    """Return the JSON Schema (draft 2020-12) describing the netdiagram IR.

    The LLM should consult this schema when constructing IR objects to pass
    to validate_diagram or render_diagram.
    """
    return diagram_json_schema()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: `test_get_schema_returns_diagram_schema PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/mcp_server.py tests/test_mcp_server.py
git commit -m "feat(mcp): add get_schema tool"
```

---

## Task 3: MCP tool — `list_types`

**Files:**
- Modify: `src/netdiagram/mcp_server.py`
- Modify: `tests/test_mcp_server.py`

- [ ] **Step 1: Append failing test to `tests/test_mcp_server.py`**

Add to the end of `tests/test_mcp_server.py`:

```python
from netdiagram.mcp_server import list_types


def test_list_types_includes_physical_and_cloud_nodes():
    types = list_types()
    assert "node_types" in types
    assert "group_types" in types
    assert "router" in types["node_types"]
    assert "firewall" in types["node_types"]
    assert "vpc" in types["node_types"]
    assert "subnet" in types["group_types"]
    assert "availability_zone" in types["group_types"]


def test_list_types_values_are_string_lists():
    types = list_types()
    for nt in types["node_types"]:
        assert isinstance(nt, str)
    for gt in types["group_types"]:
        assert isinstance(gt, str)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: `ImportError: cannot import name 'list_types'` (the two new tests fail; existing `test_get_schema_returns_diagram_schema` still passes).

- [ ] **Step 3: Implement the tool**

Append to `src/netdiagram/mcp_server.py` (after the `get_schema` function):

```python
import typing as _t

from netdiagram.ir.models import GroupType, NodeType


@app.tool()
def list_types() -> dict:
    """Return the supported node and group type literals.

    Use this before constructing IR — each node and group must have a type
    drawn from these lists. Unknown types render as a neutral shape.
    """
    return {
        "node_types": list(_t.get_args(NodeType)),
        "group_types": list(_t.get_args(GroupType)),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/mcp_server.py tests/test_mcp_server.py
git commit -m "feat(mcp): add list_types tool"
```

---

## Task 4: MCP tool — `validate_diagram`

**Files:**
- Modify: `src/netdiagram/mcp_server.py`
- Modify: `tests/test_mcp_server.py`

- [ ] **Step 1: Append failing tests**

Add to `tests/test_mcp_server.py`:

```python
from netdiagram.mcp_server import validate_diagram


def _minimal_valid_ir() -> dict:
    return {
        "version": "1.0",
        "metadata": {"title": "T", "type": "physical"},
        "nodes": [{"id": "r1", "label": "r1", "type": "router"}],
    }


def test_validate_diagram_accepts_valid_ir():
    result = validate_diagram(_minimal_valid_ir())
    assert result == {"valid": True, "errors": []}


def test_validate_diagram_rejects_invalid_and_reports_errors():
    ir = _minimal_valid_ir()
    ir["links"] = [
        {"source": {"node": "r1"}, "target": {"node": "ghost"}}
    ]
    result = validate_diagram(ir)
    assert result["valid"] is False
    assert len(result["errors"]) >= 1
    # Each error is {"loc": "...", "msg": "..."}
    for err in result["errors"]:
        assert "loc" in err and "msg" in err
    # The message for an unknown-node link should surface in at least one error
    joined = " ".join(err["msg"] for err in result["errors"])
    assert "ghost" in joined


def test_validate_diagram_rejects_unknown_node_type():
    ir = _minimal_valid_ir()
    ir["nodes"][0]["type"] = "toaster"
    result = validate_diagram(ir)
    assert result["valid"] is False
```

- [ ] **Step 2: Run to verify failures**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: the three new tests fail with `ImportError: cannot import name 'validate_diagram'`.

- [ ] **Step 3: Implement the tool**

Append to `src/netdiagram/mcp_server.py`:

```python
from pydantic import ValidationError

from netdiagram.ir.models import Diagram


@app.tool()
def validate_diagram(ir: dict) -> dict:
    """Validate an IR dict against the Diagram schema.

    Returns {"valid": True, "errors": []} on success. On failure,
    {"valid": False, "errors": [{"loc": "field.path", "msg": "..."}]}.

    Use this before render_diagram so you can fix errors iteratively
    rather than seeing a render failure.
    """
    try:
        Diagram.model_validate(ir)
    except ValidationError as e:
        return {
            "valid": False,
            "errors": [
                {
                    "loc": ".".join(str(x) for x in err["loc"]) or "<root>",
                    "msg": err["msg"],
                }
                for err in e.errors()
            ],
        }
    return {"valid": True, "errors": []}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/mcp_server.py tests/test_mcp_server.py
git commit -m "feat(mcp): add validate_diagram tool with structured errors"
```

---

## Task 5: MCP tool — `render_diagram`

**Files:**
- Modify: `src/netdiagram/mcp_server.py`
- Modify: `tests/test_mcp_server.py`

- [ ] **Step 1: Append failing tests**

Add to `tests/test_mcp_server.py`:

```python
from netdiagram.mcp_server import render_diagram


def test_render_diagram_returns_drawio_xml():
    ir = _minimal_valid_ir()
    ir["nodes"].append({"id": "r2", "label": "r2", "type": "router"})
    ir["links"] = [{"source": {"node": "r1"}, "target": {"node": "r2"}}]

    result = render_diagram(ir, "drawio")
    assert result["format"] == "drawio"
    assert result["filename"].endswith(".drawio")
    assert "<mxfile" in result["content"]


def test_render_diagram_rejects_unknown_format():
    result = render_diagram(_minimal_valid_ir(), "mermaid")
    assert result["error"] is not None
    assert "unsupported format" in result["error"].lower()


def test_render_diagram_rejects_invalid_ir():
    ir = _minimal_valid_ir()
    ir["nodes"][0]["type"] = "not-a-real-type"
    result = render_diagram(ir, "drawio")
    assert result["error"] is not None
    assert "validation" in result["error"].lower() or "invalid" in result["error"].lower()
```

- [ ] **Step 2: Run to verify failures**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: 3 new tests fail with `ImportError: cannot import name 'render_diagram'`.

- [ ] **Step 3: Implement the tool**

Append to `src/netdiagram/mcp_server.py`:

```python
from netdiagram.layout import layout_diagram
from netdiagram.renderers.drawio import DrawioRenderer

_RENDERERS = {
    "drawio": DrawioRenderer(),
}


@app.tool()
def render_diagram(ir: dict, format: str = "drawio") -> dict:
    """Render an IR to a diagram file in the requested format.

    Returns {"format": ..., "filename": ..., "content": "..."} on success.
    On error, returns {"error": "message"}. Phase 1 supports only 'drawio'.
    """
    # Validate first so we fail fast with a clear message.
    try:
        diagram = Diagram.model_validate(ir)
    except ValidationError as e:
        return {
            "error": "validation failed",
            "errors": [
                {
                    "loc": ".".join(str(x) for x in err["loc"]) or "<root>",
                    "msg": err["msg"],
                }
                for err in e.errors()
            ],
        }

    renderer = _RENDERERS.get(format)
    if renderer is None:
        return {"error": f"unsupported format '{format}'. Available: {list(_RENDERERS)}"}

    try:
        laid = layout_diagram(diagram)
        content = renderer.render(laid)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"render failed: {exc}"}

    return {
        "format": format,
        "filename": f"{diagram.metadata.title.replace(' ', '-').lower()}{renderer.extension}",
        "content": content,
    }
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/mcp_server.py tests/test_mcp_server.py
git commit -m "feat(mcp): add render_diagram tool with drawio backend"
```

---

## Task 6: MCP tool — `preview_layout`

**Files:**
- Modify: `src/netdiagram/mcp_server.py`
- Modify: `tests/test_mcp_server.py`

- [ ] **Step 1: Append failing tests**

Add to `tests/test_mcp_server.py`:

```python
from netdiagram.mcp_server import preview_layout


def test_preview_layout_returns_positioned_nodes_and_edges():
    ir = _minimal_valid_ir()
    ir["nodes"].append({"id": "r2", "label": "r2", "type": "router"})
    ir["links"] = [{"source": {"node": "r1"}, "target": {"node": "r2"}}]

    result = preview_layout(ir)
    assert "nodes" in result
    assert "edges" in result
    assert "canvas_width" in result
    assert "canvas_height" in result

    ids = {n["id"] for n in result["nodes"]}
    assert ids == {"r1", "r2"}
    for n in result["nodes"]:
        assert set(n.keys()) >= {"id", "x", "y", "width", "height"}
        assert n["width"] > 0 and n["height"] > 0

    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["source"] == "r1" and edge["target"] == "r2"
    assert len(edge["path"]) >= 2
    for point in edge["path"]:
        assert "x" in point and "y" in point


def test_preview_layout_rejects_invalid_ir():
    ir = _minimal_valid_ir()
    ir["nodes"][0]["type"] = "not-real"
    result = preview_layout(ir)
    assert "error" in result
```

- [ ] **Step 2: Run to verify failures**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: 2 new tests fail with `ImportError: cannot import name 'preview_layout'`.

- [ ] **Step 3: Implement the tool**

Append to `src/netdiagram/mcp_server.py`:

```python
@app.tool()
def preview_layout(ir: dict) -> dict:
    """Compute layout for an IR without rendering to a backend format.

    Returns positioned nodes, routed edges, and canvas bounds. Useful for
    reasoning about spacing before committing to a render.
    """
    try:
        diagram = Diagram.model_validate(ir)
    except ValidationError as e:
        return {
            "error": "validation failed",
            "errors": [
                {
                    "loc": ".".join(str(x) for x in err["loc"]) or "<root>",
                    "msg": err["msg"],
                }
                for err in e.errors()
            ],
        }

    try:
        laid = layout_diagram(diagram)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"layout failed: {exc}"}

    return {
        "canvas_width": laid.canvas_width,
        "canvas_height": laid.canvas_height,
        "nodes": [
            {
                "id": pn.node.id,
                "x": pn.x,
                "y": pn.y,
                "width": pn.width,
                "height": pn.height,
            }
            for pn in laid.nodes
        ],
        "edges": [
            {
                "source": re.link.source.node,
                "target": re.link.target.node,
                "path": [{"x": p.x, "y": p.y} for p in re.path],
            }
            for re in laid.edges
        ],
    }
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_mcp_server.py -v`
Expected: all 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/mcp_server.py tests/test_mcp_server.py
git commit -m "feat(mcp): add preview_layout tool"
```

---

## Task 7: End-to-end stdio integration smoke test

**Files:**
- Create: `tests/test_mcp_integration.py`

This verifies the server starts correctly under stdio, lists the expected tools via MCP protocol, and that each tool can be invoked end-to-end. It spawns the server as a subprocess and uses the `mcp.client.stdio` helpers from the SDK.

- [ ] **Step 1: Write the integration test**

Create `tests/test_mcp_integration.py`:

```python
"""End-to-end MCP stdio smoke test.

Spawns `netdiagram-mcp` as a subprocess, connects via the MCP stdio client,
and exercises each registered tool. Marked slow so unit test runs can skip it.
"""

from __future__ import annotations

import asyncio
import json
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


pytestmark = pytest.mark.slow


async def _call(tool: str, arguments: dict | None = None) -> dict:
    """Spawn the server, call a single tool, return the parsed result."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "netdiagram.mcp_server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments or {})
            # FastMCP returns structured content; parse the first text block.
            text = result.content[0].text
            return json.loads(text)


def test_get_schema_over_stdio():
    data = asyncio.run(_call("get_schema"))
    assert data["title"] == "Diagram"


def test_list_types_over_stdio():
    data = asyncio.run(_call("list_types"))
    assert "router" in data["node_types"]


def test_validate_and_render_over_stdio():
    ir = {
        "version": "1.0",
        "metadata": {"title": "Smoke", "type": "physical"},
        "nodes": [
            {"id": "a", "label": "a", "type": "router"},
            {"id": "b", "label": "b", "type": "switch"},
        ],
        "links": [{"source": {"node": "a"}, "target": {"node": "b"}}],
    }
    valid = asyncio.run(_call("validate_diagram", {"ir": ir}))
    assert valid["valid"] is True

    rendered = asyncio.run(_call("render_diagram", {"ir": ir, "format": "drawio"}))
    assert rendered["format"] == "drawio"
    assert "<mxfile" in rendered["content"]
```

Also register the `slow` marker in `pyproject.toml`. Under `[tool.pytest.ini_options]`, replace:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers"
```

with:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers"
markers = [
  "slow: end-to-end tests that spawn subprocesses (deselect with -m 'not slow')",
]
```

- [ ] **Step 2: Run the integration test**

Run: `uv run pytest tests/test_mcp_integration.py -v`
Expected: 3 tests pass. The first invocation may take a second or two while the subprocess starts.

If the test hangs for more than 30 seconds, the server is probably not responding on stdio. Ctrl-C and debug by running the server manually:
```bash
uv run netdiagram-mcp
```
It should print nothing and wait on stdin (that's correct — stdio MCP servers communicate via line-delimited JSON).

- [ ] **Step 3: Confirm the fast suite still runs cleanly without slow tests**

Run: `uv run pytest -m 'not slow' -v`
Expected: all Phase 1 + unit MCP tests pass (no MCP integration tests run).

- [ ] **Step 4: Commit**

```bash
git add tests/test_mcp_integration.py pyproject.toml
git commit -m "test(mcp): end-to-end stdio integration smoke tests"
```

---

## Task 8: Documentation — integration guide + CLAUDE.md pointer

**Files:**
- Create: `docs/mcp-integration.md`
- Modify: `CLAUDE.md` (append a short pointer)
- Modify: `README.md` (mention MCP briefly)

No tests — documentation only. The point is that a future user (or future Claude session) can see how to wire this into Claude Desktop / Codex / another MCP client without rediscovering it.

- [ ] **Step 1: Create `docs/mcp-integration.md`**

```markdown
# MCP Integration Guide

`netdiagram-mcp` is an MCP server that exposes the diagram pipeline to any MCP-aware client (Claude Desktop, Codex, custom MCP hosts). Launch it on stdio; it registers five tools.

## Tools

| Tool | Input | Output |
|---|---|---|
| `get_schema` | — | JSON Schema for the Diagram IR |
| `list_types` | — | `{node_types: [...], group_types: [...]}` |
| `validate_diagram` | `ir: dict` | `{valid: bool, errors: [{loc, msg}, ...]}` |
| `render_diagram` | `ir: dict, format: str` | `{format, filename, content}` or `{error, errors?}` |
| `preview_layout` | `ir: dict` | `{canvas_width, canvas_height, nodes: [...], edges: [...]}` or `{error}` |

## Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on other platforms, adding an `mcpServers` entry:

```json
{
  "mcpServers": {
    "netdiagram": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/network-diagram", "run", "netdiagram-mcp"]
    }
  }
}
```

Restart Claude Desktop. The tools will appear under the tools menu.

## Configure Codex / Generic MCP Client

Launch the server with:

```bash
uv run netdiagram-mcp
```

The server speaks line-delimited JSON-RPC on stdin/stdout per the MCP spec. Any client that can spawn a subprocess and speak stdio MCP can attach.

## Typical LLM Workflow

1. User pastes raw LLDP/CDP/interface output into chat.
2. LLM calls `get_schema` once to learn the IR structure.
3. LLM drafts an IR dict, calls `validate_diagram`. On errors, the `loc`+`msg` pairs tell it exactly what to fix.
4. LLM calls `render_diagram(ir, "drawio")`. The `content` field holds the Draw.io XML — the LLM returns it to the user for download or writes it to a path.
5. If layout spacing needs inspection before committing, `preview_layout` returns positioned nodes and routed edges without rendering.

## Debugging

Run the server directly and pipe handwritten JSON-RPC:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"manual","version":"0"}}}' | uv run netdiagram-mcp
```

A response line confirms the server is alive. For a structured test harness, see `tests/test_mcp_integration.py`.
```

- [ ] **Step 2: Append a pointer to `CLAUDE.md`**

Locate the "Dev Workflow" section (around line 40 in `CLAUDE.md`). After the `pygraphviz` note about system headers, add a new subsection:

```markdown
### MCP server

`netdiagram-mcp` is a stdio MCP server that exposes the pipeline to LLMs. See `docs/mcp-integration.md` for client config and the tool list.
```

- [ ] **Step 3: Update `README.md` Usage section**

In `README.md`, find the `~~~bash` Usage block that lists `uv run netdiagram ...` commands. After the existing four CLI examples, add:

```bash
uv run netdiagram-mcp                         # start the MCP server on stdio
```

And add one more line to the Description section explaining MCP: before or after the existing description, add:

```markdown
Also ships as an **MCP server** (`netdiagram-mcp`) so LLMs can validate, lay out, and render diagrams directly in conversation. See `docs/mcp-integration.md`.
```

- [ ] **Step 4: Verify Markdown builds (trivial)**

Run:
```bash
wc -l docs/mcp-integration.md CLAUDE.md README.md
```

Confirm the three files are non-empty and reasonably sized. No build step needed — these are plain Markdown.

- [ ] **Step 5: Commit**

```bash
git add docs/mcp-integration.md CLAUDE.md README.md
git commit -m "docs(mcp): integration guide plus CLAUDE.md and README pointers"
```

---

## Wrap-Up

- [ ] **Final full suite**

Run: `uv run pytest`
Expected: all tests pass including MCP unit + integration.

Run: `uv run ruff check src tests`
Expected: clean.

- [ ] **Manual verification (author responsibility)**

1. `uv run netdiagram-mcp` — starts without printing anything (correct behavior).
2. In another terminal, exercise it via `uv run pytest tests/test_mcp_integration.py -v`.
3. (Optional) Configure a real MCP client (Claude Desktop) pointing at this server, open a conversation, and ask the LLM to "create a small router-switch topology and render it to Draw.io." Verify the XML round-trips through Draw.io successfully.

- [ ] **Tag**

```bash
git tag phase-2a-mcp
```
