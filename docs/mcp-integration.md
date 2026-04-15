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
4. LLM calls `render_diagram(ir, "drawio")` or `render_diagram(ir, "d2")`. The `content` field holds the target-format text (Draw.io mxGraph XML or D2 source). The LLM returns it to the user for download or writes it to a path.
5. If layout spacing needs inspection before committing, `preview_layout` returns positioned nodes and routed edges without rendering.

## Debugging

Run the server directly and pipe handwritten JSON-RPC:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"manual","version":"0"}}}' | uv run netdiagram-mcp
```

A response line confirms the server is alive. For a structured test harness, see `tests/test_mcp_integration.py`.
