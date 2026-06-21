# Contributing to ForgeFlow

Thanks for being here! ForgeFlow is small on purpose, and that makes it a great
codebase to contribute to. New providers, tools, example workflows, and eval
types are especially welcome.

## Dev setup

```bash
git clone https://github.com/your-org/forgeflow
cd forgeflow
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest          # run the test suite
ruff check .    # lint
```

Everything runs offline in mock mode — you don't need API keys to develop or test.

## Project layout

```
src/forgeflow/
  cli.py            # Typer CLI
  engine/           # runner, steps, conditions, templating
  providers/        # mock | openai | anthropic + base
  tools/            # registry + safe builtins
  memory/           # SQLite key/value memory
  logging/          # run audit log
  evals/            # eval runner + assertions
  schemas/          # Pydantic models for workflows + evals
examples/           # workflows + eval suites
docs/               # spec, architecture, evals, providers
tests/              # pytest
```

## How to add things

- **A provider** → `docs/providers.md` ("Adding a provider"). Keep it thin and key-from-env.
- **A tool** → register in `tools/builtins.py` or your own module. Tools must be safe (no shell/eval).
- **An example workflow** → add to `examples/`, and add an eval to `examples/evals/`.
- **A step type** → add an executor in `engine/steps.py` and a branch in `engine/runner.py::_execute`.

## PR checklist

- [ ] `pytest` passes
- [ ] `ruff check .` is clean
- [ ] New behavior has a test (and, for workflows, an eval)
- [ ] Docs updated if you changed the spec or CLI

## Good first issues

- Add a new built-in tool (e.g. `http_get`, `slugify`, `extract_emails`).
- Add an example workflow for a new domain (recruiting, content, ops).
- Add an eval operator (`regex`, `length_between`).
- Add an `--json` output flag to `forgeflow run` for scripting.
- Improve the mock provider's heuristics for a new field type.

By contributing you agree your work is licensed under the project's [MIT License](LICENSE).
