# Dashboard

ForgeFlow ships a local web dashboard for observing runs — no extra dependencies
(it's built on Python's stdlib `http.server`) and no account or hosting required.

```bash
forgeflow serve            # opens http://127.0.0.1:8787 in your browser
forgeflow serve --port 9000 --no-browser
```

## What it shows

- **Runs** — a live, auto-refreshing list of recent runs with status pills.
- **Run detail** — click any run to see its inputs, every step (status + output),
  and final outputs — the same trace as `forgeflow inspect`, but clickable.
- **Memory** — browse the local key/value store (policies, facts).

The dashboard is **read-only** and reads from the same SQLite store the CLI writes
to (`./.forgeflow/forgeflow.db`), so anything you run on the CLI shows up here
within a few seconds.

## JSON API

The dashboard is a thin client over a small JSON API you can also hit directly:

| Endpoint | Returns |
| --- | --- |
| `GET /api/runs?limit=50` | Recent runs. |
| `GET /api/runs/<run_id>` | Full run trace (inputs, steps, outputs). |
| `GET /api/memory` | All memory items. |
| `GET /api/templates` | Built-in workflow templates. |
| `GET /api/stats` | Version + run counts by status. |

## Roadmap

Web-based **approvals** (approve/reject a paused `human_approval` gate from the
dashboard) are the next step — they need the runner to expose live run state, so
they're tracked separately from this read-only v1.
