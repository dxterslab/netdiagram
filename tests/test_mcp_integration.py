"""End-to-end MCP stdio smoke test.

Spawns `netdiagram-mcp` as a subprocess, connects via the MCP stdio client,
and exercises each registered tool. Marked slow so unit test runs can skip it.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.slow

# Ensure the subprocess can import the package from the src layout.
_SRC = str(pathlib.Path(__file__).parent.parent / "src")
_ENV = {**os.environ, "PYTHONPATH": _SRC}


async def _call(tool: str, arguments: dict | None = None) -> dict:
    """Spawn the server, call a single tool, return the parsed result."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "netdiagram.mcp_server"],
        env=_ENV,
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
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
