# Using an LLM to Build Network Diagrams via MCP

`netdiagram-mcp` is an MCP (Model Context Protocol) server that lets an LLM validate, lay out, and render network diagrams directly in conversation. The LLM reads your raw network data (LLDP output, interface lists, routing tables), constructs the diagram IR, and calls the tools to produce Draw.io or D2 files — no manual YAML writing needed.

## Setup

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "netdiagram": {
      "command": "uv",
      "args": ["--directory", "/path/to/network-diagram", "run", "netdiagram-mcp"]
    }
  }
}
```

Replace `/path/to/network-diagram` with the absolute path to your clone of the netdiagram repo. Restart Claude Desktop. The five tools will appear in the tools menu.

### Claude Code

Add to your project's `.claude/settings.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "netdiagram": {
      "command": "uv",
      "args": ["--directory", "/path/to/network-diagram", "run", "netdiagram-mcp"]
    }
  }
}
```

### Other MCP clients

Any client that can spawn a subprocess on stdio works:

```bash
uv run netdiagram-mcp
```

The server speaks JSON-RPC on stdin/stdout per the MCP spec.

## Available Tools

| Tool | What it does | When to use |
|------|-------------|-------------|
| `get_schema` | Returns the JSON Schema for the diagram IR | Once per session — teaches the LLM the IR structure |
| `list_types` | Returns valid node types and group types | Before building the IR — so the LLM picks valid types |
| `validate_diagram` | Validates an IR dict, returns `{valid, errors}` | After drafting the IR — fix errors before rendering |
| `render_diagram` | Full pipeline: validate → layout → render | When the IR is valid and you want the output file |
| `preview_layout` | Runs layout only, returns node positions and edge paths | When you want to check spacing before committing |

## Workflow: From Raw Data to Diagram

### Step 1: Paste your network data

Give the LLM raw switch output — LLDP neighbors, interface lists, bond membership, MAC tables, or any structured/unstructured evidence about your network. For example:

> Here's the LLDP neighbor output from my two spine switches. Build a network diagram showing the physical topology.
>
> **spine-sw01:**
> ```
> swp49 | bond31 | MSC1-R4-T1-LF-1   | swp53 | 100G
> swp51 | bond32 | MSC1-R4-LF-TUB-02 | swp53 | 100G
> swp50 + swp52 (peerlink) | CL3-R1-SP-02 | swp50 + swp52 | 200G
> ```
>
> **CL3-R1-SP-02:**
> ```
> swp49 | bond31 | MSC1-R4-T1-LF-1   | swp56 | 100G
> swp51 | bond32 | MSC1-R4-LF-TUB-02 | swp56 | 100G
> swp50 + swp52 (peerlink) | msc01-spine-sw01 | swp50 + swp52 | 200G
> ```

### Step 2: LLM calls `get_schema` and `list_types`

The LLM first learns what the IR looks like:

```
Tool call: get_schema()
→ Returns JSON Schema with all field definitions

Tool call: list_types()
→ Returns {node_types: ["router", "switch", ...], group_types: ["subnet", "vlan", ...]}
```

### Step 3: LLM drafts the IR and validates

The LLM interprets the LLDP data and builds a topology dict:

```
Tool call: validate_diagram({
  "version": "1.0",
  "metadata": {"title": "Spine-Leaf MLAG Fabric", "type": "physical"},
  "groups": [
    {"id": "spine-pair", "label": "MLAG Spine Pair", "type": "zone"},
    {"id": "leaves", "label": "100G Fabric Leaves", "type": "zone"}
  ],
  "nodes": [
    {"id": "spine-sw01", "label": "msc01-spine-sw01", "type": "switch",
     "group": "spine-pair",
     "interfaces": [{"id": "swp49"}, {"id": "swp50"}, {"id": "swp51"}, {"id": "swp52"}]},
    {"id": "cl3-r1-sp-02", "label": "CL3-R1-SP-02", "type": "switch",
     "group": "spine-pair",
     "interfaces": [{"id": "swp49"}, {"id": "swp50"}, {"id": "swp51"}, {"id": "swp52"}]},
    {"id": "leaf-01", "label": "MSC1-R4-T1-LF-1", "type": "switch",
     "group": "leaves",
     "interfaces": [{"id": "swp53"}, {"id": "swp56"}]},
    {"id": "leaf-02", "label": "MSC1-R4-LF-TUB-02", "type": "switch",
     "group": "leaves",
     "interfaces": [{"id": "swp53"}, {"id": "swp56"}]}
  ],
  "links": [
    {"source": {"node": "spine-sw01", "interface": "swp50"},
     "target": {"node": "cl3-r1-sp-02", "interface": "swp50"},
     "label": "peerlink 100G"},
    {"source": {"node": "spine-sw01", "interface": "swp52"},
     "target": {"node": "cl3-r1-sp-02", "interface": "swp52"},
     "label": "peerlink 100G"},
    {"source": {"node": "spine-sw01", "interface": "swp49"},
     "target": {"node": "leaf-01", "interface": "swp53"},
     "label": "bond31 100G"},
    {"source": {"node": "cl3-r1-sp-02", "interface": "swp49"},
     "target": {"node": "leaf-01", "interface": "swp56"},
     "label": "bond31 100G"},
    {"source": {"node": "spine-sw01", "interface": "swp51"},
     "target": {"node": "leaf-02", "interface": "swp53"},
     "label": "bond32 100G"},
    {"source": {"node": "cl3-r1-sp-02", "interface": "swp51"},
     "target": {"node": "leaf-02", "interface": "swp56"},
     "label": "bond32 100G"}
  ]
})

