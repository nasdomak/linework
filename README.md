# linework

**A design partner that learns your trade, thinks about the problem, writes
readable recipes, and executes them without getting a single number wrong.**

A local 2D design agent. It speaks DXF, and later plugs into LibreCAD through a
plugin — but the goal is **the drawing and the productivity**, not any one CAD
program. Everything runs on your own machine against an open-source model served
by Ollama. No cloud, no telemetry, nothing leaves the PC.

Status: **early.** The workbench that builds it exists; the product does not
yet. See `state/backlog.json` for exactly where things stand.

---

## The idea in one paragraph

Checking a model's output after the fact does not work: if it may write `10,20`
it may write `1000,200`, and both are legal. So at the moment of drawing, the
model may not write numbers at all. It states **relations** — `window on
wall_north, centred, width 120` — and our code computes "centred" from the real
wall. The model did not avoid the mistake; it had no way of making it.

> **Thinking is free. The hand is guided.**
>
> Deliberation is unconstrained: the model interprets, proposes, compares,
> argues and criticises its own work. Commitment goes through a narrow validated
> gate. **Numbers enter through two doors only: the user dictates them, or the
> solver computes them.** The model never emits executable text and never a
> final coordinate.

The ambition is not a drafting assistant. It is an **autonomous designer** —
rung 4 of a four-rung ladder (hand, apprentice, assistant, designer) — and the
architecture is built so the ceiling rises with the model rather than capping it.

## The pipeline

```
natural language + the drawing + the memory
   │
   ▼
FREE REASONING          ← the model thinks. No constraints.
   │
   ▼
design decision         ← discussed with the human when it matters
   │  the model fills a form: fixed fields, closed value lists
   ▼
validated structured intent   ← refused here if it does not fit the catalogue
   │  the ENGINE writes the script (never the model)
   ▼
readable script         ← a human can read, correct, re-run and version it
   │  the solver resolves relations into exact coordinates,
   │  defaults taken from the memory
   ▼
geometry (DXF)          ← exact
```

## The memory, in two layers

The program ships **empty** and learns its user.

- **Layer 1, the standard** — thicknesses, layer names, weights, text heights,
  dimension styles, the scales actually used. Values.
- **Layer 2, the judgement** — how you solve problems, what you rejected and
  *why*, the criteria by which you call a drawing good. Reasoning, not results.
  This is what makes rung 4 possible.

Filled by a short first-run interview, by learning while working, and — the
strongest of the three — by **reading your own old DXF drawings**, because nobody
can recite their own standard, they just draw it.

Plain text, one line one decision, with provenance and a date. Outside the
program folder, no sync, hand-exportable, and **never model weights**, so
deleting it actually deletes it.

**The script says *what*; the memory says *how*.** Change one rule and the whole
project realigns. Hand a script to a colleague and it comes out in *his*
standard.

## Repository layout

| Path | What it is | May import |
|---|---|---|
| `lang/` | the form and the script language — the bridle | standard library only |
| `geometry/` | the solver: relations become exact coordinates | standard library only |
| `memory/` | the two-layer memory | standard library only |
| `engine/` | the orchestrator, and the Ollama client | standard library only |
| `dxf/` | reading and writing real DXF | `ezdxf` |
| `shared/` | versioned schemas | standard library only |
| `plugin/` | the C++ LibreCAD plugin (product phase 14) | Qt |
| `tools/` | the workbench: the loop, rendering, visual checks | anything |
| `state/` | the executable plan, the loop state, the decision queue | — |
| `docs/adr/` | frozen decisions, numbered | — |

CI enforces the "standard library only" column.

## The workbench

This project builds itself, and that is deliberate: **the development loop is
the first prototype of the product** — an autonomous agent, bridled,
self-verifying, with persistent memory, steered by natural language. If it
cannot be made to work here, it has no business being shipped to anyone.

```
py tools/loop.py status        where the loop is, in one screen
py tools/loop.py next          the next unblocked task
py tools/loop.py check         is the plan still coherent
py tools/loop.py report        the thirty-second digest
```

- `PROMPT.md` is the standing session prompt. It never changes, so it is never
  pasted again.
- `state/backlog.json` is the single answer to "what is next". A session reads
  it; it never asks.
- `state/decisions.json` is the decision queue: the loop never blocks on a
  question, it proposes a default with a rationale and carries on. Anything
  irreversible waits.
- `tools/render_dxf.py` and `tools/visual_check.py` are the eyes: a DXF becomes
  a PNG the agent reads itself, with cluster-based golden-image comparison so a
  visual regression fails a test instead of needing a human to notice.

The `linework` plugin (installed separately on the developer's machine) provides
the hands: files including delete, git with server-built commit messages, the
GitHub API, tests, rendering, LibreCAD and Ollama.

## Running the tests

```
python -m pip install -r requirements-dev.txt
python -m pytest -q
python tools/loop.py check
```

The suite runs with **no CAD, no Ollama and no network**. Anything that needs
them sits behind a marker and outside the default run.

## Licence

Not yet decided — see decision `D-001` in `state/decisions.json` and product
task `P0-T01`. The intent is a free, public, open-source release. The proposal on
the table is GPL-2.0-or-later, because it stays compatible with LibreCAD's GPL v2
for when the plugin arrives. Until the LICENSE file exists, treat this as "all
rights reserved by default", which is precisely why it is the first task in the
plan.

## Prior art

The text-to-CAD field is crowded but elsewhere: cloud services, mostly 3D, none
inside a CAD the user already owns. LLM floor-plan generation is active academic
research. The space "local, free, 2D, learns you, reasons about the design,
inside your own CAD" is empty.
