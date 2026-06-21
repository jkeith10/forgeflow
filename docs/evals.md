# Evals

Evals are how you stop your workflow from silently breaking. An eval suite is a
YAML file with test cases; each case runs the workflow and asserts on outputs.

## Suite format

```yaml
name: support_triage_eval
workflow: ../support_triage.yaml   # path relative to THIS file

cases:
  - name: angry_repeat_caller
    inputs:
      message: "I have called three times and no one has fixed my AC."
    expect:
      steps.classify.output.category: complaint
      steps.classify.output.urgency: high

  - name: billing_issue
    inputs:
      message: "I was charged twice and want a refund."
    expect:
      steps.classify.output.category: billing
      outputs.reply:
        not_empty: true
```

## Assertion paths

The left-hand side of `expect` is a dotted path resolved against the run:

- `inputs.<name>`
- `steps.<id>.output...` (drill into structured outputs)
- `outputs.<name>`

## Operators

The right-hand side is either a scalar (equality) or a single-key operator dict:

| Operator | Meaning |
| --- | --- |
| *(scalar)* | Equality. Strings compare case-insensitively. |
| `equals: x` | Explicit equality. |
| `contains: x` | `x in actual`. |
| `icontains: x` | Case-insensitive substring. |
| `gte: n` / `lte: n` | Numeric comparison. |
| `in: [a, b]` | Membership. |
| `not_empty: true` | Truthy / non-empty. |

## Running

```bash
forgeflow eval examples/evals/support_triage_eval.yaml          # mock (default, deterministic)
forgeflow eval examples/evals/support_triage_eval.yaml --live   # use the suite's real provider
```

Evals run in **mock mode by default** so they're deterministic and free — perfect for CI.
A failing suite exits non-zero, so it gates your pipeline.
