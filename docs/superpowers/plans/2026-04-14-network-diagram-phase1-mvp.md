# Network Diagram Tool — Phase 1 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool that validates network topology YAML/JSON against a Pydantic-backed IR, computes a readable layout, and renders to Draw.io XML.

**Architecture:** Three layers — IR (Pydantic models + JSON Schema), layout engine (graphviz-based placement + custom overlap resolution), renderers (Draw.io only in Phase 1). A Typer CLI wraps it all. Each layer has a clear interface so Phase 2 can plug in D2/Mermaid renderers and the MCP server without disturbing existing code.

**Tech Stack:** Python 3.11+, [uv](https://docs.astral.sh/uv/) for packaging and execution, Pydantic v2, Typer, PyYAML, networkx, pygraphviz, lxml, pytest.

**Spec reference:** `docs/superpowers/specs/2026-04-14-network-diagram-design.md`

---

## File Structure

```
network-diagram/
├── pyproject.toml
├── README.md
├── src/netdiagram/
│   ├── __init__.py
│   ├── ir/
│   │   ├── __init__.py
│   │   ├── models.py          # Pydantic: Interface, Node, Link, Group, Diagram
│   │   ├── schema.py          # JSON Schema export
│   │   └── loader.py          # YAML/JSON load + error formatting
│   ├── layout/
│   │   ├── __init__.py
│   │   ├── types.py           # LayoutedDiagram, PositionedNode, RoutedEdge
│   │   ├── dimensions.py      # Node width/height calculation
│   │   ├── topology.py        # Classify graph shape
│   │   ├── placement.py       # graphviz initial coordinates
│   │   ├── overlap.py         # Overlap resolution pass
│   │   └── engine.py          # Pipeline orchestrator
│   ├── renderers/
│   │   ├── __init__.py
│   │   ├── base.py            # Renderer protocol
│   │   └── drawio.py          # Draw.io XML renderer
│   └── cli.py                 # Typer app
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/              # Sample IR YAML files
    │   ├── simple_two_nodes.yaml
    │   ├── branch_office.yaml
    │   └── invalid_missing_node.yaml
    ├── test_ir_models.py
    ├── test_ir_loader.py
    ├── test_ir_schema.py
    ├── test_layout_dimensions.py
    ├── test_layout_topology.py
    ├── test_layout_placement.py
    ├── test_layout_overlap.py
    ├── test_layout_engine.py
    ├── test_renderer_drawio.py
    ├── test_cli.py
    └── test_end_to_end.py
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/netdiagram/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
dist/
build/
*.egg-info/
.venv/
venv/
.DS_Store
*.drawio.bak
```

Note: `uv.lock` is intentionally NOT ignored — it locks transitive dependencies for reproducible builds and must be committed.

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "netdiagram"
version = "0.1.0"
description = "LLM-friendly network diagram tool (IR -> Draw.io, D2, Mermaid)"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.6",
  "typer>=0.12",
  "PyYAML>=6.0",
  "networkx>=3.2",
  "pygraphviz>=1.12",
  "lxml>=5.0",
]

[project.scripts]
netdiagram = "netdiagram.cli:app"

[dependency-groups]
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "ruff>=0.4",
]

[tool.hatch.build.targets.wheel]
packages = ["src/netdiagram"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "C4", "SIM"]
```

`[dependency-groups]` is PEP 735 — uv reads dev dependencies from there via `uv sync` (as opposed to the older `[project.optional-dependencies]` which required `pip install -e ".[dev]"`). Using `[dependency-groups]` keeps dev tooling out of the published wheel.

- [ ] **Step 3: Create `README.md`**

```markdown
# netdiagram

LLM-friendly network diagram tool. Describe network topologies in YAML/JSON, render to Draw.io, D2, or Mermaid.

## Install

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and execution.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync project dependencies (creates .venv and installs runtime + dev deps)
uv sync
```

`pygraphviz` requires graphviz system headers. On macOS: `brew install graphviz`. On Debian/Ubuntu: `apt-get install graphviz graphviz-dev`.

## Usage

Run the CLI via `uv run`, which ensures commands execute against the project virtualenv:

```bash
uv run netdiagram validate topology.yaml
uv run netdiagram render topology.yaml --format drawio --output network.drawio
uv run netdiagram schema
uv run netdiagram list-types
```

## Development

```bash
uv run pytest                      # run tests
uv run pytest tests/test_foo.py    # run one test file
uv run ruff check src tests        # lint
```

See `docs/superpowers/specs/` for the design spec.
```

- [ ] **Step 4: Create empty `src/netdiagram/__init__.py`**

```python
"""netdiagram: LLM-friendly network diagram tool."""

__version__ = "0.1.0"
```

- [ ] **Step 5: Create empty `tests/__init__.py` and `tests/conftest.py`**

`tests/__init__.py`: empty file.

`tests/conftest.py`:

```python
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
```

- [ ] **Step 6: Verify install and test runner work**

Run:
```bash
uv sync
uv run pytest
```

