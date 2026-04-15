import pytest

from netdiagram.ir import Diagram
from netdiagram.ir.loader import LoaderError, load_diagram


def test_load_simple_yaml(fixtures_dir):
    d = load_diagram(fixtures_dir / "simple_two_nodes.yaml")
    assert isinstance(d, Diagram)
    assert len(d.nodes) == 2
    assert len(d.links) == 1


def test_load_branch_office(fixtures_dir):
    d = load_diagram(fixtures_dir / "branch_office.yaml")
    assert len(d.groups) == 1
    assert d.groups[0].id == "server-vlan"
    assert {n.id for n in d.nodes} == {"fw1", "core-sw1", "srv1"}


def test_missing_file_raises(tmp_path):
    with pytest.raises(LoaderError, match="file not found"):
        load_diagram(tmp_path / "nope.yaml")


def test_invalid_yaml_syntax_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: valid: yaml: here: [\n")
    with pytest.raises(LoaderError, match="YAML parse error"):
        load_diagram(bad)


def test_validation_error_includes_context(fixtures_dir):
    with pytest.raises(LoaderError) as exc:
        load_diagram(fixtures_dir / "invalid_missing_node.yaml")
    msg = str(exc.value)
    assert "invalid_missing_node.yaml" in msg
    assert "unknown node 'ghost'" in msg


def test_load_json(tmp_path):
    j = tmp_path / "d.json"
    j.write_text(
        '{"version": "1.0", "metadata": {"title":"J","type":"physical"},'
        ' "nodes":[{"id":"a","label":"a","type":"router"}]}'
    )
    d = load_diagram(j)
    assert d.nodes[0].id == "a"
