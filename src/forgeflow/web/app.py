"""A zero-dependency local dashboard for ForgeFlow runs, evals, and memory.

Built on the stdlib ``http.server`` so ``forgeflow serve`` works with no extra
installs. It's a read-only observability view over the same SQLite store the CLI
writes to: list runs, inspect a run's full trace, browse memory and templates.

Routing is split out into ``api_payload`` (a pure function) so it's unit-testable
without opening a socket.
"""

from __future__ import annotations

import dataclasses
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from forgeflow import __version__
from forgeflow.logging.runs import get_run, list_runs
from forgeflow.memory.sqlite import memory_list
from forgeflow.scaffold import list_templates


def api_payload(path: str) -> tuple[int, dict]:
    """Resolve an /api/* path to ``(http_status, json_body)``."""
    parsed = urlparse(path)
    route = parsed.path
    query = parse_qs(parsed.query)

    if route == "/api/runs":
        limit = int(query.get("limit", ["50"])[0])
        return 200, {"runs": list_runs(limit)}

    if route.startswith("/api/runs/"):
        run_id = route[len("/api/runs/"):]
        data = get_run(run_id)
        if not data:
            return 404, {"error": "not_found", "run_id": run_id}
        return 200, data

    if route == "/api/memory":
        return 200, {"memory": [dataclasses.asdict(i) for i in memory_list()]}

    if route == "/api/templates":
        return 200, {"templates": [{"name": n, "description": d} for n, d in list_templates()]}

    if route == "/api/stats":
        rows = list_runs(1000)
        by_status: dict[str, int] = {}
        for r in rows:
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        return 200, {"version": __version__, "total": len(rows), "by_status": by_status}

    return 404, {"error": "unknown_route", "path": route}


