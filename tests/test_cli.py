import json

from typer.testing import CliRunner

from forgeflow.cli import app

runner = CliRunner()


def test_templates_command():
    result = runner.invoke(app, ["templates"])
    assert result.exit_code == 0
    assert "support_triage" in result.stdout
    assert "memory_get" in result.stdout


def test_run_mock(examples_dir):
    path = str(examples_dir / "support_triage.yaml")
    result = runner.invoke(app, ["run", path, "--mock", "--yes"])
    assert result.exit_code == 0
    assert "Run ID" in result.stdout


def test_run_json_output(examples_dir):
    path = str(examples_dir / "support_triage.yaml")
    result = runner.invoke(app, ["run", path, "--mock", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["status"] == "completed"
    assert data["outputs"]["category"] == "complaint"
    assert data["run_id"].startswith("run_")


def test_eval_json_output(examples_dir):
    path = str(examples_dir / "evals" / "support_triage_eval.yaml")
    result = runner.invoke(app, ["eval", path, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["all_passed"] is True
    assert data["total"] == 3


def test_eval_command(examples_dir):
    path = str(examples_dir / "evals" / "support_triage_eval.yaml")
    result = runner.invoke(app, ["eval", path])
    assert result.exit_code == 0
    assert "cases passed" in result.stdout


def test_memory_cli_roundtrip():
    assert runner.invoke(app, ["memory", "set", "policy", "be kind"]).exit_code == 0
    got = runner.invoke(app, ["memory", "get", "policy"])
    assert got.exit_code == 0
    assert "be kind" in got.stdout


def test_init_scaffolds(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "examples" / "hello_triage.yaml").exists()
