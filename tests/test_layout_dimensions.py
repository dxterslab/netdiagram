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