def render_index() -> str:
    return _INDEX_HTML


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, render_index().encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path.startswith("/api/"):
            status, payload = api_payload(self.path)
            self._send(status, json.dumps(payload, default=str).encode("utf-8"), "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # silence default request logging
        pass


def make_server(host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def serve(host: str = "127.0.0.1", port: int = 8787, open_browser: bool = True) -> None:
    httpd = make_server(host, port)
    url = f"http://{host}:{port}"
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:  # headless / no browser — not fatal
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ForgeFlow Dashboard</title>
<style>
  :root {
    --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#e6edf3;
    --muted:#8b949e; --accent:#58a6ff; --green:#3fb950; --yellow:#d29922; --red:#f85149;
    --mono:"SFMono-Regular",ui-monospace,Menlo,Consolas,monospace;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
    font-family:-apple-system,Segoe UI,Roboto,sans-serif; font-size:14px; }
  header { display:flex; align-items:center; gap:12px; padding:16px 24px;
    border-bottom:1px solid var(--border); }
  header h1 { font-size:18px; margin:0; }
  header .v { color:var(--muted); font-family:var(--mono); font-size:12px; }
  .stats { margin-left:auto; display:flex; gap:18px; font-family:var(--mono); font-size:13px; }
  .stats b { color:var(--accent); }
  main { display:grid; grid-template-columns:minmax(360px,1fr) 1.4fr; gap:0; height:calc(100vh - 65px); }
  .col { overflow:auto; padding:16px 24px; }
  .col.left { border-right:1px solid var(--border); }
  h2 { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
    margin:0 0 10px; }
  table { width:100%; border-collapse:collapse; }
  th,td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--border); font-size:13px; }
  th { color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; }
  tbody tr { cursor:pointer; }
  tbody tr:hover { background:#1c2430; }
  tbody tr.sel { background:#1f6feb22; outline:1px solid var(--accent); }
  .rid { font-family:var(--mono); font-size:12px; color:var(--accent); }
  .pill { font-family:var(--mono); font-size:11px; padding:2px 8px; border-radius:10px; }
  .completed { background:#3fb95022; color:var(--green); }
  .halted { background:#d2992222; color:var(--yellow); }
  .error,.rejected { background:#f8514922; color:var(--red); }
  .skipped { background:#8b949e22; color:var(--muted); }
  .empty { color:var(--muted); padding:24px 0; }
  .panel { background:var(--panel); border:1px solid var(--border); border-radius:8px;
    padding:14px 16px; margin-bottom:14px; }
  .panel h3 { margin:0 0 8px; font-size:12px; color:var(--muted); text-transform:uppercase; }
  pre { margin:0; white-space:pre-wrap; word-break:break-word; font-family:var(--mono);
    font-size:12px; color:var(--text); }
  .step { display:flex; gap:10px; align-items:flex-start; padding:8px 0; border-bottom:1px solid var(--border); }
  .step:last-child { border-bottom:none; }
  .step .mark { font-family:var(--mono); }
  .step .body { flex:1; min-width:0; }
  .step .id { font-family:var(--mono); font-weight:600; }
  .step .type { color:var(--muted); font-size:11px; }
  .hint { color:var(--muted); }
  .toggle { display:flex; gap:8px; margin-bottom:12px; }
  .toggle button { background:var(--panel); color:var(--text); border:1px solid var(--border);
    padding:5px 12px; border-radius:6px; cursor:pointer; font-size:12px; }
  .toggle button.active { border-color:var(--accent); color:var(--accent); }
</style>
</head>
<body>
<header>
  <h1>🔨 ForgeFlow</h1>
  <span class="v" id="version"></span>
  <div class="stats" id="stats"></div>
</header>
<main>
  <div class="col left">
    <div class="toggle">
      <button id="tab-runs" class="active" onclick="setTab('runs')">Runs</button>
      <button id="tab-memory" onclick="setTab('memory')">Memory</button>
    </div>
    <div id="list"></div>
  </div>
  <div class="col right">
    <h2>Detail</h2>
    <div id="detail"><div class="empty">Select a run to see its full trace.</div></div>
  </div>
</main>
<script>
let TAB = "runs", SELECTED = null;

function pill(s){ return '<span class="pill '+s+'">'+s+'</span>'; }

async function getJSON(u){ const r = await fetch(u); return r.json(); }

async function refreshStats(){
  const s = await getJSON("/api/stats");
  document.getElementById("version").textContent = "v"+s.version;
  const parts = Object.entries(s.by_status).map(([k,v]) => k+': <b>'+v+'</b>');
  document.getElementById("stats").innerHTML =
    'runs: <b>'+s.total+'</b> &nbsp; ' + parts.join(" &nbsp; ");
}

async function refreshList(){
  if (TAB === "runs") return renderRuns();
  return renderMemory();
}

async function renderRuns(){
  const d = await getJSON("/api/runs?limit=50");
  const el = document.getElementById("list");
  if (!d.runs.length){ el.innerHTML = '<div class="empty">No runs yet. Try: <code>forgeflow run examples/support_triage.yaml --mock</code></div>'; return; }
  let rows = d.runs.map(r =>
    '<tr data-id="'+r.run_id+'" class="'+(r.run_id===SELECTED?'sel':'')+'" onclick="openRun(\\''+r.run_id+'\\')">'+
    '<td class="rid">'+r.run_id+'</td>'+
    '<td>'+r.workflow+'</td>'+
    '<td>'+pill(r.status)+'</td>'+
    '<td class="hint">'+r.provider+'</td></tr>').join("");
  el.innerHTML = '<table><thead><tr><th>Run</th><th>Workflow</th><th>Status</th><th>Provider</th></tr></thead><tbody>'+rows+'</tbody></table>';
}

async function renderMemory(){
  const d = await getJSON("/api/memory");
  const el = document.getElementById("list");
  if (!d.memory.length){ el.innerHTML = '<div class="empty">Memory is empty. Try: <code>forgeflow memory set key value</code></div>'; return; }
  let rows = d.memory.map(m =>
    '<tr><td class="rid">'+m.key+'</td><td>'+esc(m.value)+'</td><td class="hint">'+m.updated_at+'</td></tr>').join("");
  el.innerHTML = '<table><thead><tr><th>Key</th><th>Value</th><th>Updated</th></tr></thead><tbody>'+rows+'</tbody></table>';
}

function esc(s){ return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

async function openRun(id){
  SELECTED = id;
  document.querySelectorAll("tbody tr").forEach(tr => tr.classList.toggle("sel", tr.dataset.id===id));
  const r = await getJSON("/api/runs/"+id);
  const steps = (r.steps||[]).map(s => {
    const mark = s.status==="completed" ? '<span style="color:var(--green)">✓</span>'
      : s.status==="skipped" ? '<span style="color:var(--muted)">→</span>'
      : '<span style="color:var(--red)">✗</span>';
    const out = s.output===null||s.output===undefined ? '' : '<pre>'+esc(JSON.stringify(s.output,null,2))+'</pre>';
    return '<div class="step"><span class="mark">'+mark+'</span><div class="body">'+
      '<span class="id">'+s.id+'</span> <span class="type">'+s.type+' · '+s.status+'</span>'+
      (s.detail?'<div class="hint">'+esc(s.detail)+'</div>':'')+out+'</div></div>';
  }).join("");
  document.getElementById("detail").innerHTML =
    '<div class="panel"><h3>'+r.workflow+' '+pill(r.status)+'</h3>'+
    '<div class="hint">'+r.run_id+' · '+r.provider+' · '+r.created_at+'</div></div>'+
    '<div class="panel"><h3>Inputs</h3><pre>'+esc(JSON.stringify(r.inputs,null,2))+'</pre></div>'+
    '<div class="panel"><h3>Steps</h3>'+(steps||'<div class="hint">none</div>')+'</div>'+
    (Object.keys(r.outputs||{}).length ? '<div class="panel"><h3>Outputs</h3><pre>'+esc(JSON.stringify(r.outputs,null,2))+'</pre></div>' : '');
}

function setTab(t){
  TAB = t;
  document.getElementById("tab-runs").classList.toggle("active", t==="runs");
  document.getElementById("tab-memory").classList.toggle("active", t==="memory");
  refreshList();
}

async function tick(){ await refreshStats(); await refreshList(); }
tick();
setInterval(tick, 3000);
</script>
</body>
</html>
"""
