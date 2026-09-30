# ADR 0001 — Thinking is free, the hand is guided

- **Status:** accepted
- **Date:** 2026-09-30
- **Source:** brainstorming sessions 1–3 (16/09/2026), `docs/BRAINSTORMING_SUMMARY.md` §2, §4, §10, §11
- **Backlog:** P0-T02

This is the constitution of the architecture. Every later design decision is
measured against it; a proposal that contradicts it needs a new ADR that
supersedes this one, not a quiet exception.

## Context

A 2D design agent has two different jobs, and an early draft of the project
confused them by bridling both.

**Designing** is deciding *what* to draw: how a flat is laid out, where the
load-bearing wall goes, how a joint resolves, what the brief is missing, whether
the request makes sense at all. Here the model must reason at length, propose,
compare alternatives, argue, and criticise its own work. The longer and better it
thinks, the better the outcome.

**Drafting** is putting the exact mark on the sheet. Here creativity is a defect.

Checking a model's output *after* the fact cannot make drafting safe. If the model
may write `10,20` it may equally write `1000,200`; both are legal coordinates, and
no downstream check can tell which one the user meant. The only defence is that the
model is never in a position to write the number.

## Decision

> **Thinking is free. The hand is guided.**

Deliberation is unconstrained. Commitment goes through a narrow, validated gate.

### The pipeline

```
natural language + the drawing + the memory
   │
   ▼
FREE REASONING               the model thinks: interprets, proposes, compares,
   │                         criticises, decomposes, decides. No constraints.
   ▼
design decision              discussed with the human when it matters
   │  the model fills in a form: fixed fields, values from closed lists
   ▼
validated structured intent  refused here if it does not fit the catalogue
   │  the ENGINE writes the script (never the model)
   ▼
readable script              a human can read, correct, re-run and version it
   │  the solver resolves relations into exact coordinates,
   │  with defaults taken from the memory
   ▼
geometry (DXF)               exact
```

### The two-doors rule for numbers

**Numbers enter through two doors only: the user dictates them, or the solver computes them.**

The model states **relations**, never coordinates:

```
window on wall_north, centred, width 120
```

`120` came through the first door: the user said it. "Centred" has exactly one
meaning, computed by the solver from the real wall: the second door. The model did
not avoid a mistake; it had no way of making one.

### The narrow gate: form first, then script

1. **The form.** The model commits by filling a form with fixed fields whose values
   come from closed lists — one catalogue entry per vocabulary word. A form that
   does not fit the catalogue is refused with a readable reason and handed back.
2. **The script.** Only a validated form is turned into a script line, and **the
   engine writes it, never the model.** The script is the readable, correctable,
   re-runnable record of what will be drawn.

The model therefore **never emits executable text and never a final coordinate.**

### Why deliberation is deliberately unconstrained

- The ambition is rung 4 of the autonomy ladder — a designer, not a draughtsman.
  A designer that may not think at length is a contradiction.
- Reasoning is where errors are cheapest to catch: a paragraph of argument costs
  seconds, a wrong drawing costs hours.
- The ceiling must rise with the model. A small model is an excellent hand because
  it never computes a coordinate; a larger model is a better designer because it
  reasons better. Bridling the reasoning would cap the ambition at the smallest
  model ever supported.
- Unconstrained reasoning is safe precisely because nothing it produces reaches the
  drawing except through the gate.

## Consequences

- **Phase 1 (the language) is the riskiest phase of the project.** The form and the
  script grammar *are* the bridle. Too narrow and nothing useful can be said; too
  rich and the bridle is gone.
- **The reasoning stage and the commitment stage are different in kind.** Free text
  with unconstrained length for reasoning; forced JSON validated against the
  catalogue for commitment. They may use different models.
- **The solver carries the precision** (phase 2). A mediocre model plus an exact
  solver still produces an exact drawing.
- **Something must exist for what the language cannot say** — the escape hatch
  (open issue B, P1-T05). It is the hole in the fence, so everything that comes
  through it is flagged in the script and in the output, and never silently mixed
  with validated geometry.
- **The script is an artefact in its own right**: the plan, the record, and the
  document a human corrects. Memory, undo, reproducibility and audit collapse into
  one readable file, and the model's mistakes become visible as a line of text
  instead of hiding in a drawing.

## Verification

`tests/test_repo_shape.py` asserts that this ADR exists, is non-empty, and contains
the two-doors rule verbatim. The rule itself is enforced in code from phase 1 on:
the form validator refuses anything outside the catalogue (P1-T01), and no code
path lets model output reach the DXF writer without passing through the form and
the engine-written script.