→ {"valid": true, "errors": []}
```

If validation fails, the LLM sees exactly what's wrong:

```
→ {"valid": false, "errors": [
    {"loc": "<root>", "msg": "Value error, link target references unknown node 'leaf-03'"}
  ]}
```

The LLM fixes the IR and re-validates until `valid: true`.

### Step 4: LLM renders the diagram

```
Tool call: render_diagram(ir, "drawio")
→ {"format": "drawio", "filename": "spine-leaf-mlag-fabric.drawio", "content": "<?xml ...>"}
```

The LLM writes the content to a file:

```
Tool call: render_diagram(ir, "d2")
→ {"format": "d2", "filename": "spine-leaf-mlag-fabric.d2", "content": "# Spine-Leaf MLAG Fabric\n..."}
```

### Step 5: Open the diagrams

The LLM returns the files. Open them:

```bash
# Draw.io (desktop app, VS Code extension, or web)
open spine-leaf-mlag-fabric.drawio

# D2 (render to SVG first)
d2 --layout=elk spine-leaf-mlag-fabric.d2 spine-leaf.svg
open spine-leaf.svg
```

## Example Prompts

### From LLDP output

> Here's the LLDP neighbor table from my core switch. Create a physical topology diagram showing all connected devices, their port names, and which ones are bonded.
>
> ```
> [paste lldpctl output]
> ```

### From multiple device outputs

> I have three files with switch data:
> - spine-sw01.txt (LLDP + MAC table + bond state)
> - cl3-r1-sp-02.txt (same)
> - msc01-tor-agg1.txt (same)
>
> Read all three and build a single diagram showing how these switches interconnect. Use MLAG groups for the spine pair. Show which bonds are active vs standby with solid vs dashed lines.

### Focused view from a larger topology

> From the full topology you built, create a separate diagram showing ONLY the connections between the firewall cluster and the spine pair. Include the HA sync link, all data-plane bonds, the warp (wrp) inter-VS links, and the standalone eth1-04 connections. Mark proto-down links as dotted.

### Iterative refinement

> The diagram looks right but the Qumulo storage nodes are missing their second NIC connections to CL3-R1-SP-02. Add those as dashed lines (cables present but bond not configured) and re-render.

### Asking for layout feedback

> Before rendering, can you show me the layout preview? I want to check if the nodes are spaced well before generating the final diagram.

The LLM calls `preview_layout`:

```
Tool call: preview_layout(ir)
→ {
    "canvas_width": 800, "canvas_height": 450,
    "nodes": [
      {"id": "spine-sw01", "x": 100, "y": 100, "width": 140, "height": 60},
      {"id": "cl3-r1-sp-02", "x": 100, "y": 240, "width": 130, "height": 60},
      ...
    ],
    "edges": [
      {"source": "spine-sw01", "target": "cl3-r1-sp-02", "path": [...]},
      ...
    ]
  }
```

The LLM can report: "The two spines are stacked vertically at x=100, 140px apart. The leaves are positioned to the right. Canvas is 800x450. Want me to proceed with rendering?"

## Error Handling

The MCP tools return structured errors — the LLM can read and fix them without user intervention:

| Error type | Tool | Response shape |
|---|---|---|
| Invalid IR (schema violation) | `validate_diagram` | `{"valid": false, "errors": [{"loc": "nodes.0.type", "msg": "..."}]}` |
| Unknown format | `render_diagram` | `{"error": "unsupported format 'mermaid'. Available: ['drawio', 'd2']"}` |
| Invalid IR passed to render | `render_diagram` | `{"error": "validation failed", "errors": [...]}` |
| Layout failure | `render_diagram` | `{"error": "render failed: ..."}` |

The `loc` field in validation errors tells the LLM exactly which field to fix (e.g., `nodes.2.interfaces.0.id` means "the first interface on the third node").

## Tips for Best Results

1. **Provide raw data, not instructions.** Paste LLDP tables, interface lists, bond configs directly. The LLM is better at interpreting structured CLI output than following prose descriptions of a network.

2. **One scope per diagram.** "Show me the firewall-to-spine connections" produces a cleaner diagram than "show me everything." The LLM can build multiple focused views from the same data.

3. **Name your interfaces explicitly.** When the LLM sees `swp49` in both LLDP and the IR's interface list, it can validate the reference. Unnamed connections become harder to verify.

4. **Use link styles to encode status.** Tell the LLM: "mark unbonded cables as dashed and proto-down links as dotted." This carries into both Draw.io and D2 output.

5. **Iterate via validate → fix → validate.** The LLM should call `validate_diagram` before every `render_diagram`. Each validation error has a specific `loc` and `msg` — the LLM can fix the exact field without guessing.
