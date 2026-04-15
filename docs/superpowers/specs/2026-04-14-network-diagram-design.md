# Network Diagram Tool — Design Spec

**Date:** 2026-04-14
**Status:** Approved (design phase)

## Overview

A Python tool that lets LLMs and humans describe network topologies in a structured format (YAML/JSON) and renders them to multiple diagram backends (Draw.io, D2, Mermaid). The primary workflow is LLM-driven: a user provides raw network data (LLDP/CDP neighbors, interface state, routing tables, cloud inventory), an LLM interprets it into a validated intermediate representation (IR), and the tool renders readable diagrams.

The tool's value is in the rendering and layout layer — it relieves the LLM of pixel-level concerns so it can focus on understanding the network.

## Goals

- Structured, schema-validated IR that LLMs produce reliably and humans can read/edit
- Multi-backend rendering: Draw.io, D2, Mermaid from a single IR
- Layout engine that produces readable diagrams without manual cleanup on common topologies
- Two interfaces: CLI for file-based workflows, MCP server for LLM-in-the-loop workflows
- Support both physical topologies (devices, links, interfaces) and logical/cloud topologies (VPCs, subnets, availability zones, security groups)

## Non-Goals

- Real-time network monitoring or live data collection
- Replacing dedicated design tools (Visio, Lucidchart) for manual diagram authoring
- Pixel-perfect layouts for arbitrarily large/dense topologies (N2G's own limitation; we aim for substantial improvement but not perfection)
- Round-trip editing of diagrams modified in the target tool (Draw.io/yEd) after rendering

## Architecture

```
Raw network data (LLDP/CDP output, inventory, configs)
    |
    v
[LLM interprets data]
    |
    v
IR (YAML/JSON)  <--- JSON Schema validation
    |
    v
[Layout engine]  — computes node positions, edge routes, label placement
    |
    v
[Renderer]  — Draw.io XML, D2, or Mermaid
    |
    v
Output file(s)
```

Three logical layers:

1. **IR & Validation** — Pydantic models define the schema; JSON Schema is auto-generated for LLM consumption.
2. **Layout Engine** — Dimension-aware placement and edge routing. Leverages existing graph layout algorithms (via networkx/graphviz/grandalf) and adds post-processing passes for overlap resolution, edge routing around nodes, and label collision handling.
3. **Renderers** — One per backend, consuming a layouted IR and producing target-format output.

Two interfaces sit on top:
- **CLI** (`netdiagram`) — validate, render, inspect schema
- **MCP server** (`netdiagram-mcp`) — tools for LLM iteration: `get_schema`, `validate_diagram`, `render_diagram`, `preview_layout`, `list_node_types`

## Intermediate Representation (IR)

### Design principles

- **Typed nodes** — `router`, `switch`, `firewall`, `server`, `cloud`, `load_balancer`, `vpc`, `availability_zone`, `subnet`, etc. The renderer picks icons/shapes from the node type.
- **Explicit interfaces** — links connect interface-to-interface, not node-to-node. Interface labels are first-class.
- **Nested groups** — groups (subnets, VLANs, VPCs, AZs) can contain nodes and other groups.
- **Physical vs logical** — `metadata.type` distinguishes physical topologies from logical ones; affects rendering defaults.
- **Pydantic-backed** — all validation uses Pydantic v2; JSON Schema is generated from models.

### Example

```yaml
version: "1.0"
metadata:
  title: "Branch Office Topology"
  type: physical

groups:
  - id: server-vlan
    label: "VLAN 100 - Servers (10.0.1.0/24)"
    type: subnet

nodes:
  - id: core-sw1
    label: "core-sw1"
    type: switch
    group: server-vlan
    interfaces:
      - id: gi0/1
        speed: 1G
        state: up
      - id: gi0/2
        speed: 1G
        state: down
    data:
      vendor: cisco
      model: "C9300"

links:
  - source: { node: core-sw1, interface: gi0/1 }
    target: { node: fw1, interface: eth1 }
    label: "Trunk"
    style: solid
```

### Supported node types (initial)

Physical: `router`, `switch`, `firewall`, `server`, `load_balancer`, `access_point`, `endpoint`, `generic`
Cloud: `vpc`, `subnet`, `availability_zone`, `region`, `security_group`, `internet_gateway`, `nat_gateway`, `cloud_lb`, `cloud_db`

Each type maps to a renderer-specific icon/shape. Unknown types fall back to `generic`.

### Supported group types

`subnet`, `vlan`, `vpc`, `availability_zone`, `region`, `zone` (generic), `dmz`

Groups can nest (e.g., subnet inside VPC inside AZ inside region).

## Layout Engine

### Problem statement

Existing tools like N2G delegate layout entirely to igraph's force-directed algorithms (Kamada-Kawai by default). These treat nodes as dimensionless points and don't account for node size, label width, or edge routing — resulting in overlapping labels, edges crossing through node bodies, and unreadable busy diagrams.

### Approach

Use existing graph layout algorithms for initial coordinate assignment, then run custom post-processing passes.

**Pipeline:**

1. **Topology analysis** — classify the graph (tree, ring, mesh, star, hierarchical) to pick the best layout algorithm.
2. **Initial placement** — run the chosen algorithm (hierarchical via graphviz `dot`, force-directed via `fdp`/`neato`, or custom for rings) to get seed coordinates.
3. **Node expansion** — compute real node dimensions (width/height) from label length, icon, and padding.
4. **Overlap resolution** — detect node overlaps and nudge positions until resolved (e.g., via simulated-annealing or iterative spacing).
5. **Group layout** — arrange nested groups; expand parent bounds to fit children with configurable padding.
6. **Edge routing** — route edges as orthogonal or curved paths that avoid node bounding boxes. Parallel edges get spacing.
7. **Label placement** — place interface and link labels with collision detection against nodes and other labels.

### Libraries

- `networkx` — graph data structure, topology classification, graph algorithms
- `pygraphviz` (preferred) or `grandalf` (fallback, pure Python) — initial layout algorithms
- Custom Python for post-processing passes (overlap resolution, edge routing, label placement)

### Known limits

For very dense meshes (hundreds of nodes with full-mesh links), perfect layouts are infeasible; the engine will fall back to force-directed output with a warning. This matches N2G's acknowledged limit but we aim to push the threshold much higher via the post-processing passes.

## Renderers

All renderers share this interface:

```python
class Renderer(Protocol):
    format: str         # "drawio", "d2", "mermaid"
    extension: str
    def render(self, diagram: LayoutedDiagram) -> str: ...
```

### Draw.io renderer

- Emits `.drawio` XML (mxGraph format) via `lxml`
- Uses Draw.io's built-in network shape libraries (Cisco, AWS, Azure, GCP) based on node type
- Groups rendered as container cells with children nested inside
- Interface labels as edge source/target labels (`exitX`/`exitY` + edge label)
- Preserves layout engine coordinates in `mxGeometry` elements

### D2 renderer

- Emits `.d2` text in D2's native syntax
- Leverages D2's first-class network shape and icon support
- Nested containers map directly to D2's container syntax
- Layout hints passed via D2 attributes; users can optionally re-layout with D2's engines (ELK/Dagre) if they prefer

### Mermaid renderer

- Emits Mermaid `flowchart` syntax
- Limited: no true network icons, only text-labeled boxes; groups via `subgraph`
- Best-effort rendering for markdown embeds; limitations documented
- Skips advanced IR features (nested groups beyond one level, complex interface metadata) and warns

## Interfaces

### CLI (`netdiagram`)

Built with Typer.

```
netdiagram validate <ir-file>
netdiagram render <ir-file> --format <drawio|d2|mermaid>[,...] --output <path>
netdiagram render <ir-file> --format all --output-dir <dir>
netdiagram schema                  # prints JSON Schema
netdiagram list-types              # lists node and group types with descriptions
```

Validation errors from Pydantic are formatted with file path, line/column (for YAML), and fix suggestions where possible.

### MCP Server (`netdiagram-mcp`)

Built with the official `mcp` Python SDK. Exposes:

- `get_schema()` → JSON Schema for the IR
- `list_node_types()` → `[{type, description, icon_preview}, ...]`
- `validate_diagram(ir: dict)` → `{valid: bool, errors: [...]}`
- `render_diagram(ir: dict, format: str)` → `{content: str, filename: str}`
- `preview_layout(ir: dict)` → `{nodes: [{id, x, y, width, height}], edges: [{source, target, path: [...]}]}`

The `preview_layout` tool lets the LLM reason about spacing before committing to a render — useful when the LLM wants to iterate on grouping decisions.

### Typical LLM workflow

1. User pastes LLDP/CDP output into chat
2. LLM calls `get_schema()` (once per session, or uses cached schema)
3. LLM drafts IR, calls `validate_diagram(ir)`
4. On errors, LLM fixes and re-validates
5. LLM calls `render_diagram(ir, "drawio")` — returns file content
6. User opens file; if tweaks needed, LLM modifies IR and re-renders

## Tech Stack

- **Python 3.11+**
- **Pydantic v2** — IR models, JSON Schema generation
- **Typer** — CLI
- **PyYAML** — YAML parsing
- **networkx** — graph structures and analysis
- **pygraphviz** — initial layout (with grandalf as fallback)
- **lxml** — Draw.io XML generation
- **mcp** — official MCP Python SDK
- **ttp** (phase 3) — optional CLI output parsers

## Project Layout

```
network-diagram/
├── pyproject.toml
├── README.md
├── src/netdiagram/
│   ├── ir/
│   │   ├── models.py          # Pydantic models (Node, Link, Group, Diagram)
│   │   ├── schema.py          # JSON Schema generation
│   │   └── loader.py          # YAML/JSON file loading + validation
│   ├── layout/
│   │   ├── engine.py          # Pipeline orchestration
│   │   ├── topology.py        # Graph classification
│   │   ├── placement.py       # Initial placement via graphviz/grandalf
│   │   ├── overlap.py         # Overlap resolution
│   │   ├── routing.py         # Edge routing
│   │   └── labels.py          # Label placement
│   ├── renderers/
│   │   ├── base.py            # Renderer protocol + LayoutedDiagram type
│   │   ├── drawio.py
│   │   ├── d2.py
│   │   └── mermaid.py
│   ├── cli.py                 # Typer app
│   └── mcp_server.py          # MCP tools
├── tests/
│   ├── fixtures/              # Sample IR files + golden outputs
│   ├── test_ir.py
│   ├── test_layout.py
│   ├── test_renderers.py
│   └── test_mcp.py
└── docs/
    └── superpowers/specs/     # Design docs (this file)
```

## Testing Strategy

- **IR validation tests** — valid/invalid IR examples exercising every schema rule
- **Renderer snapshot tests** — fixture IR → golden output files; regressions caught by diff
- **Layout tests** — known topologies (ring, tree, mesh, hierarchical) produce expected structural properties: no node overlaps, no edges crossing node bodies (for topologies where this is feasible), expected group containment
- **Visual smoke tests** — representative fixtures render end-to-end; manual verification that outputs open correctly in Draw.io, D2, Mermaid during development
- **MCP integration tests** — invoke tools via MCP protocol, verify response schemas and error handling
- **End-to-end tests** — full pipeline from YAML → validated IR → layout → rendered file for each backend

## Phasing

**Phase 1 — MVP:**
- Pydantic IR models + JSON Schema generation
- YAML/JSON loader with clear validation errors
- Draw.io renderer
- Basic layout engine: topology classification, graphviz-based placement, node overlap resolution
- CLI: `validate`, `render`, `schema`, `list-types`

**Phase 2 — Full rendering + MCP:**
- D2 and Mermaid renderers
- MCP server with all listed tools
- Advanced layout: edge routing with obstacle avoidance, label collision resolution
- Nested group layout with padding

**Phase 3 — Data ingestion helpers:**
- TTP-based parsers for LLDP/CDP/interface output (optional helpers; the LLM can always build IR directly)
- Topology auto-detection refinements (rings, spine-leaf, full-mesh)
- Additional node type icons (security appliances, SD-WAN, etc.)

## Open Questions

None at design time. Open questions that arise during implementation will be captured in the implementation plan.
