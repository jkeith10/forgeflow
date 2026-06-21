#!/usr/bin/env bash
# ForgeFlow 60-second demo — runs entirely offline in mock mode (no API keys).
set -euo pipefail

run() { echo; echo "\$ $*"; eval "$@"; }

echo "=== ForgeFlow demo (mock mode, no API keys needed) ==="

run forgeflow run examples/support_triage.yaml --mock --yes
run forgeflow run examples/sales_lead_qualifier.yaml --mock --yes
run forgeflow run examples/home_service_dispatch.yaml --mock --yes

echo; echo "=== Evals ==="
run forgeflow eval examples/evals/support_triage_eval.yaml
run forgeflow eval examples/evals/sales_lead_qualifier_eval.yaml

echo; echo "=== Audit log ==="
run forgeflow runs -n 5

echo; echo "Done. Inspect any run with: forgeflow inspect <run_id>"
