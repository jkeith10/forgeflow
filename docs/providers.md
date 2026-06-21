# Providers

ForgeFlow is provider-agnostic. A provider implements one method:

```python
def complete(self, prompt, *, system=None, json_fields=None) -> LLMResponse: ...
```

When `json_fields` is set, the provider is asked to return a JSON object containing
those keys (the engine then parses it, with retries).

## Built-in providers

### `mock` (default, offline)

Deterministic, no API keys, no network. It's a small heuristic reasoner that
inspects the requested fields and the prompt and fills in plausible values. This
is what powers the offline demo and the CI eval suite.

```bash
forgeflow run examples/support_triage.yaml --mock
```

### `openai`

```bash
pip install "forgeflow[openai]"
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o-mini        # optional
forgeflow run examples/support_triage.yaml --provider openai
```

### `anthropic`

```bash
pip install "forgeflow[anthropic]"
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_MODEL=claude-haiku-4-5-20251001   # optional
forgeflow run examples/support_triage.yaml --provider anthropic
```

## Selecting a provider

Resolution order (first wins):

1. `--provider` / `--mock` on the CLI
2. `provider:` on the step
3. `provider:` on the workflow
4. `FORGEFLOW_PROVIDER` env var
5. `mock`

## Adding a provider

1. Subclass `Provider` in `src/forgeflow/providers/your_provider.py`.
2. Implement `default_model` and `complete()`.
3. Register it in `src/forgeflow/providers/__init__.py::get_provider`.

Keep the adapter thin — config from env, fail with a clear message if the SDK or
key is missing, and translate `json_fields` into whatever JSON-mode the API offers.
See [`openai.py`](../src/forgeflow/providers/openai.py) for a ~40-line reference.
