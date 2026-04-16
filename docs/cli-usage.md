# CLI Usage Guide

`netdiagram` is a command-line tool that validates network topology YAML/JSON files and renders them to Draw.io or D2 diagrams.

## Commands

```
netdiagram validate <file>          Validate IR against the schema
netdiagram render <file> [options]  Render to Draw.io or D2
netdiagram schema                   Print JSON Schema for the IR
netdiagram list-types               List supported node and group types
```

## Quick Start

### 1. Write a topology file

Create `my-network.yaml`:

```yaml
version: "1.0"
metadata:
  title: "Small Office Network"
  type: physical

groups:
  - id: server-room
    label: "Server Room"
    type: zone

nodes:
  - id: fw1
    label: "Edge Firewall"
    type: firewall
    interfaces:
      - id: eth0
        state: up
      - id: eth1
        state: up

  - id: core-sw
    label: "Core Switch"
    type: switch
    group: server-room
    interfaces:
      - id: gi0/1
        state: up
      - id: gi0/2
        state: up
      - id: gi0/3
        state: up

  - id: srv1
    label: "Web Server"
    type: server
    group: server-room
    interfaces:
      - id: eth0
        state: up

  - id: srv2
    label: "Database"
    type: server
    group: server-room
    interfaces:
      - id: eth0
        state: up

links:
  - source: { node: fw1, interface: eth1 }
    target: { node: core-sw, interface: gi0/1 }
    label: "Trunk"

  - source: { node: core-sw, interface: gi0/2 }
    target: { node: srv1, interface: eth0 }
    label: "VLAN 10"

  - source: { node: core-sw, interface: gi0/3 }
    target: { node: srv2, interface: eth0 }
    label: "VLAN 20"
```

### 2. Validate the file

```bash
uv run netdiagram validate my-network.yaml
```

Output on success:
```
my-network.yaml: valid
```

Output on error (e.g., a typo in a node reference):
```
validation errors in my-network.yaml:
  <root>: Value error, link target references unknown node 'srv3'
```

### 3. Render to Draw.io

```bash
uv run netdiagram render my-network.yaml --format drawio --output my-network.drawio
```

Open the `.drawio` file with:
- Draw.io desktop app (`brew install --cask drawio`)
- VS Code extension (`hediet.vscode-drawio`)
- [app.diagrams.net](https://app.diagrams.net) (web)

### 4. Render to D2

```bash
uv run netdiagram render my-network.yaml --format d2 --output my-network.d2
```

Render the D2 file to SVG or PNG:
```bash
# Install D2
brew install d2

# Render to SVG (uses ELK layout engine)
d2 --layout=elk my-network.d2 my-network.svg

# Live preview (opens browser, re-renders on file save)
d2 --watch my-network.d2
```

### 5. Render to both formats at once

```bash
uv run netdiagram render my-network.yaml --format drawio --output my-network.drawio
uv run netdiagram render my-network.yaml --format d2 --output my-network.d2
```

## Reference Commands

### View the JSON Schema

The schema describes every field the IR accepts. Useful for building YAML by hand or sharing with an LLM:

```bash
uv run netdiagram schema
```

Pipe to a file for reference:
```bash
uv run netdiagram schema > ir-schema.json
```

### List available types

```bash
uv run netdiagram list-types
```

Output:
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

## Real-World Example: MLAG Spine Pair with Dual-Homed Leaves

This example shows a realistic datacenter fabric with MLAG bonds:

```yaml
version: "1.0"
metadata:
  title: "DC Fabric — Spine-Leaf MLAG"
  type: physical

groups:
  - id: spine-pair
    label: "MLAG Spine Pair"
    type: zone
  - id: leaves
    label: "Leaf Switches"
    type: zone

nodes:
  - id: spine1
    label: "spine-01"
    type: switch
    group: spine-pair
    interfaces:
      - { id: swp49, state: up }
      - { id: swp50, state: up }
      - { id: swp51, state: up }
      - { id: swp52, state: up }

  - id: spine2
    label: "spine-02"
    type: switch
    group: spine-pair
    interfaces:
      - { id: swp49, state: up }
      - { id: swp50, state: up }
      - { id: swp51, state: up }
      - { id: swp52, state: up }

  - id: leaf1
    label: "leaf-01"
    type: switch
    group: leaves
    interfaces:
      - { id: swp53, state: up }
      - { id: swp56, state: up }

  - id: leaf2
    label: "leaf-02"
    type: switch
    group: leaves
    interfaces:
      - { id: swp53, state: up }
      - { id: swp56, state: up }

links:
  # MLAG peerlink
  - source: { node: spine1, interface: swp50 }
    target: { node: spine2, interface: swp50 }
    label: "peerlink 100G"
  - source: { node: spine1, interface: swp52 }
    target: { node: spine2, interface: swp52 }
    label: "peerlink 100G"

  # Leaf-01 MLAG bond (dual-homed to both spines)
  - source: { node: spine1, interface: swp49 }
    target: { node: leaf1, interface: swp53 }
    label: "bond31 100G"
  - source: { node: spine2, interface: swp49 }
    target: { node: leaf1, interface: swp56 }
    label: "bond31 100G"

  # Leaf-02 MLAG bond
  - source: { node: spine1, interface: swp51 }
    target: { node: leaf2, interface: swp53 }
    label: "bond32 100G"
  - source: { node: spine2, interface: swp51 }
    target: { node: leaf2, interface: swp56 }
    label: "bond32 100G"
```

Render both:
```bash
uv run netdiagram render dc-fabric.yaml --format drawio --output dc-fabric.drawio
uv run netdiagram render dc-fabric.yaml --format d2 --output dc-fabric.d2
```

## Link Styles

Use `style` on links to distinguish connection types:

| Style | Meaning | Visual |
|-------|---------|--------|
| `solid` (default) | Active, bonded, primary | Solid line |
| `dashed` | Standby, management, unbonded cable | Dashed line |
| `dotted` | Inferred, proto-down, unverified | Dotted line |

```yaml
links:
  - source: { node: fw1, interface: bond11 }
    target: { node: spine1, interface: swp7 }
    label: "VS1 client VRF"
    style: solid

  - source: { node: fw1, interface: mgmt }
    target: { node: mgt-sw1, interface: swp21 }
    label: "OOB management"
    style: dashed

  - source: { node: fw2, interface: bond11 }
    target: { node: spine2, interface: swp7 }
    label: "bond13 proto-down"
    style: dotted
```

## Tips

- **Validate before rendering.** `validate` gives cleaner error messages than a render failure.
- **Use groups for paired devices.** MLAG spine pairs, HA firewall clusters, and management switch pairs each become a container in the diagram.
- **Declare interfaces explicitly.** Links reference interfaces by `id` — if a link names an interface not in the node's `interfaces` list, validation catches it.
- **One YAML per scope.** A full-site topology gets cluttered. Split into focused views: "fw-to-spines", "storage-to-spines", "spines-to-leaves". Each renders to a clean, readable diagram.
