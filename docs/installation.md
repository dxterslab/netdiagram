# Installation Guide

## Prerequisites

### Python 3.11+

netdiagram requires Python 3.11 or later.

```bash
python3 --version   # must be 3.11+
```

### Graphviz system library

The layout engine uses `pygraphviz`, which requires graphviz C headers at install time.

**macOS:**
```bash
brew install graphviz
```

**Debian / Ubuntu:**
```bash
sudo apt-get install graphviz graphviz-dev
```

**RHEL / Fedora:**
```bash
sudo dnf install graphviz graphviz-devel
```

If you skip this, the install will fail with `graphviz/cgraph.h: No such file or directory`.

### D2 (optional — only needed to render `.d2` files)

netdiagram generates `.d2` source text. To render it to SVG or PNG you need the D2 CLI:

```bash
brew install d2          # macOS
# or
curl -fsSL https://d2lang.com/install.sh | sh
```

---

## Install Methods

### Method 1: Install from GitHub (recommended)

No PyPI account needed. Installs the latest `main` branch.

**With uv (recommended):**

```bash
# Install as a global tool — netdiagram and netdiagram-mcp become available everywhere
uv tool install git+https://github.com/dxterslab/netdiagram
```

**With pip:**

```bash
pip install git+https://github.com/dxterslab/netdiagram
```

**With pipx (isolated environment):**

```bash
pipx install git+https://github.com/dxterslab/netdiagram
```

After any of these, the CLI is available globally:

```bash
netdiagram --help
netdiagram validate topology.yaml
netdiagram render topology.yaml --format drawio --output network.drawio
netdiagram-mcp   # starts the MCP server on stdio
```

### Method 2: Install from a specific tag or branch

```bash
# Install a tagged release
uv tool install git+https://github.com/dxterslab/netdiagram@phase-2d-label-collision

# Install from a feature branch
uv tool install git+https://github.com/dxterslab/netdiagram@feat/some-branch
```

### Method 3: Clone and develop locally

Use this if you want to modify the code or run tests.

```bash
git clone https://github.com/dxterslab/netdiagram.git
cd netdiagram

# uv creates the venv, installs all deps (runtime + dev), and writes uv.lock
uv sync

# Run via uv run (required — the venv isn't activated globally)
uv run netdiagram validate topology.yaml
uv run netdiagram render topology.yaml --format drawio --output network.drawio
uv run netdiagram-mcp

# Run tests
uv run pytest
uv run ruff check src tests
```

---

## Verify the Installation

```bash
# Check the CLI works
netdiagram list-types

# Check the MCP server starts (it will wait silently on stdin — Ctrl-C to exit)
netdiagram-mcp
```

Expected `list-types` output:

```
Node types:
  - router
  - switch
  - firewall
  - server
  - load_balancer
  - access_point
  - endpoint
  - generic
  - vpc
  - cloud_lb
  - cloud_db
  - internet_gateway
  - nat_gateway
  - security_group

Group types:
  - subnet
  - vlan
  - vpc
  - availability_zone
  - region
  - zone
  - dmz
```

---

## Configure the MCP Server

Once installed, configure your LLM client to use `netdiagram-mcp`.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "netdiagram": {
      "command": "netdiagram-mcp"
    }
  }
}
```

If you installed via Method 3 (local dev clone), use the full uv invocation instead:

```json
{
  "mcpServers": {
    "netdiagram": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/netdiagram", "run", "netdiagram-mcp"]
    }
  }
}
```

Restart Claude Desktop. The five tools (`get_schema`, `list_types`, `validate_diagram`, `render_diagram`, `preview_layout`) will appear in the tools menu.

### Claude Code

Add to `.claude/settings.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "netdiagram": {
      "command": "netdiagram-mcp"
    }
  }
}
```

### Other MCP clients

Any stdio MCP client can spawn the server:

```bash
netdiagram-mcp
```

See [docs/mcp-integration.md](mcp-integration.md) for the full tool reference and [docs/mcp-llm-workflow.md](mcp-llm-workflow.md) for usage examples.

---

## Upgrading

**uv tool:**
```bash
uv tool install --force git+https://github.com/dxterslab/netdiagram
```

**pip:**
```bash
pip install --force-reinstall git+https://github.com/dxterslab/netdiagram
```

**Local clone:**
```bash
cd netdiagram
git pull
uv sync
```

---

## Uninstalling

**uv tool:**
```bash
uv tool uninstall netdiagram
```

**pip:**
```bash
pip uninstall netdiagram
```

**Local clone:** delete the directory.

---

## Troubleshooting

### `graphviz/cgraph.h: No such file or directory`

Graphviz system headers are missing. Install them (see Prerequisites above) and retry.

On macOS with Homebrew, if the error persists after `brew install graphviz`, pygraphviz may need explicit header paths:

```bash
CFLAGS="-I$(brew --prefix graphviz)/include" \
LDFLAGS="-L$(brew --prefix graphviz)/lib" \
uv tool install git+https://github.com/dxterslab/netdiagram
```

### `netdiagram: command not found` after install

If you installed with `uv tool install`, ensure `~/.local/bin` (or uv's tool bin directory) is on your `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### MCP server doesn't respond

`netdiagram-mcp` speaks JSON-RPC on stdin/stdout. It will print nothing on startup — that's correct. It's waiting for JSON-RPC messages from the MCP client. If you're testing manually:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}' | netdiagram-mcp
```

A JSON response confirms the server is alive.
