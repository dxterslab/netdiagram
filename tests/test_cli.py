import json

from typer.testing import CliRunner

from netdiagram.cli import app

runner = CliRunner()


def test_validate_good_file(fixtures_dir):
    result = runner.invoke(app, ["validate", str(fixtures_dir / "simple_two_nodes.yaml")])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_validate_bad_file(fixtures_dir):
    result = runner.invoke(app, ["validate", str(fixtures_dir / "invalid_missing_node.yaml")])
    assert result.exit_code != 0
    assert "unknown node 'ghost'" in result.stdout


def test_render_drawio_to_file(fixtures_dir, tmp_path):
    out = tmp_path / "out.drawio"
    result = runner.invoke(
        app,
        ["render", str(fixtures_dir / "simple_two_nodes.yaml"),
         "--format", "drawio", "--output", str(out)],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    content = out.read_text()
    assert "<mxfile" in content


def test_schema_prints_json(fixtures_dir):
    result = runner.invoke(app, ["schema"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert parsed["title"] == "Diagram"


def test_list_types_prints_node_and_group_types():
    result = runner.invoke(app, ["list-types"])
    assert result.exit_code == 0
    assert "router" in result.stdout
    assert "subnet" in result.stdout


def test_render_d2_to_file(fixtures_dir, tmp_path):
    out = tmp_path / "out.d2"
    result = runner.invoke(
        app,
        [
            "render",
            str(fixtures_dir / "simple_two_nodes.yaml"),
            "--format",
            "d2",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    content = out.read_text()
    assert '"r1": {' in content
    assert '"r2": {' in content
