# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Phase 1 MVP complete (as of 2026-04-15). The repo has:
- Full IR layer (Pydantic models, loader, JSON Schema export)
- Layout engine (topology classification → graphviz placement → overlap resolution → canvas normalization → edge routing → group bounds)
- Draw.io renderer (nodes, edges with interface labels, groups as containers)
- Typer CLI (`validate`, `render`, `schema`, `list-types`)
- 57 tests, all passing

Phase 2 (pending) adds the D2 and Mermaid renderers plus the MCP server.
Phase 3 (pending) adds TTP-based parsers for LLDP/CDP output.

Reference:
- `docs/superpowers/specs/2026-04-14-network-diagram-design.md` — design decisions and rationale
- `docs/superpowers/plans/2026-04-14-network-diagram-phase1-mvp.md` — task-by-task plan (completed)

## What This Tool Does

`netdiagram` lets LLMs (and humans) describe network topologies in a validated YAML/JSON intermediate representation (IR), then renders them to multiple diagram backends. The primary workflow: a user provides raw network data (LLDP/CDP output, cloud inventory) to an LLM, the LLM produces the IR, and this tool handles layout + rendering so the LLM doesn't have to reason about pixel placement.

Phase 1 ships Draw.io output. Phase 2 adds D2, Mermaid, and an MCP server. Phase 3 adds TTP-based parsers for CLI show output.

## Architecture — Three Layers

```
IR (Pydantic models, JSON Schema) → Layout Engine → Renderers
```

- **IR** (`src/netdiagram/ir/`) — Pydantic v2 models define nodes, links, groups, interfaces. Cross-reference validation (dangling node refs, group cycles, unknown interfaces) happens at model construction. JSON Schema is auto-generated from the models for LLM consumption.
- **Layout** (`src/netdiagram/layout/`) — pipeline: classify topology shape → initial placement via graphviz → compute node dimensions → resolve overlaps → route edges. Each stage is a separate module so post-processing passes can be added without disturbing placement.
- **Renderers** (`src/netdiagram/renderers/`) — one per backend, share the `Renderer` protocol. Take a `LayoutedDiagram` (positioned nodes + routed edges) and emit a string in the target format.

Interfaces on top: Typer CLI (`cli.py`) now, MCP server (Phase 2) later. Both consume the same core pipeline.

## Key Design Decisions

- **Schema-first IR, not a custom DSL** — LLMs generate structured data more reliably than DSL syntax. Pydantic validation gives the LLM actionable error messages. Rejected custom DSL and programmatic-only API; see design spec for rationale.
- **Layout is ours, not the backend's** — N2G (a predecessor) delegates entirely to igraph's force-directed layout, which treats nodes as dimensionless points. That is the root cause of "lines crossing through nodes" in busy diagrams. Our layout engine runs its own overlap resolution and (Phase 2) edge routing with obstacle avoidance.
- **Interfaces are first-class on nodes** — links connect interface-to-interface, not just node-to-node. Interface labels (`gi0/1`, `eth0`) render as edge-endpoint labels.

## Dev Workflow (once Task 1 of the plan lands)

This project uses [uv](https://docs.astral.sh/uv/) for packaging, venv management, and command execution. Do NOT manage the virtualenv manually or use `pip install`.

```bash
uv sync                                                   # create .venv, install runtime + dev deps from uv.lock
uv run pytest                                             # run all tests
uv run pytest tests/test_ir_models.py::test_name -v       # single test
uv run ruff check src tests                               # lint
uv run netdiagram validate topology.yaml                  # run the CLI
```

`uv.lock` is committed to the repo and pins transitive deps for reproducible installs. When adding a dependency, edit `pyproject.toml` and run `uv sync` — do not run `uv pip install <pkg>` ad-hoc (that bypasses the lockfile).

`pygraphviz` requires system graphviz headers. macOS: `brew install graphviz`. Debian/Ubuntu: `apt-get install graphviz graphviz-dev`.

### macOS + Python 3.14 + uv: CLI import workaround

On macOS with Python 3.14 and uv 0.11+, `uv sync` sets the `UF_HIDDEN` flag on the editable-install `.pth` file; Python 3.14's `site.addpackage()` skips hidden files, so `uv run netdiagram ...` fails with `ImportError`. Tests via `uv run pytest` are unaffected because `[tool.pytest.ini_options] pythonpath = ["src"]` injects the path separately.

**Workarounds (pick one):**
```bash
# Option A — strip the hidden flag after uv sync:
chflags nohidden .venv/lib/python*/site-packages/_editable_impl_*.pth

# Option B — prefix CLI runs with PYTHONPATH:
PYTHONPATH=src uv run netdiagram validate topology.yaml
```

## Conventions

- **TDD.** Every task in the plan writes a failing test first, then the minimal implementation. Don't batch up code without corresponding tests.
- **Pydantic v2 idioms** — `ConfigDict(extra="forbid")` on all IR models so unknown fields in user YAML surface as errors rather than silent drops.
- **Narrow files.** The plan deliberately splits layout into `dimensions.py`, `topology.py`, `placement.py`, `overlap.py`, `engine.py` rather than one big module. Keep new logic in the module that matches its responsibility; add a new module before letting any file grow past ~200 lines.
- **Commits per task step.** Plan tasks include explicit `git commit` steps — follow them. Small commits make review and rollback practical.
