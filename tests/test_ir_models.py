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
            nodes=[],
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
            nodes=[],
        )


def test_node_and_group_id_collision_rejected():
    with pytest.raises(ValidationError, match="ids used as both node and group"):
        Diagram(
            version="1.0",
            metadata=Metadata(title="T", type="logical"),
            groups=[Group(id="shared", label="G", type="zone")],
            nodes=[Node(id="shared", label="N", type="router")],
        )


def test_unknown_version_rejected():
    with pytest.raises(ValidationError):
        Diagram(
            version="99.0",
            metadata=Metadata(title="T", type="physical"),
            nodes=[Node(id="a", label="a", type="router")],
        )