Expected: `uv sync` creates `.venv`, resolves all dependencies, and writes `uv.lock`. `pytest` reports "no tests ran" with exit code 5 (no tests collected — that's fine here, we have none yet). If `pygraphviz` install fails, follow README for system deps.

- [ ] **Step 7: Commit**

```bash
git add .gitignore pyproject.toml uv.lock README.md src/netdiagram/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: project scaffolding with uv, pyproject.toml, and test setup"
```

---

## Task 2: IR Models — Core Types

**Files:**
- Create: `src/netdiagram/ir/__init__.py`
- Create: `src/netdiagram/ir/models.py`
- Test: `tests/test_ir_models.py`

- [ ] **Step 1: Create `src/netdiagram/ir/__init__.py`**

```python
from netdiagram.ir.models import (
    Diagram,
    Group,
    GroupType,
    Interface,
    InterfaceState,
    Link,
    LinkEndpoint,
    LinkStyle,
    Metadata,
    Node,
    NodeType,
)

__all__ = [
    "Diagram",
    "Group",
    "GroupType",
    "Interface",
    "InterfaceState",
    "Link",
    "LinkEndpoint",
    "LinkStyle",
    "Metadata",
    "Node",
    "NodeType",
]
```

- [ ] **Step 2: Write failing tests for models**

Create `tests/test_ir_models.py`:

```python
import pytest
from pydantic import ValidationError

from netdiagram.ir import Diagram, Group, Interface, Link, LinkEndpoint, Metadata, Node


def test_minimal_valid_diagram():
    d = Diagram(
        version="1.0",
        metadata=Metadata(title="Test", type="physical"),
        nodes=[Node(id="r1", label="r1", type="router")],
    )
    assert d.version == "1.0"
    assert d.nodes[0].id == "r1"


def test_duplicate_node_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate node id"):
        Diagram(
            version="1.0",
            metadata=Metadata(title="T", type="physical"),
            nodes=[
                Node(id="a", label="a", type="router"),
                Node(id="a", label="a2", type="switch"),
            ],
        )


def test_link_references_unknown_node_rejected():
    with pytest.raises(ValidationError, match="unknown node 'x'"):
        Diagram(
            version="1.0",
            metadata=Metadata(title="T", type="physical"),
            nodes=[Node(id="a", label="a", type="router")],
            links=[
                Link(
                    source=LinkEndpoint(node="a"),
                    target=LinkEndpoint(node="x"),
                )
            ],
        )


def test_link_references_unknown_interface_rejected():
    with pytest.raises(ValidationError, match="interface 'gi0/9' not found on node 'a'"):
        Diagram(
            version="1.0",
            metadata=Metadata(title="T", type="physical"),
            nodes=[
                Node(id="a", label="a", type="router", interfaces=[Interface(id="gi0/1")]),
                Node(id="b", label="b", type="router", interfaces=[Interface(id="gi0/1")]),
            ],
            links=[
                Link(
                    source=LinkEndpoint(node="a", interface="gi0/9"),
                    target=LinkEndpoint(node="b", interface="gi0/1"),
                )
            ],
        )


def test_group_membership_validated():
    with pytest.raises(ValidationError, match="unknown group 'missing'"):
        Diagram(
            version="1.0",
            metadata=Metadata(title="T", type="physical"),
            nodes=[Node(id="a", label="a", type="router", group="missing")],
        )


def test_group_nesting_validated():
    d = Diagram(
        version="1.0",
        metadata=Metadata(title="T", type="logical"),
        groups=[
            Group(id="vpc1", label="VPC1", type="vpc"),
            Group(id="subnet1", label="Subnet1", type="subnet", parent="vpc1"),
        ],
        nodes=[Node(id="srv", label="srv", type="server", group="subnet1")],
    )
    assert d.groups[1].parent == "vpc1"


def test_group_parent_must_exist():
    with pytest.raises(ValidationError, match="unknown parent group 'nope'"):
        Diagram(
            version="1.0",
            metadata=Metadata(title="T", type="logical"),
            groups=[Group(id="a", label="A", type="subnet", parent="nope")],
        )


def test_group_cycle_rejected():
    with pytest.raises(ValidationError, match="cycle in group hierarchy"):
        Diagram(
            version="1.0",
            metadata=Metadata(title="T", type="logical"),
            groups=[
                Group(id="a", label="A", type="zone", parent="b"),
                Group(id="b", label="B", type="zone", parent="a"),
            ],
        )
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_ir_models.py -v`
Expected: ImportError / ModuleNotFoundError for `netdiagram.ir`.

- [ ] **Step 4: Implement models**

Create `src/netdiagram/ir/models.py`:

```python
"""Pydantic models for the network diagram IR."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- Enumerations --------------------------------------------------------

NodeType = Literal[
    # Physical
    "router",
    "switch",
    "firewall",
    "server",
    "load_balancer",
    "access_point",
    "endpoint",
    "generic",
    # Cloud
    "vpc",
    "cloud_lb",
    "cloud_db",
    "internet_gateway",
    "nat_gateway",
    "security_group",
]

GroupType = Literal[
    "subnet",
    "vlan",
    "vpc",
    "availability_zone",
    "region",
    "zone",
    "dmz",
]

InterfaceState = Literal["up", "down", "unknown"]
LinkStyle = Literal["solid", "dashed", "dotted"]
DiagramType = Literal["physical", "logical"]


# --- Leaf models ---------------------------------------------------------

class Interface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str | None = None
    speed: str | None = None  # "1G", "10G", etc. — free-form in Phase 1
    state: InterfaceState = "unknown"
    data: dict[str, Any] = Field(default_factory=dict)


class LinkEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node: str
    interface: str | None = None


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    type: DiagramType
    description: str | None = None


# --- Graph entities ------------------------------------------------------

class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    type: NodeType
    group: str | None = None
    interfaces: list[Interface] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _interfaces_unique(self) -> Node:
        seen: set[str] = set()
        for iface in self.interfaces:
            if iface.id in seen:
                raise ValueError(f"duplicate interface id '{iface.id}' on node '{self.id}'")
            seen.add(iface.id)
        return self


class Group(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    type: GroupType
    parent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class Link(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: LinkEndpoint
    target: LinkEndpoint
    label: str | None = None
    style: LinkStyle = "solid"
    data: dict[str, Any] = Field(default_factory=dict)


# --- Root diagram --------------------------------------------------------

class Diagram(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "1.0"
    metadata: Metadata
    groups: list[Group] = Field(default_factory=list)
    nodes: list[Node]
    links: list[Link] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cross_references(self) -> Diagram:
        # Node id uniqueness
        node_ids: set[str] = set()
        iface_ids_by_node: dict[str, set[str]] = {}
        for n in self.nodes:
            if n.id in node_ids:
                raise ValueError(f"duplicate node id '{n.id}'")
            node_ids.add(n.id)
            iface_ids_by_node[n.id] = {i.id for i in n.interfaces}

        # Group id uniqueness
        group_ids: set[str] = set()
        for g in self.groups:
            if g.id in group_ids:
                raise ValueError(f"duplicate group id '{g.id}'")
            group_ids.add(g.id)

        # Group parent references + cycle detection
        for g in self.groups:
            if g.parent is not None and g.parent not in group_ids:
                raise ValueError(f"group '{g.id}' references unknown parent group '{g.parent}'")
        self._check_group_cycles(group_ids)

        # Node -> group reference
        for n in self.nodes:
            if n.group is not None and n.group not in group_ids:
                raise ValueError(f"node '{n.id}' references unknown group '{n.group}'")

        # Link endpoints reference valid nodes and (optionally) interfaces
        for link in self.links:
            for role, ep in (("source", link.source), ("target", link.target)):
                if ep.node not in node_ids:
                    raise ValueError(f"link {role} references unknown node '{ep.node}'")
                if ep.interface is not None and ep.interface not in iface_ids_by_node[ep.node]:
                    raise ValueError(
                        f"link {role} interface '{ep.interface}' not found on node '{ep.node}'"
                    )

        return self

    def _check_group_cycles(self, group_ids: set[str]) -> None:
        parents = {g.id: g.parent for g in self.groups}
        for gid in group_ids:
            seen: set[str] = set()
            cur: str | None = gid
            while cur is not None:
                if cur in seen:
                    raise ValueError(f"cycle in group hierarchy at '{cur}'")
                seen.add(cur)
                cur = parents.get(cur)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_ir_models.py -v`
Expected: all 8 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/ir/ tests/test_ir_models.py
git commit -m "feat(ir): Pydantic models for Node, Link, Group, Diagram with cross-ref validation"
```

---

## Task 3: IR Loader (YAML/JSON + Error Formatting)

**Files:**
- Create: `src/netdiagram/ir/loader.py`
- Create: `tests/fixtures/simple_two_nodes.yaml`
- Create: `tests/fixtures/branch_office.yaml`
- Create: `tests/fixtures/invalid_missing_node.yaml`
- Test: `tests/test_ir_loader.py`

- [ ] **Step 1: Create fixture files**

`tests/fixtures/simple_two_nodes.yaml`:

```yaml
version: "1.0"
metadata:
  title: "Simple two-node diagram"
  type: physical
nodes:
  - id: r1
    label: r1
    type: router
    interfaces:
      - id: gi0/1
        state: up
  - id: r2
    label: r2
    type: router
    interfaces:
      - id: gi0/1
        state: up
links:
  - source: { node: r1, interface: gi0/1 }
    target: { node: r2, interface: gi0/1 }
    label: "uplink"
```

`tests/fixtures/branch_office.yaml`:

```yaml
version: "1.0"
metadata:
  title: "Branch Office Topology"
  type: physical
groups:
  - id: server-vlan
    label: "VLAN 100 - Servers"
    type: subnet
nodes:
  - id: fw1
    label: fw1
    type: firewall
    interfaces:
      - id: eth0
        state: up
      - id: eth1
        state: up
  - id: core-sw1
    label: core-sw1
    type: switch
    group: server-vlan
    interfaces:
      - id: gi0/1
        state: up
      - id: gi0/2
        state: up
  - id: srv1
    label: srv1
    type: server
    group: server-vlan
    interfaces:
      - id: eth0
        state: up
links:
  - source: { node: fw1, interface: eth1 }
    target: { node: core-sw1, interface: gi0/1 }
    label: "Trunk"
  - source: { node: core-sw1, interface: gi0/2 }
    target: { node: srv1, interface: eth0 }
```

`tests/fixtures/invalid_missing_node.yaml`:

```yaml
version: "1.0"
metadata:
  title: "Invalid - link to missing node"
  type: physical
nodes:
  - id: a
    label: a
    type: router
links:
  - source: { node: a }
    target: { node: ghost }
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_ir_loader.py`:

```python
import pytest

from netdiagram.ir import Diagram
from netdiagram.ir.loader import LoaderError, load_diagram


def test_load_simple_yaml(fixtures_dir):
    d = load_diagram(fixtures_dir / "simple_two_nodes.yaml")
    assert isinstance(d, Diagram)
    assert len(d.nodes) == 2
    assert len(d.links) == 1


def test_load_branch_office(fixtures_dir):
    d = load_diagram(fixtures_dir / "branch_office.yaml")
    assert len(d.groups) == 1
    assert d.groups[0].id == "server-vlan"
    assert {n.id for n in d.nodes} == {"fw1", "core-sw1", "srv1"}


def test_missing_file_raises(tmp_path):
    with pytest.raises(LoaderError, match="file not found"):
        load_diagram(tmp_path / "nope.yaml")


def test_invalid_yaml_syntax_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: valid: yaml: here: [\n")
    with pytest.raises(LoaderError, match="YAML parse error"):
        load_diagram(bad)


def test_validation_error_includes_context(fixtures_dir):
    with pytest.raises(LoaderError) as exc:
        load_diagram(fixtures_dir / "invalid_missing_node.yaml")
    msg = str(exc.value)
    assert "invalid_missing_node.yaml" in msg
    assert "unknown node 'ghost'" in msg


def test_load_json(tmp_path):
    j = tmp_path / "d.json"
    j.write_text(
        '{"version": "1.0", "metadata": {"title":"J","type":"physical"},'
        ' "nodes":[{"id":"a","label":"a","type":"router"}]}'
    )
    d = load_diagram(j)
    assert d.nodes[0].id == "a"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_ir_loader.py -v`
Expected: ImportError — `netdiagram.ir.loader` does not exist.

- [ ] **Step 4: Implement the loader**

Create `src/netdiagram/ir/loader.py`:

```python
"""Load and validate diagram IR from YAML or JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from netdiagram.ir.models import Diagram


class LoaderError(Exception):
    """Raised when a diagram cannot be loaded or validated."""


def load_diagram(path: str | Path) -> Diagram:
    """Load a diagram IR from a YAML or JSON file. Raises LoaderError on any failure."""
    p = Path(path)
    if not p.exists():
        raise LoaderError(f"file not found: {p}")

    raw = p.read_text(encoding="utf-8")

    try:
        data = _parse(raw, p.suffix.lower())
    except yaml.YAMLError as e:
        raise LoaderError(f"YAML parse error in {p}: {e}") from e
    except json.JSONDecodeError as e:
        raise LoaderError(f"JSON parse error in {p}: {e}") from e

    try:
        return Diagram.model_validate(data)
    except ValidationError as e:
        raise LoaderError(_format_validation_error(p, e)) from e


def _parse(raw: str, suffix: str) -> Any:
    if suffix == ".json":
        return json.loads(raw)
    # Default to YAML for .yaml, .yml, or unknown extensions
    return yaml.safe_load(raw)


def _format_validation_error(path: Path, err: ValidationError) -> str:
    lines = [f"validation errors in {path}:"]
    for e in err.errors():
        loc = ".".join(str(x) for x in e["loc"]) or "<root>"
        lines.append(f"  {loc}: {e['msg']}")
    return "\n".join(lines)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_ir_loader.py -v`
Expected: all 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/ir/loader.py tests/test_ir_loader.py tests/fixtures/
git commit -m "feat(ir): YAML/JSON loader with formatted validation errors"
```

---

## Task 4: JSON Schema Export

**Files:**
- Create: `src/netdiagram/ir/schema.py`
- Test: `tests/test_ir_schema.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ir_schema.py`:

```python
import json

from netdiagram.ir.schema import diagram_json_schema


def test_schema_is_valid_json_schema():
    s = diagram_json_schema()
    assert s["$schema"].startswith("https://json-schema.org/")
    assert s["title"] == "Diagram"
    assert "properties" in s
    assert "nodes" in s["properties"]


def test_schema_includes_node_types_enum():
    s = diagram_json_schema()
    # Navigate to Node.type enum — Pydantic generates $defs with refs
    node_def = s["$defs"]["Node"]
    type_prop = node_def["properties"]["type"]
    assert "router" in type_prop["enum"]
    assert "vpc" in type_prop["enum"]


def test_schema_serializable():
    s = diagram_json_schema()
    # Must round-trip through JSON without loss
    json.dumps(s)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ir_schema.py -v`
Expected: ImportError on `netdiagram.ir.schema`.

- [ ] **Step 3: Implement schema export**

Create `src/netdiagram/ir/schema.py`:

```python
"""JSON Schema generation for the Diagram IR."""

from __future__ import annotations

from typing import Any

from netdiagram.ir.models import Diagram


def diagram_json_schema() -> dict[str, Any]:
    """Return a JSON Schema (draft 2020-12) for the Diagram IR."""
    schema = Diagram.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Diagram"
    return schema
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ir_schema.py -v`
Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/ir/schema.py tests/test_ir_schema.py
git commit -m "feat(ir): JSON Schema export for LLM consumption"
```

---

## Task 5: Layout Types & Renderer Base

**Files:**
- Create: `src/netdiagram/layout/__init__.py`
- Create: `src/netdiagram/layout/types.py`
- Create: `src/netdiagram/renderers/__init__.py`
- Create: `src/netdiagram/renderers/base.py`

No dedicated tests — this task only defines types; behavior tests come with the consumers (Tasks 6-14).

- [ ] **Step 1: Create `src/netdiagram/layout/types.py`**

```python
"""Layout output types shared between the layout engine and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field

from netdiagram.ir.models import Diagram, Group, Link, Node


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass
class PositionedNode:
    node: Node
    x: float
    y: float
    width: float
    height: float


@dataclass
class PositionedGroup:
    group: Group
    x: float
    y: float
    width: float
    height: float


@dataclass
class RoutedEdge:
    link: Link
    path: list[Point]  # Start, optional waypoints, end. Phase 1: just [start, end].
    source_label_pos: Point | None = None
    target_label_pos: Point | None = None


@dataclass
class LayoutedDiagram:
    diagram: Diagram
    nodes: list[PositionedNode] = field(default_factory=list)
    groups: list[PositionedGroup] = field(default_factory=list)
    edges: list[RoutedEdge] = field(default_factory=list)
    canvas_width: float = 0.0
    canvas_height: float = 0.0

    def node_by_id(self, nid: str) -> PositionedNode:
        for pn in self.nodes:
            if pn.node.id == nid:
                return pn
        raise KeyError(nid)
```

- [ ] **Step 2: Create `src/netdiagram/layout/__init__.py`**

```python
from netdiagram.layout.types import (
    LayoutedDiagram,
    Point,
    PositionedGroup,
    PositionedNode,
    RoutedEdge,
)

__all__ = [
    "LayoutedDiagram",
    "Point",
    "PositionedGroup",
    "PositionedNode",
    "RoutedEdge",
]
```

- [ ] **Step 3: Create `src/netdiagram/renderers/base.py`**

```python
"""Base protocol for diagram renderers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from netdiagram.layout.types import LayoutedDiagram


@runtime_checkable
class Renderer(Protocol):
    format: str
    extension: str

    def render(self, diagram: LayoutedDiagram) -> str:
        """Render the laid-out diagram to the target format as a string."""
        ...
```

- [ ] **Step 4: Create `src/netdiagram/renderers/__init__.py`**

```python
from netdiagram.renderers.base import Renderer

__all__ = ["Renderer"]
```

- [ ] **Step 5: Smoke test the imports**

Run: `uv run python -c "from netdiagram.layout import LayoutedDiagram; from netdiagram.renderers import Renderer; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/layout/ src/netdiagram/renderers/
git commit -m "feat: layout types and renderer protocol"
```

---

## Task 6: Layout — Node Dimensions

**Files:**
- Create: `src/netdiagram/layout/dimensions.py`
- Test: `tests/test_layout_dimensions.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_layout_dimensions.py`:

```python
from netdiagram.ir.models import Node
from netdiagram.layout.dimensions import compute_node_size


def test_default_size_for_short_label():
    n = Node(id="r1", label="r1", type="router")
    w, h = compute_node_size(n)
    assert w >= 80
    assert h >= 60


def test_wider_for_longer_labels():
    short = compute_node_size(Node(id="a", label="a", type="router"))
    long_ = compute_node_size(
        Node(id="b", label="very-long-hostname-device-1", type="router")
    )
    assert long_[0] > short[0]


def test_firewall_minimum_size():
    n = Node(id="fw", label="fw", type="firewall")
    w, h = compute_node_size(n)
    # Firewalls use a slightly larger default for icon visibility
    assert w >= 100
    assert h >= 70


def test_label_with_unicode():
    # Ensure len-based sizing doesn't crash on non-ASCII
    n = Node(id="x", label="café-01", type="switch")
    w, h = compute_node_size(n)
    assert w > 0 and h > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_layout_dimensions.py -v`
Expected: ImportError on `netdiagram.layout.dimensions`.

- [ ] **Step 3: Implement dimension computation**

Create `src/netdiagram/layout/dimensions.py`:

```python
"""Compute rendered dimensions for nodes based on label and type.

Returns pixel sizes that downstream renderers can use directly. The numbers
are calibrated for Draw.io's default font (Helvetica 12pt) — other renderers
may scale as needed.
"""

from __future__ import annotations

from netdiagram.ir.models import Node

# Approximate pixel width per character at 12pt Helvetica.
_CHAR_WIDTH_PX = 7.0
_LABEL_PADDING_PX = 24.0
_MIN_WIDTH_PX = 80.0
_MIN_HEIGHT_PX = 60.0

# Types that want a slightly larger default so icons read clearly.
_LARGE_TYPES = {"firewall", "load_balancer", "cloud_lb", "cloud_db"}


def compute_node_size(node: Node) -> tuple[float, float]:
    label_width = len(node.label) * _CHAR_WIDTH_PX + _LABEL_PADDING_PX
    min_w = 100.0 if node.type in _LARGE_TYPES else _MIN_WIDTH_PX
    min_h = 70.0 if node.type in _LARGE_TYPES else _MIN_HEIGHT_PX
    return max(min_w, label_width), min_h
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_layout_dimensions.py -v`
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/layout/dimensions.py tests/test_layout_dimensions.py
git commit -m "feat(layout): compute node dimensions from label and type"
```

---

## Task 7: Layout — Topology Classification

**Files:**
- Create: `src/netdiagram/layout/topology.py`
- Test: `tests/test_layout_topology.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_layout_topology.py`:

```python
import networkx as nx

from netdiagram.layout.topology import TopologyShape, classify_topology


def _graph(edges: list[tuple[str, str]], nodes: list[str] | None = None) -> nx.Graph:
    g = nx.Graph()
    if nodes:
        g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    return g


def test_single_node_is_trivial():
    g = _graph([], nodes=["a"])
    assert classify_topology(g) == TopologyShape.TRIVIAL


def test_tree_detected():
    # a-b, b-c, b-d (no cycles)
    g = _graph([("a", "b"), ("b", "c"), ("b", "d")])
    assert classify_topology(g) == TopologyShape.TREE


def test_star_detected():
    # one hub, many leaves
    g = _graph([("hub", "a"), ("hub", "b"), ("hub", "c"), ("hub", "d")])
    assert classify_topology(g) == TopologyShape.STAR


def test_ring_detected():
    g = _graph([("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")])
    assert classify_topology(g) == TopologyShape.RING


def test_mesh_detected():
    # Every node connected to every other (K4)
    nodes = ["a", "b", "c", "d"]
    edges = [(u, v) for i, u in enumerate(nodes) for v in nodes[i + 1 :]]
    assert classify_topology(_graph(edges)) == TopologyShape.MESH


def test_hierarchical_fallback():
    # A graph with cycles that isn't a ring/star/mesh
    g = _graph(
        [("core", "dist1"), ("core", "dist2"), ("dist1", "acc1"),
         ("dist1", "acc2"), ("dist2", "acc3"), ("acc1", "acc2")]
    )
    assert classify_topology(g) == TopologyShape.HIERARCHICAL
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_layout_topology.py -v`
Expected: ImportError on `netdiagram.layout.topology`.

- [ ] **Step 3: Implement classification**

Create `src/netdiagram/layout/topology.py`:

```python
"""Classify an undirected network topology to pick a layout algorithm."""

from __future__ import annotations

from enum import Enum

import networkx as nx


class TopologyShape(str, Enum):
    TRIVIAL = "trivial"        # 0 or 1 node
    TREE = "tree"              # acyclic, connected
    STAR = "star"              # one hub connected to all leaves
    RING = "ring"              # single cycle through all nodes
    MESH = "mesh"              # every node connected to every other
    HIERARCHICAL = "hierarchical"  # default fallback for anything else


def classify_topology(g: nx.Graph) -> TopologyShape:
    n = g.number_of_nodes()
    if n <= 1:
        return TopologyShape.TRIVIAL

    m = g.number_of_edges()

    # Star: one vertex of degree n-1, all others degree 1
    degrees = sorted(d for _, d in g.degree())
    if degrees[-1] == n - 1 and all(d == 1 for d in degrees[:-1]):
        return TopologyShape.STAR

    # Tree: connected, m == n - 1
    if nx.is_connected(g) and m == n - 1:
        return TopologyShape.TREE

    # Ring: connected, every node degree 2, m == n
    if nx.is_connected(g) and m == n and all(d == 2 for _, d in g.degree()):
        return TopologyShape.RING

    # Mesh: complete graph
    if m == n * (n - 1) // 2:
        return TopologyShape.MESH

    return TopologyShape.HIERARCHICAL
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_layout_topology.py -v`
Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/layout/topology.py tests/test_layout_topology.py
git commit -m "feat(layout): topology classification (tree, star, ring, mesh, hierarchical)"
```

---

## Task 8: Layout — Initial Placement via Graphviz

**Files:**
- Create: `src/netdiagram/layout/placement.py`
- Test: `tests/test_layout_placement.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_layout_placement.py`:

```python
import networkx as nx

from netdiagram.layout.placement import compute_initial_positions
from netdiagram.layout.topology import TopologyShape


def test_returns_position_for_each_node():
    g = nx.Graph()
    g.add_edges_from([("a", "b"), ("b", "c"), ("b", "d")])
    positions = compute_initial_positions(g, TopologyShape.TREE)
    assert set(positions.keys()) == {"a", "b", "c", "d"}
    for x, y in positions.values():
        assert isinstance(x, float)
        assert isinstance(y, float)


def test_single_node_position():
    g = nx.Graph()
    g.add_node("only")
    positions = compute_initial_positions(g, TopologyShape.TRIVIAL)
    assert positions == {"only": (0.0, 0.0)}


def test_ring_positions_are_circular():
    # All nodes should lie roughly on a circle (equal distance from centroid)
    g = nx.Graph()
    nodes = ["a", "b", "c", "d", "e"]
    g.add_edges_from([(nodes[i], nodes[(i + 1) % 5]) for i in range(5)])
    positions = compute_initial_positions(g, TopologyShape.RING)
    cx = sum(x for x, _ in positions.values()) / 5
    cy = sum(y for _, y in positions.values()) / 5
    distances = [((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in positions.values()]
    avg = sum(distances) / len(distances)
    for d in distances:
        assert abs(d - avg) / avg < 0.05  # within 5% of the mean radius
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_layout_placement.py -v`
Expected: ImportError on `netdiagram.layout.placement`.

- [ ] **Step 3: Implement placement**

Create `src/netdiagram/layout/placement.py`:

```python
"""Compute initial 2D coordinates for nodes given the topology shape."""

from __future__ import annotations

import math

import networkx as nx

from netdiagram.layout.topology import TopologyShape

# Algorithm selection per topology. Graphviz engines:
#   dot   -> hierarchical (best for trees, hierarchies)
#   neato -> force-directed (general)
#   twopi -> radial (good for stars)
#   circo -> circular (not always round for rings)
_ENGINE_BY_SHAPE = {
    TopologyShape.TREE: "dot",
    TopologyShape.STAR: "twopi",
    TopologyShape.HIERARCHICAL: "dot",
    TopologyShape.MESH: "neato",
}


def compute_initial_positions(
    g: nx.Graph, shape: TopologyShape
) -> dict[str, tuple[float, float]]:
    """Return a mapping of node id -> (x, y) coordinates."""
    if shape is TopologyShape.TRIVIAL:
        return {n: (0.0, 0.0) for n in g.nodes()}

    if shape is TopologyShape.RING:
        return _ring_positions(g)

    engine = _ENGINE_BY_SHAPE.get(shape, "dot")
    return _graphviz_positions(g, engine)


def _ring_positions(g: nx.Graph) -> dict[str, tuple[float, float]]:
    # Walk the single cycle to order the nodes, then place around a circle.
    nodes = list(g.nodes())
    ordered = _walk_ring(g, nodes[0])
    n = len(ordered)
    radius = max(120.0, n * 40.0)
    out: dict[str, tuple[float, float]] = {}
    for i, nid in enumerate(ordered):
        angle = 2 * math.pi * i / n
        out[nid] = (radius * math.cos(angle), radius * math.sin(angle))
    return out


def _walk_ring(g: nx.Graph, start: str) -> list[str]:
    ordered = [start]
    prev: str | None = None
    cur = start
    while True:
        neighbors = [n for n in g.neighbors(cur) if n != prev]
        if not neighbors:
            break
        nxt = neighbors[0]
        if nxt == start:
            break
        ordered.append(nxt)
        prev, cur = cur, nxt
    return ordered


def _graphviz_positions(g: nx.Graph, engine: str) -> dict[str, tuple[float, float]]:
    # Use networkx's graphviz_layout helper (requires pygraphviz).
    # Graphviz returns coordinates in points; we scale to pixels (1 pt = 1 px
    # is fine for our purposes — the overlap pass will re-space as needed).
    from networkx.drawing.nx_agraph import graphviz_layout

    pos = graphviz_layout(g, prog=engine)
    return {n: (float(x), float(y)) for n, (x, y) in pos.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_layout_placement.py -v`
Expected: all 3 tests pass. If graphviz_layout fails due to missing system graphviz, fix the install (see README).

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/layout/placement.py tests/test_layout_placement.py
git commit -m "feat(layout): initial placement via graphviz + ring layout"
```

---

## Task 9: Layout — Overlap Resolution

**Files:**
- Create: `src/netdiagram/layout/overlap.py`
- Test: `tests/test_layout_overlap.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_layout_overlap.py`:

```python
from netdiagram.ir.models import Node
from netdiagram.layout.overlap import resolve_overlaps
from netdiagram.layout.types import PositionedNode


def _pn(nid: str, x: float, y: float, w: float = 100, h: float = 60) -> PositionedNode:
    return PositionedNode(
        node=Node(id=nid, label=nid, type="router"), x=x, y=y, width=w, height=h
    )


def _overlap(a: PositionedNode, b: PositionedNode) -> bool:
    return not (
        a.x + a.width <= b.x
        or b.x + b.width <= a.x
        or a.y + a.height <= b.y
        or b.y + b.height <= a.y
    )


def test_no_overlap_unchanged():
    nodes = [_pn("a", 0, 0), _pn("b", 200, 0)]
    resolved = resolve_overlaps(nodes, padding=10)
    # Coordinates should be identical
    assert resolved[0].x == 0 and resolved[0].y == 0
    assert resolved[1].x == 200 and resolved[1].y == 0


def test_two_overlapping_nodes_separated():
    nodes = [_pn("a", 0, 0), _pn("b", 20, 20)]
    resolved = resolve_overlaps(nodes, padding=10)
    assert not _overlap(resolved[0], resolved[1])


def test_chain_of_overlaps_resolves():
    nodes = [_pn(f"n{i}", i * 5, 0) for i in range(5)]
    resolved = resolve_overlaps(nodes, padding=5)
    for i in range(len(resolved)):
        for j in range(i + 1, len(resolved)):
            assert not _overlap(resolved[i], resolved[j]), f"{i} overlaps {j}"


def test_padding_enforced():
    nodes = [_pn("a", 0, 0), _pn("b", 20, 0)]
    resolved = resolve_overlaps(nodes, padding=30)
    # Horizontal gap between rightmost of first and leftmost of second >= 30
    a, b = sorted(resolved, key=lambda p: p.x)
    gap = b.x - (a.x + a.width)
    assert gap >= 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_layout_overlap.py -v`
Expected: ImportError on `netdiagram.layout.overlap`.

- [ ] **Step 3: Implement overlap resolution**

Create `src/netdiagram/layout/overlap.py`:

```python
"""Resolve node overlaps by iteratively pushing colliding nodes apart.

Algorithm: a simplified version of Dwyer's scan-line approach. For each pair
of overlapping rectangles, compute the minimum translation vector along the
axis of least penetration and apply half the displacement to each node. Iterate
until no overlaps remain or a max iteration cap is hit.
"""

from __future__ import annotations

from netdiagram.layout.types import PositionedNode

_MAX_ITERATIONS = 200


def resolve_overlaps(
    nodes: list[PositionedNode], padding: float = 10.0
) -> list[PositionedNode]:
    """Return a new list of PositionedNode with overlaps resolved."""
    # Work on mutable copies (dataclass is mutable by default here).
    work = [
        PositionedNode(node=pn.node, x=pn.x, y=pn.y, width=pn.width, height=pn.height)
        for pn in nodes
    ]

    for _ in range(_MAX_ITERATIONS):
        moved = False
        for i in range(len(work)):
            for j in range(i + 1, len(work)):
                if _push_apart(work[i], work[j], padding):
                    moved = True
        if not moved:
            break
    return work


def _push_apart(a: PositionedNode, b: PositionedNode, padding: float) -> bool:
    """If a and b overlap (including padding), move each by half the MTV.
    Returns True if a push happened.
    """
    a_right, a_bottom = a.x + a.width, a.y + a.height
    b_right, b_bottom = b.x + b.width, b.y + b.height

    overlap_x = min(a_right, b_right) - max(a.x, b.x) + padding
    overlap_y = min(a_bottom, b_bottom) - max(a.y, b.y) + padding

    if overlap_x <= 0 or overlap_y <= 0:
        return False

    # Push along the axis of least penetration.
    if overlap_x < overlap_y:
        dx = overlap_x / 2
        if a.x < b.x:
            a.x -= dx
            b.x += dx
        else:
            a.x += dx
            b.x -= dx
    else:
        dy = overlap_y / 2
        if a.y < b.y:
            a.y -= dy
            b.y += dy
        else:
            a.y += dy
            b.y -= dy
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_layout_overlap.py -v`
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/layout/overlap.py tests/test_layout_overlap.py
git commit -m "feat(layout): iterative overlap resolution with padding"
```

---

## Task 10: Layout Engine Pipeline

**Files:**
- Create: `src/netdiagram/layout/engine.py`
- Test: `tests/test_layout_engine.py`
- Modify: `src/netdiagram/layout/__init__.py` (add `layout_diagram` export)

- [ ] **Step 1: Write failing tests**

Create `tests/test_layout_engine.py`:

```python
from netdiagram.ir.models import Diagram, Interface, Link, LinkEndpoint, Metadata, Node
from netdiagram.layout.engine import layout_diagram


def _simple_diagram() -> Diagram:
    return Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router", interfaces=[Interface(id="e0")]),
            Node(id="b", label="b", type="router", interfaces=[Interface(id="e0")]),
            Node(id="c", label="c", type="router", interfaces=[Interface(id="e0")]),
        ],
        links=[
            Link(source=LinkEndpoint(node="a", interface="e0"),
                 target=LinkEndpoint(node="b", interface="e0")),
            Link(source=LinkEndpoint(node="b", interface="e0"),
                 target=LinkEndpoint(node="c", interface="e0")),
        ],
    )


def test_layout_produces_position_for_every_node():
    d = _simple_diagram()
    laid = layout_diagram(d)
    assert {pn.node.id for pn in laid.nodes} == {"a", "b", "c"}


def test_layout_produces_edge_for_every_link():
    d = _simple_diagram()
    laid = layout_diagram(d)
    assert len(laid.edges) == 2
    for edge in laid.edges:
        assert len(edge.path) >= 2  # at least start and end


def test_layout_no_node_overlaps():
    d = _simple_diagram()
    laid = layout_diagram(d)
    nodes = laid.nodes
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            overlap_x = (a.x + a.width > b.x) and (b.x + b.width > a.x)
            overlap_y = (a.y + a.height > b.y) and (b.y + b.height > a.y)
            assert not (overlap_x and overlap_y), f"{a.node.id} overlaps {b.node.id}"


def test_canvas_encloses_all_nodes():
    d = _simple_diagram()
    laid = layout_diagram(d)
    for pn in laid.nodes:
        assert pn.x >= 0
        assert pn.y >= 0
        assert pn.x + pn.width <= laid.canvas_width
        assert pn.y + pn.height <= laid.canvas_height


def test_single_node_diagram_lays_out():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="only", label="only", type="server")],
    )
    laid = layout_diagram(d)
    assert len(laid.nodes) == 1
    assert laid.canvas_width > 0 and laid.canvas_height > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_layout_engine.py -v`
Expected: ImportError on `netdiagram.layout.engine`.

- [ ] **Step 3: Implement the engine**

Create `src/netdiagram/layout/engine.py`:

```python
"""Top-level layout pipeline.

Pipeline stages:
1. Build a networkx graph from the IR.
2. Classify the topology to pick a layout algorithm.
3. Compute initial coordinates.
4. Compute node dimensions.
5. Resolve node overlaps.
6. Normalize coordinates so the canvas origin is (0, 0) with margin.
7. Route edges as straight line segments between node centers (Phase 1).
"""

from __future__ import annotations

import networkx as nx

from netdiagram.ir.models import Diagram
from netdiagram.layout.dimensions import compute_node_size
from netdiagram.layout.overlap import resolve_overlaps
from netdiagram.layout.placement import compute_initial_positions
from netdiagram.layout.topology import classify_topology
from netdiagram.layout.types import LayoutedDiagram, Point, PositionedNode, RoutedEdge

_MARGIN = 40.0
_NODE_PADDING = 20.0


def layout_diagram(diagram: Diagram) -> LayoutedDiagram:
    g = _build_graph(diagram)
    shape = classify_topology(g)
    raw_positions = compute_initial_positions(g, shape)

    # Create PositionedNode objects with real dimensions.
    positioned: list[PositionedNode] = []
    for node in diagram.nodes:
        x, y = raw_positions.get(node.id, (0.0, 0.0))
        w, h = compute_node_size(node)
        # Graphviz coords reference node centers; convert to top-left.
        positioned.append(PositionedNode(node=node, x=x - w / 2, y=y - h / 2, width=w, height=h))

    positioned = resolve_overlaps(positioned, padding=_NODE_PADDING)

    # Normalize so the minimum x/y is at `_MARGIN`.
    positioned = _normalize(positioned, margin=_MARGIN)

    canvas_w, canvas_h = _canvas_bounds(positioned, margin=_MARGIN)

    laid = LayoutedDiagram(
        diagram=diagram, nodes=positioned, canvas_width=canvas_w, canvas_height=canvas_h
    )
    laid.edges = _route_edges(diagram, laid)
    return laid


def _build_graph(diagram: Diagram) -> nx.Graph:
    g = nx.Graph()
    for n in diagram.nodes:
        g.add_node(n.id)
    for link in diagram.links:
        g.add_edge(link.source.node, link.target.node)
    return g


def _normalize(nodes: list[PositionedNode], margin: float) -> list[PositionedNode]:
    if not nodes:
        return nodes
    min_x = min(pn.x for pn in nodes)
    min_y = min(pn.y for pn in nodes)
    dx = margin - min_x
    dy = margin - min_y
    for pn in nodes:
        pn.x += dx
        pn.y += dy
    return nodes


def _canvas_bounds(nodes: list[PositionedNode], margin: float) -> tuple[float, float]:
    if not nodes:
        return (2 * margin, 2 * margin)
    max_x = max(pn.x + pn.width for pn in nodes)
    max_y = max(pn.y + pn.height for pn in nodes)
    return (max_x + margin, max_y + margin)


def _route_edges(diagram: Diagram, laid: LayoutedDiagram) -> list[RoutedEdge]:
    """Phase 1: straight-line edges between node centers."""
    by_id = {pn.node.id: pn for pn in laid.nodes}
    out: list[RoutedEdge] = []
    for link in diagram.links:
        s = by_id[link.source.node]
        t = by_id[link.target.node]
        start = Point(s.x + s.width / 2, s.y + s.height / 2)
        end = Point(t.x + t.width / 2, t.y + t.height / 2)
        out.append(RoutedEdge(link=link, path=[start, end]))
    return out
```

- [ ] **Step 4: Update `src/netdiagram/layout/__init__.py`**

Append to the existing file:

```python
from netdiagram.layout.engine import layout_diagram

__all__ += ["layout_diagram"]
```

The complete file should now read:

```python
from netdiagram.layout.engine import layout_diagram
from netdiagram.layout.types import (
    LayoutedDiagram,
    Point,
    PositionedGroup,
    PositionedNode,
    RoutedEdge,
)

__all__ = [
    "LayoutedDiagram",
    "Point",
    "PositionedGroup",
    "PositionedNode",
    "RoutedEdge",
    "layout_diagram",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_layout_engine.py -v`
Expected: all 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/layout/engine.py src/netdiagram/layout/__init__.py tests/test_layout_engine.py
git commit -m "feat(layout): end-to-end layout pipeline (classify -> place -> resolve -> route)"
```

---

## Task 11: Draw.io Renderer — Nodes

**Files:**
- Create: `src/netdiagram/renderers/drawio.py`
- Modify: `src/netdiagram/renderers/__init__.py`
- Test: `tests/test_renderer_drawio.py`

This task covers nodes only. Edges come in Task 12, groups in Task 13.

- [ ] **Step 1: Write failing tests**

Create `tests/test_renderer_drawio.py`:

```python
from lxml import etree

from netdiagram.ir.models import Diagram, Metadata, Node
from netdiagram.layout import layout_diagram
from netdiagram.renderers.drawio import DrawioRenderer


def _render(diagram: Diagram) -> str:
    return DrawioRenderer().render(layout_diagram(diagram))


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(xml.encode("utf-8"))


def test_renders_valid_drawio_xml():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="a", label="a", type="router")],
    )
    xml = _render(d)
    root = _parse(xml)
    assert root.tag == "mxfile"
    # Must contain a diagram element
    assert root.find("diagram") is not None


def test_each_node_becomes_mxcell():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="switch"),
        ],
    )
    root = _parse(_render(d))
    cells = root.findall(".//mxCell")
    node_cells = [c for c in cells if c.get("vertex") == "1"]
    assert len(node_cells) == 2
    values = {c.get("value") for c in node_cells}
    assert values == {"a", "b"}


def test_node_type_determines_shape_style():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="r1", label="r1", type="router")],
    )
    root = _parse(_render(d))
    cell = next(c for c in root.findall(".//mxCell") if c.get("value") == "r1")
    style = cell.get("style") or ""
    # Style string should include "router" somewhere (via shape= attribute)
    assert "router" in style.lower()


def test_node_geometry_uses_layout_coordinates():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="a", label="a", type="router")],
    )
    root = _parse(_render(d))
    cell = next(c for c in root.findall(".//mxCell") if c.get("value") == "a")
    geom = cell.find("mxGeometry")
    assert geom is not None
    assert float(geom.get("width")) > 0
    assert float(geom.get("height")) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_renderer_drawio.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement the renderer (nodes only)**

Create `src/netdiagram/renderers/drawio.py`:

```python
"""Draw.io (mxGraph XML) renderer."""

from __future__ import annotations

from lxml import etree

from netdiagram.ir.models import NodeType
from netdiagram.layout.types import LayoutedDiagram, PositionedNode

# Map IR node types to Draw.io mxGraph style strings. The built-in shape
# libraries we use are `mscae/...` (Microsoft Azure Cloud) and `cisco/...`.
# For generic/unknown types, fall back to a rounded rectangle.
_STYLE_BY_TYPE: dict[NodeType, str] = {
    "router": "shape=mscae/router;html=1;whiteSpace=wrap;fillColor=#1B5E9E;fontColor=#FFFFFF;",
    "switch": "shape=mscae/switch;html=1;whiteSpace=wrap;fillColor=#0072C6;fontColor=#FFFFFF;",
    "firewall": "shape=cisco/firewall;html=1;whiteSpace=wrap;fillColor=#B0343C;fontColor=#FFFFFF;",
    "server": "shape=mscae/server;html=1;whiteSpace=wrap;fillColor=#5C8A3F;fontColor=#FFFFFF;",
    "load_balancer": "shape=mscae/load_balancer;html=1;whiteSpace=wrap;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "access_point": "shape=mscae/wireless_ap;html=1;whiteSpace=wrap;fillColor=#2C7873;fontColor=#FFFFFF;",
    "endpoint": "shape=mscae/workstation;html=1;whiteSpace=wrap;fillColor=#7A7A7A;fontColor=#FFFFFF;",
    "vpc": "shape=mscae/cloud;html=1;whiteSpace=wrap;fillColor=#D3E6F1;fontColor=#000000;",
    "cloud_lb": "shape=mscae/load_balancer;html=1;whiteSpace=wrap;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "cloud_db": "shape=mscae/database;html=1;whiteSpace=wrap;fillColor=#A44E8A;fontColor=#FFFFFF;",
    "internet_gateway": "shape=mscae/internet;html=1;whiteSpace=wrap;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "nat_gateway": "shape=mscae/nat_gateway;html=1;whiteSpace=wrap;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "security_group": "shape=mscae/security;html=1;whiteSpace=wrap;fillColor=#B0343C;fontColor=#FFFFFF;",
    "generic": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8E8E8;",
}


class DrawioRenderer:
    format = "drawio"
    extension = ".drawio"

    def render(self, diagram: LayoutedDiagram) -> str:
        mxfile = etree.Element("mxfile", host="netdiagram")
        dia = etree.SubElement(
            mxfile, "diagram", id="main", name=diagram.diagram.metadata.title
        )
        model = etree.SubElement(
            dia,
            "mxGraphModel",
            dx=str(int(diagram.canvas_width)),
            dy=str(int(diagram.canvas_height)),
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(int(diagram.canvas_width)),
            pageHeight=str(int(diagram.canvas_height)),
            math="0",
            shadow="0",
        )
        root = etree.SubElement(model, "root")
        # Draw.io requires two reserved cells with ids "0" and "1".
        etree.SubElement(root, "mxCell", id="0")
        etree.SubElement(root, "mxCell", id="1", parent="0")

        for pn in diagram.nodes:
            self._append_node(root, pn)

        # Indent for readability; this is not required by Draw.io but helps diffs.
        etree.indent(mxfile, space="  ")
        return etree.tostring(mxfile, xml_declaration=True, encoding="utf-8").decode("utf-8")

    def _append_node(self, root: etree._Element, pn: PositionedNode) -> None:
        style = _STYLE_BY_TYPE.get(pn.node.type, _STYLE_BY_TYPE["generic"])
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"node-{pn.node.id}",
            value=pn.node.label,
            style=style,
            vertex="1",
            parent="1",
        )
        etree.SubElement(
            cell,
            "mxGeometry",
            x=str(pn.x),
            y=str(pn.y),
            width=str(pn.width),
            height=str(pn.height),
        )
        cell.find("mxGeometry").set("as", "geometry")
```

- [ ] **Step 4: Update `src/netdiagram/renderers/__init__.py`**

```python
from netdiagram.renderers.base import Renderer
from netdiagram.renderers.drawio import DrawioRenderer

__all__ = ["Renderer", "DrawioRenderer"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_renderer_drawio.py -v`
Expected: all 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/renderers/drawio.py src/netdiagram/renderers/__init__.py tests/test_renderer_drawio.py
git commit -m "feat(renderer): Draw.io XML output for nodes with type-based shapes"
```

---

## Task 12: Draw.io Renderer — Edges with Interface Labels

**Files:**
- Modify: `src/netdiagram/renderers/drawio.py` (add edge rendering)
- Modify: `tests/test_renderer_drawio.py` (add edge tests)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_renderer_drawio.py`:

```python
from netdiagram.ir.models import Interface, Link, LinkEndpoint


def test_each_link_becomes_edge_cell():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router", interfaces=[Interface(id="e0")]),
            Node(id="b", label="b", type="router", interfaces=[Interface(id="e0")]),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a", interface="e0"),
                target=LinkEndpoint(node="b", interface="e0"),
                label="uplink",
            )
        ],
    )
    root = _parse(_render(d))
    edges = [c for c in root.findall(".//mxCell") if c.get("edge") == "1"]
    assert len(edges) == 1
    e = edges[0]
    assert e.get("source") == "node-a"
    assert e.get("target") == "node-b"
    assert e.get("value") == "uplink"


def test_edge_has_interface_labels_as_child_cells():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router", interfaces=[Interface(id="gi0/1")]),
            Node(id="b", label="b", type="router", interfaces=[Interface(id="gi0/2")]),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a", interface="gi0/1"),
                target=LinkEndpoint(node="b", interface="gi0/2"),
            )
        ],
    )
    root = _parse(_render(d))
    edge = next(c for c in root.findall(".//mxCell") if c.get("edge") == "1")
    edge_id = edge.get("id")
    # Interface labels are child cells whose parent is the edge
    label_cells = [c for c in root.findall(".//mxCell") if c.get("parent") == edge_id]
    values = {c.get("value") for c in label_cells}
    assert "gi0/1" in values
    assert "gi0/2" in values


def test_edge_style_reflects_link_style():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[
            Link(source=LinkEndpoint(node="a"), target=LinkEndpoint(node="b"), style="dashed")
        ],
    )
    root = _parse(_render(d))
    edge = next(c for c in root.findall(".//mxCell") if c.get("edge") == "1")
    assert "dashed=1" in (edge.get("style") or "")
```

- [ ] **Step 2: Run to confirm new tests fail**

Run: `uv run pytest tests/test_renderer_drawio.py -v`
Expected: the three new tests fail because edges are not yet rendered.

- [ ] **Step 3: Add edge rendering to `DrawioRenderer`**

Modify `src/netdiagram/renderers/drawio.py` — add an edge style map, a counter for edge ids, and a new `_append_edge` method. Replace the full file with:

```python
"""Draw.io (mxGraph XML) renderer."""

from __future__ import annotations

from lxml import etree

from netdiagram.ir.models import LinkStyle, NodeType
from netdiagram.layout.types import LayoutedDiagram, PositionedNode, RoutedEdge

_STYLE_BY_TYPE: dict[NodeType, str] = {
    "router": "shape=mscae/router;html=1;whiteSpace=wrap;fillColor=#1B5E9E;fontColor=#FFFFFF;",
    "switch": "shape=mscae/switch;html=1;whiteSpace=wrap;fillColor=#0072C6;fontColor=#FFFFFF;",
    "firewall": "shape=cisco/firewall;html=1;whiteSpace=wrap;fillColor=#B0343C;fontColor=#FFFFFF;",
    "server": "shape=mscae/server;html=1;whiteSpace=wrap;fillColor=#5C8A3F;fontColor=#FFFFFF;",
    "load_balancer": "shape=mscae/load_balancer;html=1;whiteSpace=wrap;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "access_point": "shape=mscae/wireless_ap;html=1;whiteSpace=wrap;fillColor=#2C7873;fontColor=#FFFFFF;",
    "endpoint": "shape=mscae/workstation;html=1;whiteSpace=wrap;fillColor=#7A7A7A;fontColor=#FFFFFF;",
    "vpc": "shape=mscae/cloud;html=1;whiteSpace=wrap;fillColor=#D3E6F1;fontColor=#000000;",
    "cloud_lb": "shape=mscae/load_balancer;html=1;whiteSpace=wrap;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "cloud_db": "shape=mscae/database;html=1;whiteSpace=wrap;fillColor=#A44E8A;fontColor=#FFFFFF;",
    "internet_gateway": "shape=mscae/internet;html=1;whiteSpace=wrap;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "nat_gateway": "shape=mscae/nat_gateway;html=1;whiteSpace=wrap;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "security_group": "shape=mscae/security;html=1;whiteSpace=wrap;fillColor=#B0343C;fontColor=#FFFFFF;",
    "generic": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8E8E8;",
}

_EDGE_STYLE_BY_LINK_STYLE: dict[LinkStyle, str] = {
    "solid": "endArrow=none;html=1;rounded=0;",
    "dashed": "endArrow=none;html=1;rounded=0;dashed=1;",
    "dotted": "endArrow=none;html=1;rounded=0;dashed=1;dashPattern=1 4;",
}


class DrawioRenderer:
    format = "drawio"
    extension = ".drawio"

    def render(self, diagram: LayoutedDiagram) -> str:
        mxfile = etree.Element("mxfile", host="netdiagram")
        dia = etree.SubElement(
            mxfile, "diagram", id="main", name=diagram.diagram.metadata.title
        )
        model = etree.SubElement(
            dia,
            "mxGraphModel",
            dx=str(int(diagram.canvas_width)),
            dy=str(int(diagram.canvas_height)),
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(int(diagram.canvas_width)),
            pageHeight=str(int(diagram.canvas_height)),
            math="0",
            shadow="0",
        )
        root = etree.SubElement(model, "root")
        etree.SubElement(root, "mxCell", id="0")
        etree.SubElement(root, "mxCell", id="1", parent="0")

        for pn in diagram.nodes:
            self._append_node(root, pn)

        for i, re in enumerate(diagram.edges):
            self._append_edge(root, re, edge_index=i)

        etree.indent(mxfile, space="  ")
        return etree.tostring(mxfile, xml_declaration=True, encoding="utf-8").decode("utf-8")

    def _append_node(self, root: etree._Element, pn: PositionedNode) -> None:
        style = _STYLE_BY_TYPE.get(pn.node.type, _STYLE_BY_TYPE["generic"])
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"node-{pn.node.id}",
            value=pn.node.label,
            style=style,
            vertex="1",
            parent="1",
        )
        geom = etree.SubElement(
            cell,
            "mxGeometry",
            x=str(pn.x),
            y=str(pn.y),
            width=str(pn.width),
            height=str(pn.height),
        )
        geom.set("as", "geometry")

    def _append_edge(self, root: etree._Element, re: RoutedEdge, edge_index: int) -> None:
        edge_id = f"edge-{edge_index}"
        style = _EDGE_STYLE_BY_LINK_STYLE[re.link.style]
        edge_cell = etree.SubElement(
            root,
            "mxCell",
            id=edge_id,
            value=re.link.label or "",
            style=style,
            edge="1",
            parent="1",
            source=f"node-{re.link.source.node}",
            target=f"node-{re.link.target.node}",
        )
        geom = etree.SubElement(edge_cell, "mxGeometry", relative="1")
        geom.set("as", "geometry")

        # Interface labels as child cells anchored to the edge.
        if re.link.source.interface:
            self._append_endpoint_label(
                root, parent_id=edge_id, label=re.link.source.interface, position=-0.7
            )
        if re.link.target.interface:
            self._append_endpoint_label(
                root, parent_id=edge_id, label=re.link.target.interface, position=0.7
            )

    def _append_endpoint_label(
        self, root: etree._Element, parent_id: str, label: str, position: float
    ) -> None:
        # In Draw.io, edge labels are child mxCells with a geometry x in [-1, 1]
        # representing position along the edge (-1 = source, 1 = target).
        cell = etree.SubElement(
            root,
            "mxCell",
            value=label,
            style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];",
            vertex="1",
            connectable="0",
            parent=parent_id,
        )
        geom = etree.SubElement(cell, "mxGeometry", x=str(position), y="0", relative="1")
        etree.SubElement(geom, "mxPoint").set("as", "offset")
        geom.set("as", "geometry")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_renderer_drawio.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/renderers/drawio.py tests/test_renderer_drawio.py
git commit -m "feat(renderer): Draw.io edges with interface labels and link styles"
```

---

## Task 13: Draw.io Renderer — Groups as Containers

**Files:**
- Modify: `src/netdiagram/layout/engine.py` (compute PositionedGroup)
- Modify: `src/netdiagram/renderers/drawio.py` (render groups)
- Modify: `tests/test_layout_engine.py` (add group tests)
- Modify: `tests/test_renderer_drawio.py` (add group rendering tests)

- [ ] **Step 1: Add failing layout test**

Append to `tests/test_layout_engine.py`:

```python
from netdiagram.ir.models import Group


def test_layout_includes_positioned_groups():
    d = Diagram(
        metadata=Metadata(title="T", type="logical"),
        groups=[Group(id="vlan100", label="VLAN 100", type="vlan")],
        nodes=[
            Node(id="sw1", label="sw1", type="switch", group="vlan100"),
            Node(id="sw2", label="sw2", type="switch", group="vlan100"),
        ],
    )
    laid = layout_diagram(d)
    assert len(laid.groups) == 1
    pg = laid.groups[0]
    # Group must enclose all its child nodes
    children = [pn for pn in laid.nodes if pn.node.group == "vlan100"]
    for pn in children:
        assert pn.x >= pg.x
        assert pn.y >= pg.y
        assert pn.x + pn.width <= pg.x + pg.width
        assert pn.y + pn.height <= pg.y + pg.height
```

- [ ] **Step 2: Run to confirm the test fails**

Run: `uv run pytest tests/test_layout_engine.py::test_layout_includes_positioned_groups -v`
Expected: FAIL — groups list is empty.

- [ ] **Step 3: Implement group positioning in the engine**

Modify `src/netdiagram/layout/engine.py`. Two changes:

1. Update the `from netdiagram.layout.types import ...` line to add `PositionedGroup`. The import line should read:

```python
from netdiagram.layout.types import LayoutedDiagram, Point, PositionedGroup, PositionedNode, RoutedEdge
```

2. Replace the body of `layout_diagram` and append new helpers. Delete the old `_canvas_bounds` function (replaced below). The relevant code:

```python


_GROUP_PADDING = 30.0
_GROUP_LABEL_HEIGHT = 28.0


def layout_diagram(diagram: Diagram) -> LayoutedDiagram:
    g = _build_graph(diagram)
    shape = classify_topology(g)
    raw_positions = compute_initial_positions(g, shape)

    positioned: list[PositionedNode] = []
    for node in diagram.nodes:
        x, y = raw_positions.get(node.id, (0.0, 0.0))
        w, h = compute_node_size(node)
        positioned.append(PositionedNode(node=node, x=x - w / 2, y=y - h / 2, width=w, height=h))

    positioned = resolve_overlaps(positioned, padding=_NODE_PADDING)
    positioned = _normalize(positioned, margin=_MARGIN)

    groups = _compute_group_bounds(diagram, positioned)

    canvas_w, canvas_h = _canvas_bounds_with_groups(positioned, groups, margin=_MARGIN)

    laid = LayoutedDiagram(
        diagram=diagram,
        nodes=positioned,
        groups=groups,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
    )
    laid.edges = _route_edges(diagram, laid)
    return laid


def _compute_group_bounds(
    diagram: Diagram, positioned: list[PositionedNode]
) -> list[PositionedGroup]:
    """For each group, compute a bounding rectangle that encloses all its member
    nodes plus a padding allowance and label strip at the top."""
    by_id = {pn.node.id: pn for pn in positioned}
    out: list[PositionedGroup] = []
    for group in diagram.groups:
        members = [by_id[n.id] for n in diagram.nodes if n.group == group.id]
        if not members:
            # Empty group still gets a small placeholder rectangle near origin.
            out.append(
                PositionedGroup(group=group, x=0.0, y=0.0, width=200.0, height=80.0)
            )
            continue
        min_x = min(pn.x for pn in members) - _GROUP_PADDING
        min_y = min(pn.y for pn in members) - _GROUP_PADDING - _GROUP_LABEL_HEIGHT
        max_x = max(pn.x + pn.width for pn in members) + _GROUP_PADDING
        max_y = max(pn.y + pn.height for pn in members) + _GROUP_PADDING
        out.append(
            PositionedGroup(
                group=group, x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y
            )
        )
    return out


def _canvas_bounds_with_groups(
    nodes: list[PositionedNode], groups: list[PositionedGroup], margin: float
) -> tuple[float, float]:
    max_x = margin
    max_y = margin
    for pn in nodes:
        max_x = max(max_x, pn.x + pn.width)
        max_y = max(max_y, pn.y + pn.height)
    for pg in groups:
        max_x = max(max_x, pg.x + pg.width)
        max_y = max(max_y, pg.y + pg.height)
    return (max_x + margin, max_y + margin)
```

Keep `_build_graph`, `_normalize`, `_route_edges` as-is. Delete the old `_canvas_bounds` helper (replaced by `_canvas_bounds_with_groups`).

- [ ] **Step 4: Run layout tests**

Run: `uv run pytest tests/test_layout_engine.py -v`
Expected: all 6 layout tests pass (including the new group test).

- [ ] **Step 5: Add failing renderer test**

Append to `tests/test_renderer_drawio.py`:

```python
from netdiagram.ir.models import Group


def test_groups_rendered_as_container_cells():
    d = Diagram(
        metadata=Metadata(title="T", type="logical"),
        groups=[Group(id="vlan100", label="VLAN 100", type="vlan")],
        nodes=[
            Node(id="sw1", label="sw1", type="switch", group="vlan100"),
            Node(id="sw2", label="sw2", type="switch", group="vlan100"),
        ],
    )
    root = _parse(_render(d))
    group_cells = [c for c in root.findall(".//mxCell") if c.get("id") == "group-vlan100"]
    assert len(group_cells) == 1
    gcell = group_cells[0]
    assert gcell.get("value") == "VLAN 100"
    # Nodes whose IR group is vlan100 must have parent == group-vlan100
    node_cells = {c.get("id"): c for c in root.findall(".//mxCell") if c.get("vertex") == "1"}
    assert node_cells["node-sw1"].get("parent") == "group-vlan100"
    assert node_cells["node-sw2"].get("parent") == "group-vlan100"
```

- [ ] **Step 6: Run to confirm the new test fails**

Run: `uv run pytest tests/test_renderer_drawio.py::test_groups_rendered_as_container_cells -v`
Expected: FAIL — no `group-vlan100` cell is produced yet.

- [ ] **Step 7: Render groups as Draw.io containers**

Modify `src/netdiagram/renderers/drawio.py`. Add a group style constant, update `render()` to emit group cells before nodes, and update `_append_node()` to set `parent` to the group cell id when the node has a group. Replace the class body with:

```python
_GROUP_STYLE_BY_TYPE: dict[str, str] = {
    "subnet": "rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#9E9E9E;verticalAlign=top;fontSize=12;",
    "vlan": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF8E1;strokeColor=#F9A825;verticalAlign=top;fontSize=12;",
    "vpc": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8F5E9;strokeColor=#2E7D32;verticalAlign=top;fontSize=12;",
    "availability_zone": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E3F2FD;strokeColor=#1565C0;verticalAlign=top;fontSize=12;dashed=1;",
    "region": "rounded=1;whiteSpace=wrap;html=1;fillColor=#EDE7F6;strokeColor=#4527A0;verticalAlign=top;fontSize=12;",
    "zone": "rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#9E9E9E;verticalAlign=top;fontSize=12;",
    "dmz": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFEBEE;strokeColor=#C62828;verticalAlign=top;fontSize=12;",
}


class DrawioRenderer:
    format = "drawio"
    extension = ".drawio"

    def render(self, diagram: LayoutedDiagram) -> str:
        mxfile = etree.Element("mxfile", host="netdiagram")
        dia = etree.SubElement(
            mxfile, "diagram", id="main", name=diagram.diagram.metadata.title
        )
        model = etree.SubElement(
            dia,
            "mxGraphModel",
            dx=str(int(diagram.canvas_width)),
            dy=str(int(diagram.canvas_height)),
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(int(diagram.canvas_width)),
            pageHeight=str(int(diagram.canvas_height)),
            math="0",
            shadow="0",
        )
        root = etree.SubElement(model, "root")
        etree.SubElement(root, "mxCell", id="0")
        etree.SubElement(root, "mxCell", id="1", parent="0")

        # Emit groups first (ordered from outermost to innermost so children can reference parents).
        group_ids: set[str] = set()
        for pg in _order_groups(diagram):
            self._append_group(root, pg)
            group_ids.add(pg.group.id)

        for pn in diagram.nodes:
            parent = f"group-{pn.node.group}" if pn.node.group in group_ids else "1"
            self._append_node(root, pn, parent=parent)

        for i, re in enumerate(diagram.edges):
            self._append_edge(root, re, edge_index=i)

        etree.indent(mxfile, space="  ")
        return etree.tostring(mxfile, xml_declaration=True, encoding="utf-8").decode("utf-8")

    def _append_group(self, root: etree._Element, pg) -> None:
        style = _GROUP_STYLE_BY_TYPE.get(pg.group.type, _GROUP_STYLE_BY_TYPE["zone"])
        parent = f"group-{pg.group.parent}" if pg.group.parent else "1"
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"group-{pg.group.id}",
            value=pg.group.label,
            style=style,
            vertex="1",
            parent=parent,
        )
        geom = etree.SubElement(
            cell,
            "mxGeometry",
            x=str(pg.x),
            y=str(pg.y),
            width=str(pg.width),
            height=str(pg.height),
        )
        geom.set("as", "geometry")

    def _append_node(self, root: etree._Element, pn: PositionedNode, parent: str = "1") -> None:
        style = _STYLE_BY_TYPE.get(pn.node.type, _STYLE_BY_TYPE["generic"])
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"node-{pn.node.id}",
            value=pn.node.label,
            style=style,
            vertex="1",
            parent=parent,
        )
        # When nested inside a group, geometry is relative to the group origin.
        if parent.startswith("group-"):
            group_id = parent[len("group-") :]
            pg = next(g for g in root.findall(".//mxCell") if g.get("id") == parent)
            gx = float(pg.find("mxGeometry").get("x"))
            gy = float(pg.find("mxGeometry").get("y"))
            rel_x = pn.x - gx
            rel_y = pn.y - gy
        else:
            rel_x = pn.x
            rel_y = pn.y
        geom = etree.SubElement(
            cell, "mxGeometry", x=str(rel_x), y=str(rel_y), width=str(pn.width), height=str(pn.height)
        )
        geom.set("as", "geometry")

    def _append_edge(self, root: etree._Element, re: RoutedEdge, edge_index: int) -> None:
        edge_id = f"edge-{edge_index}"
        style = _EDGE_STYLE_BY_LINK_STYLE[re.link.style]
        edge_cell = etree.SubElement(
            root,
            "mxCell",
            id=edge_id,
            value=re.link.label or "",
            style=style,
            edge="1",
            parent="1",
            source=f"node-{re.link.source.node}",
            target=f"node-{re.link.target.node}",
        )
        geom = etree.SubElement(edge_cell, "mxGeometry", relative="1")
        geom.set("as", "geometry")

        if re.link.source.interface:
            self._append_endpoint_label(
                root, parent_id=edge_id, label=re.link.source.interface, position=-0.7
            )
        if re.link.target.interface:
            self._append_endpoint_label(
                root, parent_id=edge_id, label=re.link.target.interface, position=0.7
            )

    def _append_endpoint_label(
        self, root: etree._Element, parent_id: str, label: str, position: float
    ) -> None:
        cell = etree.SubElement(
            root,
            "mxCell",
            value=label,
            style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];",
            vertex="1",
            connectable="0",
            parent=parent_id,
        )
        geom = etree.SubElement(cell, "mxGeometry", x=str(position), y="0", relative="1")
        etree.SubElement(geom, "mxPoint").set("as", "offset")
        geom.set("as", "geometry")


def _order_groups(diagram: LayoutedDiagram):
    """Yield PositionedGroup objects ordered outermost-first (parents before children)."""
    by_id = {pg.group.id: pg for pg in diagram.groups}
    ordered: list = []
    visited: set[str] = set()

    def visit(gid: str) -> None:
        if gid in visited:
            return
        pg = by_id[gid]
        if pg.group.parent:
            visit(pg.group.parent)
        visited.add(gid)
        ordered.append(pg)

    for gid in by_id:
        visit(gid)
    return ordered
```

- [ ] **Step 8: Run all renderer and layout tests**

Run: `uv run pytest tests/test_renderer_drawio.py tests/test_layout_engine.py -v`
Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/netdiagram/layout/engine.py src/netdiagram/renderers/drawio.py tests/test_renderer_drawio.py tests/test_layout_engine.py
git commit -m "feat(renderer,layout): groups as Draw.io container cells with child nesting"
```

---

## Task 14: CLI — `validate`, `render`, `schema`, `list-types`

**Files:**
- Create: `src/netdiagram/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
import json

from typer.testing import CliRunner

from netdiagram.cli import app

runner = CliRunner()


def test_validate_good_file(fixtures_dir):
    result = runner.invoke(app, ["validate", str(fixtures_dir / "simple_two_nodes.yaml")])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_validate_bad_file(fixtures_dir):
    result = runner.invoke(app, ["validate", str(fixtures_dir / "invalid_missing_node.yaml")])
    assert result.exit_code != 0
    assert "unknown node 'ghost'" in result.stdout


def test_render_drawio_to_file(fixtures_dir, tmp_path):
    out = tmp_path / "out.drawio"
    result = runner.invoke(
        app,
        ["render", str(fixtures_dir / "simple_two_nodes.yaml"),
         "--format", "drawio", "--output", str(out)],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    content = out.read_text()
    assert "<mxfile" in content


def test_schema_prints_json(fixtures_dir):
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["title"] == "Diagram"


def test_list_types_prints_node_and_group_types():
    result = runner.invoke(app, ["list-types"])
    assert result.exit_code == 0
    assert "router" in result.stdout
    assert "subnet" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: ImportError on `netdiagram.cli`.

- [ ] **Step 3: Implement the CLI**

Create `src/netdiagram/cli.py`:

```python
"""Typer-based CLI for netdiagram."""

from __future__ import annotations

import json
import typing as t
from pathlib import Path

import typer

from netdiagram.ir.loader import LoaderError, load_diagram
from netdiagram.ir.models import GroupType, NodeType
from netdiagram.ir.schema import diagram_json_schema
from netdiagram.layout import layout_diagram
from netdiagram.renderers.drawio import DrawioRenderer

app = typer.Typer(help="LLM-friendly network diagram tool.")

_RENDERERS = {
    "drawio": DrawioRenderer(),
}


@app.command()
def validate(
    path: Path = typer.Argument(..., exists=False, help="Path to a YAML or JSON diagram IR file."),
) -> None:
    """Validate a diagram file against the IR schema."""
    try:
        load_diagram(path)
    except LoaderError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)
    typer.echo(f"{path}: valid")


@app.command()
def render(
    path: Path = typer.Argument(..., help="Path to a YAML or JSON diagram IR file."),
    fmt: str = typer.Option(
        "drawio", "--format", "-f", help="Output format: drawio (more in later phases)."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path. Defaults to <input>.<ext>."
    ),
) -> None:
    """Render a diagram file to the chosen format."""
    try:
        diagram = load_diagram(path)
    except LoaderError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)

    renderer = _RENDERERS.get(fmt)
    if renderer is None:
        typer.echo(f"Unknown format '{fmt}'. Supported: {', '.join(_RENDERERS)}")
        raise typer.Exit(code=2)

    laid = layout_diagram(diagram)
    content = renderer.render(laid)

    out = output or path.with_suffix(renderer.extension)
    out.write_text(content, encoding="utf-8")
    typer.echo(f"Wrote {out}")


@app.command()
def schema() -> None:
    """Print the JSON Schema for the Diagram IR."""
    typer.echo(json.dumps(diagram_json_schema(), indent=2))


@app.command("list-types")
def list_types() -> None:
    """List supported node and group types."""
    typer.echo("Node types:")
    for nt in t.get_args(NodeType):
        typer.echo(f"  - {nt}")
    typer.echo()
    typer.echo("Group types:")
    for gt in t.get_args(GroupType):
        typer.echo(f"  - {gt}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all 5 tests pass.

- [ ] **Step 5: Smoke test the installed command**

Run:
```bash
uv run netdiagram list-types
uv run netdiagram validate tests/fixtures/simple_two_nodes.yaml
```
Expected: both commands succeed and print reasonable output.

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/cli.py tests/test_cli.py
git commit -m "feat(cli): validate, render, schema, list-types commands via Typer"
```

---

## Task 15: End-to-End Integration Test

**Files:**
- Create: `tests/test_end_to_end.py`

- [ ] **Step 1: Write the end-to-end test**

Create `tests/test_end_to_end.py`:

```python
from pathlib import Path

from lxml import etree
from typer.testing import CliRunner

from netdiagram.cli import app
from netdiagram.ir.loader import load_diagram
from netdiagram.layout import layout_diagram
from netdiagram.renderers.drawio import DrawioRenderer


def test_branch_office_renders_valid_drawio_xml(fixtures_dir: Path, tmp_path: Path) -> None:
    """Full pipeline: YAML -> IR -> layout -> Draw.io XML. Assert the output parses,
    contains all nodes and edges, and has no overlapping node geometries."""
    diagram = load_diagram(fixtures_dir / "branch_office.yaml")
    laid = layout_diagram(diagram)
    xml = DrawioRenderer().render(laid)

    root = etree.fromstring(xml.encode("utf-8"))
    node_cells = [c for c in root.findall(".//mxCell") if c.get("vertex") == "1"
                  and c.get("id", "").startswith("node-")]
    edge_cells = [c for c in root.findall(".//mxCell") if c.get("edge") == "1"]
    assert len(node_cells) == 3
    assert len(edge_cells) == 2

    # Node geometries must be absolute coordinates (no negative values) and disjoint.
    rects: list[tuple[float, float, float, float]] = []
    for c in node_cells:
        # For nodes inside groups, geometry is relative to the group — skip those.
        if c.get("parent") != "1":
            continue
        g = c.find("mxGeometry")
        rects.append((
            float(g.get("x")),
            float(g.get("y")),
            float(g.get("width")),
            float(g.get("height")),
        ))
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            ax, ay, aw, ah = rects[i]
            bx, by, bw, bh = rects[j]
            overlap_x = ax + aw > bx and bx + bw > ax
            overlap_y = ay + ah > by and by + bh > ay
            assert not (overlap_x and overlap_y), f"overlap between rect {i} and {j}"


def test_cli_render_produces_openable_file(fixtures_dir: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "branch.drawio"
    result = runner.invoke(
        app, ["render", str(fixtures_dir / "branch_office.yaml"), "--output", str(out)]
    )
    assert result.exit_code == 0, result.stdout
    # The file must parse as XML with an mxfile root
    parsed = etree.parse(str(out))
    assert parsed.getroot().tag == "mxfile"
```

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -v`
Expected: every test in the suite passes (including this new file).

- [ ] **Step 3: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "test: end-to-end YAML -> Draw.io XML rendering with branch office fixture"
```

---

## Wrap-Up

- [ ] **Final verification**

Run: `uv run pytest --cov=netdiagram --cov-report=term-missing`
Expected: all tests pass, coverage reported per module.

- [ ] **Manual verification (author responsibility)**

1. `uv run netdiagram render tests/fixtures/branch_office.yaml --output /tmp/branch.drawio`
2. Open `/tmp/branch.drawio` in Draw.io (desktop or app.diagrams.net).
3. Confirm:
   - Three nodes visible (fw1, core-sw1, srv1) with distinct shapes per type
   - VLAN 100 container encloses core-sw1 and srv1
   - Interface labels appear on the edges
   - No node overlaps, no edges pass through node bodies

Note any visual issues for Phase 2 layout improvements; do not fix in Phase 1.

- [ ] **Tag Phase 1 complete**

```bash
git tag phase-1-mvp
```
