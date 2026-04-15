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

    version: Literal["1.0"] = "1.0"
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

        # Node/group id namespace collision
        overlap = node_ids & group_ids
        if overlap:
            raise ValueError(f"ids used as both node and group: {sorted(overlap)}")

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
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(gid: str) -> None:
            if gid in in_stack:
                raise ValueError(f"cycle in group hierarchy at '{gid}'")
            if gid in visited:
                return
            visited.add(gid)
            in_stack.add(gid)
            parent = parents.get(gid)
            if parent is not None:
                dfs(parent)
            in_stack.remove(gid)

        for gid in group_ids:
            dfs(gid)
