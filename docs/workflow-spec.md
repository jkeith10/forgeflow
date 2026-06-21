# Workflow Spec

A ForgeFlow workflow is a YAML file. This is the full reference.

## Top-level fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | ✅ | Unique workflow name (used in run logs). |
| `description` | string | | Human-readable summary. |
| `provider` | string | | Default provider: `mock`, `openai`, `anthropic`. Overridable per-step and via the CLI. |
| `model` | string | | Default model for LLM steps. |
| `inputs` | map | | Declared inputs (see below). |
| `example_inputs` | map | | Sample inputs used when `run` is called with no `--input`. Great for demos. |
| `steps` | list | ✅ | Ordered list of steps. |
| `outputs` | map | | Final outputs, built from templates after all steps run. |

## Inputs

```yaml
inputs:
  message:
    type: string
    required: true
    description: The raw inbound customer message.
  priority:
    type: string
    default: normal
```

If a required input is missing and not present in `example_inputs`, the run fails fast with a clear error.

## Templating

ForgeFlow uses Jinja2. Two contexts are available everywhere:

- `inputs.<name>` — resolved inputs.
- `steps.<id>.output` — the output of a previous step.
- `memory['<key>']` — read a value from local memory.

**Type preservation:** if a template string is *exactly* one expression (`"{{ steps.x.output }}"`), the native Python value (dict/list/number) is preserved. Otherwise it renders to a string.

## Steps

Every step has an `id` and a `type`. Optional on all steps:

- `when` — a condition. The step runs only if it's truthy. Example: `when: "{{ steps.classify.output.urgency == 'high' }}"`.

### `type: llm`

Calls the configured provider.

```yaml
- id: classify
  type: llm
  output: [category, urgency, summary]   # optional: parse result as JSON with these keys
  retries: 1                             # optional: retry on JSON parse failure
  provider: anthropic                    # optional: override provider for this step
  model: claude-haiku-4-5-20251001       # optional: override model
  system: "You are a precise classifier."# optional: system prompt
  prompt: |
    Classify the message: {{ inputs.message }}
```

- Without `output`, the step result is the raw text string.
- With `output`, the result is a parsed `dict` and those keys are expected.

### `type: human_approval`

Pauses for a human decision. In interactive runs the CLI prompts y/n; with `--yes` or in non-interactive contexts (CI, evals) it auto-approves.

```yaml
- id: approval
  type: human_approval
  when: "{{ steps.classify.output.urgency == 'high' }}"
  message: "High-urgency issue. Approve before continuing."
```

A rejected approval **halts** the run (status `halted`); later steps don't run.

### `type: tool`

Calls a registered tool by name with templated args.

```yaml
- id: count
  type: tool
  tool: word_count
  args:
    text: "{{ inputs.message }}"
```

See [the tool registry](../src/forgeflow/tools/registry.py) for built-ins and how to register your own.

### `type: transform`

Pure templating — no LLM call. Useful for reshaping data between steps.

```yaml
- id: combine
  type: transform
  value:
    category: "{{ steps.classify.output.category }}"
    word_count: "{{ steps.count.output }}"
```

### `type: map`

Fan out a single inner step over a list, **concurrently**, preserving input order.
The step's output is a list of the inner step's outputs.

```yaml
- id: classify_all
  type: map
  over: "{{ inputs.messages }}"   # must resolve to a list
  as: message                     # name the item is exposed as (default: item)
  step:                           # one inner llm | tool | transform step
    type: llm
    output: [category, urgency]
    prompt: "Classify: {{ message }}"
```

Inside the inner step you also get `{{ index }}` (0-based position) and `{{ item }}`
(an alias for whatever `as` names). Access results downstream by index:
`{{ steps.classify_all.output.0.category }}`. An empty `over` list yields `[]`.

## Outputs

```yaml
outputs:
  reply: "{{ steps.draft_response.output }}"
  urgency: "{{ steps.classify.output.urgency }}"
```

Outputs are computed after all steps complete and saved with the run.
