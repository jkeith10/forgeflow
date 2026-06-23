import threading
import urllib.request

from forgeflow.engine.runner import run_workflow
from forgeflow.memory.sqlite import memory_set
from forgeflow.schemas.workflow import load_workflow
from forgeflow.web.app import api_payload, make_server, render_index


def _seed_run(examples_dir):
    wf = load_workflow(examples_dir / "support_triage.yaml")
    return run_workflow(wf, mock=True)


def test_api_runs_lists_and_fetches(examples_dir):
    result = _seed_run(examples_dir)

    status, body = api_payload("/api/runs")
    assert status == 200
    assert any(r["run_id"] == result.run_id for r in body["runs"])

    status, run = api_payload(f"/api/runs/{result.run_id}")
    assert status == 200
    assert run["workflow"] == "support_triage"
    assert run["outputs"]["category"] == "complaint"


def test_api_run_not_found():
    status, body = api_payload("/api/runs/run_does_not_exist")
    assert status == 404
    assert body["error"] == "not_found"


def test_api_stats_and_memory(examples_dir):
    _seed_run(examples_dir)
    memory_set("refund_policy", "Refunds over $500 need approval")

    status, stats = api_payload("/api/stats")
    assert status == 200
    assert stats["total"] >= 1
    assert "completed" in stats["by_status"]

    status, mem = api_payload("/api/memory")
    assert status == 200
    assert any(m["key"] == "refund_policy" for m in mem["memory"])


def test_api_unknown_route():
    status, body = api_payload("/api/nope")
    assert status == 404
    assert body["error"] == "unknown_route"


def test_index_html_renders():
    html = render_index()
    assert "ForgeFlow" in html
    assert "/api/runs" in html


def test_http_server_roundtrip(examples_dir):
    _seed_run(examples_dir)
    srv = make_server("127.0.0.1", 0)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        stats = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stats", timeout=5).read()
        assert b"total" in stats
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read()
        assert b"ForgeFlow" in page
    finally:
        srv.shutdown()
        srv.server_close()
