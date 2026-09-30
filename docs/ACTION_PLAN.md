# linework — Action Plan, A to Z

> **This is the living copy.** It was copied into the repository from
> `01_ACTION_PLAN.md` in the kDrive folder on 30/09/2026 and is maintained here
> from now on; the kDrive original is history.
>
> `state/backlog.json` is the executable form of this plan: 45 tasks, each with
> dependencies, a definition of done and a way to verify it. `tools/sync_plan.py
> check` keeps the two in agreement and CI fails if they drift: the phase
> headings below must match the backlog's phases, and the task index at the end is
> generated from the backlog (`python tools/sync_plan.py write`).
>
> Written after the third brainstorming round (16/09/2026), on
> `docs/BRAINSTORMING_SUMMARY.md`. It declares rung 4 of the autonomy ladder —
> **designer** — as the destination. Marco's directive: aim for the maximum, no
> throwaway stepping stones, **completeness is the north star**.

---

## The spine

```
  the language → the solver → the drawing → the memory → the thinking → the judgement
  (what can be   (exact       (real DXF)    (learns      (reasons,      (critiques
   said)          where)                     you)         proposes)      itself)
```

Two rules govern the order:

1. **Whatever can sink the project comes first.** The language is phase 1 because its grammar is
   the bridle on the hand, and getting it wrong costs a rewrite of everything downstream.
2. **Nothing waits on the C++ plugin.** The goal is the drawing, so the LibreCAD live window comes
   late. The product is useful long before it exists.

Every phase states: goal, how you know it is finished, main risk.

---

## PHASE 0 — Foundations and contracts

- Project name **`linework`**, repository `github.com/nasdomak/linework` *(open issue G, settled 17/09/2026)*.
- Monorepo: `lang/`, `geometry/`, `dxf/`, `memory/`, `engine/`, `plugin/` (late), `shared/`,
  `tests/`, `tools/`, `docs/adr/`, `.github/workflows/`.
- Licence resolved with evidence (**settled 30/09/2026: GPL-2.0-or-later, `docs/adr/0004-licence.md`**). The engine is a standalone Python program reading and writing
  DXF; only the later plugin links LibreCAD's GPLv2 headers. Record the conclusion in an ADR — a
  public release depends on it.
- **ADR 0001** — thinking is free, the hand is guided: the pipeline, the two-doors rule for
  numbers, the form-then-script gate, and why deliberation is deliberately unconstrained.
- **ADR 0002** — the memory model: two layers (standard / judgement), three levels, three fill
  channels, provenance and dates, privacy, the script-vs-memory separation rule.
- CI on GitHub Actions: Python tests on Windows, macOS, Linux.

**Finished when.** Repo exists, both ADRs written, CI green.

---

## PHASE 1 — The language *(the most important artefact)*

**Goal.** Design what can be said, at both ends: the **form** the model commits through, and the
**script** the engine writes. The grammar is the bridle *(open issue A)*.

- The **form**: fixed fields, closed value lists, one entry per vocabulary word. The model never
  produces executable text.
- The **script**: readable by someone with no programming background, correctable by hand,
  re-runnable, diffable, versionable.
- **Relations, not coordinates**: `centred on`, `along`, `offset from`, `between`, `aligned with`,
  `distributed over`. The vocabulary of position is the heart of it.
- **Design intent must also be expressible**, not just finished commands: alternatives, open
  choices, "either this or that pending a decision". Without this, phase 9 has nothing to speak.
- **Anchoring rules** *(open issue C)*: where the first object goes, what "next to it" means.
  Answered by the grammar, not at runtime.
- **The escape hatch** *(open issue B)*: boundary of the free channel, how it is flagged and
  contained.
- Versioned schemas in `shared/`.

**Finished when.** A written specification with worked examples across all four domains, plus a
parser and validator with a green suite. No geometry yet.

**Risk.** Highest in the project, and it is a **design** risk. Too narrow and it cannot say anything
useful; too rich and the bridle is gone. Expect iteration; expect it to take more than one session.

---

## PHASE 2 — The geometry solver

Turn relations into exact coordinates. Pure Python, no CAD dependency, massively tested.

- Offsets and parallels, intersections, trim/extend, fillets, chamfers, tangents.
- Guaranteed closure of contours; recognition of closed contours from loose segments.
- Distributions: along a segment, on a circle, on a grid, by count or pitch.
- Notable points for automatic dimension attachment.
- Tolerances: a contour closes **exactly**, not "almost".

**Finished when.** Hundreds of tests green, covering degenerate cases (parallel, tangent,
coincident, zero-length).

**Risk.** Technically low, heavy in volume. Pays back most: after it, a mediocre model still
produces a precise drawing.

---

## PHASE 3 — The drawing: DXF in and out

- Write with `ezdxf`: geometry, layers, line types and weights, **associative dimensions**,
  **hatches**, blocks, text — everything LibreCAD's plugin API cannot do.
- Read: parse a drawing made by somebody else, in the usual DXF dialects.
- Safe round-trip: open, modify, write back **without losing** what the agent did not touch. This
  is what makes editing existing drawings possible at all.
- Verify output opens faithfully in LibreCAD and in at least one other CAD.

---

## PHASE 4 — Memory, layer 1: the standard

- Plain text, one line one decision, **provenance and date** on each.
- Three levels: defaults → user profile → current project. Nearest wins, conflicts reported.
- **Channel 1** — the short first-run interview, 5–6 questions, then it stops.
- **Channel 2** — learning while working: answers and hand-corrections become rules.
- **Channel 3** — deduction from the user's own DXF drawings: layer names, weights, colours, text
  heights, dimension styles, real scales.
- Retrieval: rules always loaded, cases by keyword. No vector database *(open issue E)*.
- Privacy: outside the program folder, no sync, hand-exportable, never model weights.

**Finished when.** Channel 3 reads a real drawing of Marco's and produces a profile he recognises,
and one script rendered against two profiles produces two correctly different drawings.

---

## PHASE 5 — The brain: free reasoning, guided hand

**Goal.** The first real sentence that becomes a drawing — with genuine thinking in front of it.

- Python engine, **standard library only** at the core (the rule the FreeCAD sibling project records as its ADR 0004: zero
  dependencies, zero supply-chain surface; enforced here by `tools/check_core_imports.py`); `ezdxf` isolated in the DXF layer.
- Ollama over its local HTTP API, transparent auto-start, model-agnostic.
- **Two distinct stages, deliberately different in nature:**
  - *reasoning* — free text, unconstrained length, the model interprets, weighs, decides;
  - *commitment* — forced JSON, validated against the catalogue, refused if it does not fit.
- Defaults resolved from memory; whatever is still missing becomes a question.
- Bounded self-correction: errors go back to the model, fixed number of attempts, no loops.
- **Model-scalable from the start** *(principle 9, §10 of the summary)*: the reasoning stage uses
  whatever model is present and gets better with a bigger one; the drafting stage is identical for
  all. Support for using different models for different stages.

**Finished when.** "A 5x4 room with 30 walls, a door east and two windows south" becomes a correct
drawing from a small local model — and the same request to a larger model produces visibly better
reasoning, with identical precision.

---

## PHASE 6 — Eyes, and editing what already exists

The half of the job that is most of the job.

- Aggregated perception: by layer, by type, by area, plus extents, units, scale, blocks. Never
  entity by entity — real drawings hold tens of thousands.
- Selection semantics in the language: "every external wall", "all ground-floor doors".
- Cross-cutting edits: "walls from 30 to 25", "move all doors 10 cm in".
- Reading questions: areas, counts, lengths, compliance.
- Feasibility checking and nonsense tolerance.

---

## PHASE 7 — Questions, briefing, session memory

- **Deterministic questions**: generated by the engine with a proposed default, so they work with
  any model. Never a pop-up, hard cap per request.
- **Briefing**: before a long job, everything unknown is asked **up front, once**.
- **Session memory**: "the north wall I just drew" resolves in the next sentence.
- Every answer feeds phase 4. This is the flywheel.

---

## PHASE 8 — Project gear

- Propose the approach, decompose into ordered features, then per feature plan → execute →
  re-perceive → replan on failure.
- One feature = one undo step.
- **Preview before commit**: ghost geometry on a temporary layer, "like this?"
- Explicit bounds on features and retries; cancellation honoured at every checkpoint.

---

## PHASE 9 — The design conversation *(rung 4 begins here)*

**Goal.** The agent stops executing and starts designing.

- Propose two or three approaches with the trade-off of each stated plainly.
- Say what the brief is missing or where it contradicts itself.
- Argue for a choice, and accept being overruled without sulking or capitulating.
- Criticise its own proposal before the user has to.
- Hold the conversation *before* drawing: a paragraph of argument costs seconds, a wrong drawing
  costs hours.

**Finished when.** Given a vague brief, the agent comes back with real alternatives and a
defensible recommendation rather than a guess.

**Risk.** Model-dependent by nature. Degrades gracefully: a small model proposes one option and
says so; a larger one argues. Never blocked, never faked.

---

## PHASE 10 — Memory, layer 2: the judgement

**Goal.** Learn the user's trade, not just their settings.

- Record accepted and rejected proposals **with the reason given**.
- Record recurring solutions as reusable typologies.
- Record the criteria by which the user calls a drawing good.
- Retrieval by situation, not by keyword alone: the hard part *(open issue E)*.
- Same guarantees as layer 1: readable, editable, exportable, never weights.

**Finished when.** The agent reuses a past decision correctly in a new drawing, and can say *why*
it did.

---

## PHASE 11 — Delegation: the long jobs

- **The huge drawing** — generative, checkpointed, the script grows.
- **Forty variants** — parametric: one script plus a parameter table.
- **Dimension or standardise an existing drawing** — analytic: reads, proposes corrections in bulk.
- Job state persisted on disk: plan, completed features, decisions, pending questions.
- Exact resume after interruption, crash or reboot. Clean interruption leaves no half drawings.
- Inspectable progress throughout.

**Finished when.** A job of tens of minutes is interrupted halfway, everything closed, and it
resumes exactly where it was.

---

## PHASE 12 — Verification and critique

Two different things, both needed *(principle 13)*.

- **Geometric verification** (deterministic): open contours, duplicates, zero-length segments,
  wrong layer, text out of scale, dimensions not matching their geometry, hatches on open contours.
  Automatic repair of safe cases.
- **Design critique** (judgement against criteria) *(open issue F)*: does the layout work, is the
  part manufacturable, does it meet the norm, is anything missing. Criteria come partly from
  standards, partly from memory layer 2.
- Both are useful **on their own**, on drawings made by other people.

---

## PHASE 13 — Domain vocabularies

Each domain a separate module, loaded only when needed so the prompt never outgrows a small model.

- **Geometry and mechanical**: holes, slots, dimensioned contours, views, chamfers, tolerances.
- **Architecture**: walls with thickness and junctions, openings that cut the wall, rooms and
  areas, standard hatches, print scales.
- **Civil**: profiles, sections, gradients, spot levels.
- **Schematics and services**: symbol libraries as blocks, connections, legends, numbering.
- **Annotation** across all: text, title blocks, tables, legends.

---

## PHASE 14 — The LibreCAD live window (C++ plugin)

- Non-modal panel, TCP loopback bridge with token, JSON-RPC 2.0. Deliberately dumb.
- Perception of the open document and the selection; primitives; undo per feature; on-screen
  highlighting for previews and disambiguation.
- Resolve *(open issue H)*: panel persistence after `execComm`, binary compatibility with official
  builds (Qt 6, CMake, MSVC 2019+), prebuilt binaries per platform via CI.
- **Command-line channel** as the safety net for users who cannot install the plugin.
- Propose `addDimension` and `addHatch` upstream to LibreCAD — long lead time, worth starting early
  even though the product no longer depends on it.

**Risk.** The Windows toolchain. If impassable the product still works — which is precisely why
this phase is here and not first.

---

## PHASE 15 — Non-text input

*(open issue D)* Photographed hand sketch, old PDF plan, scan → clean DXF. 2D is exactly where
vision models work, and this may be the most useful capability of all. Additive, not foundational.

---

## PHASE 16 — Standards, scales, printing

Representation scales and their consistency with text heights and dimensions; ISO/UNI dimension and
hatch styles; line weights and types per layer; parametric title blocks and tables; paper space and
print layouts.

---

## PHASE 17 — Testing, robustness, release

- Headless suite running without any CAD and without Ollama.
- Automated harness over real pilot cases, one per domain.
- Testing across model sizes — explicitly measuring **where each rung of the ladder becomes
  reachable**, since the ceiling rises with the model.
- CI producing plugin binaries for three platforms.
- Installers, documentation, test guide, demo video.
- Public release on GitHub; announcement to the LibreCAD and wider CAD communities.

---

## Sequence at a glance

```
  0 Foundations
  │
  ├─► 1 THE LANGUAGE ──────┐   (design risk: the bridle is decided here)
  ├─► 2 Geometry solver ───┤   (parallel: pure maths)
  └─► 3 DXF in/out ────────┘
            │
            ▼
        4 Memory: the standard
            │
            ▼
        5 THE BRAIN (free reasoning + guided hand)
            │
            ├─► 6 Eyes and editing
            ├─► 7 Questions and briefing
            └─► 8 Project gear
                      │
                      ├─►  9 DESIGN CONVERSATION ──► 10 Memory: the judgement
                      ├─► 11 Delegation
                      └─► 12 Verification and critique
                                │
                                ├─► 13 Domains
                                ├─► 14 LibreCAD plugin
                                ├─► 15 Non-text input
                                └─► 16 Standards and printing
                                          │
                                          ▼
                                    17 Release
```

Rungs of the ladder: **1–5 = hand**, **4 + 7 = apprentice**, **8 + 11 = assistant**,
**9 + 10 + 12 = designer**.

---

## Working rules

- **Frozen decisions go into numbered ADRs.**
- **Persistent memory** in `project_context.md`, updated at every checkpoint.
- **Language**: the whole project is in **English**. Only the live conversation with Marco is in
  Italian, in plain words, commands one at a time, ready to paste.
- **Documents are updated in place, never renamed.**
- **Headless tests always green** before a phase is declared finished.
- **Real validation by Marco** before moving on.
- **Never optimise for Marco's machine or model**: they are the test bench, not the target — and no
  design decision may assume a small model is all there will ever be.
- **`PROMPT.md` is the standing session prompt**; it replaced the rule that every session
  writes the prompt for the next one, which now applies only while the workbench is unfinished.

---

<!-- BEGIN TASK INDEX: generated by tools/sync_plan.py write; do not edit by hand -->

## Task index

Generated from `state/backlog.json`. Status is not shown here: run `python tools/loop.py status`.

### Phase 0 — Foundations and contracts

- `P0-T01` Decide the licence and record it in an ADR
- `P0-T02` Write ADR 0001 - thinking is free, the hand is guided
- `P0-T03` Write ADR 0002 - the memory model
- `P0-T04` Lay out the monorepo directories with their contracts — after `P0-T02`
- `P0-T05` Prove CI green on Windows, macOS and Linux

### Phase 1 — The language

- `P1-T01` Specify the commitment form: fields and closed value lists — after `P0-T02`, `P0-T04`
- `P1-T02` Design the script language: readable, correctable, re-runnable — after `P1-T01`
- `P1-T03` Make design intent and alternatives expressible — after `P1-T02`
- `P1-T04` Answer the blank page in the grammar — after `P1-T02`
- `P1-T05` Design the escape hatch and its boundary — after `P1-T02`

### Phase 2 — The geometry solver

- `P2-T01` Primitives and exact intersections — after `P1-T02`
- `P2-T02` Offsets, trim, extend, fillet, chamfer, tangents — after `P2-T01`
- `P2-T03` Contour closure, exactly — after `P2-T01`
- `P2-T04` Distributions and notable points — after `P2-T01`

### Phase 3 — The drawing: DXF in and out

- `P3-T01` Write real DXF: geometry, layers, weights, dimensions, hatches — after `P2-T03`
- `P3-T02` Read a drawing somebody else made — after `P3-T01`
- `P3-T03` Safe round-trip: change one thing, lose nothing — after `P3-T02`
- `P3-T04` Close the two open render defects: colour 7 and hatch patterns — after `P3-T01`

### Phase 4 — Memory, layer 1: the standard

- `P4-T01` The memory store: plain text, provenance, dates, three levels — after `P0-T03`
- `P4-T02` Channel 1: the short first-run interview — after `P4-T01`
- `P4-T03` Channel 3: deduce the standard from the user's own drawings — after `P3-T02`, `P4-T01`
- `P4-T04` One script, two profiles, two correctly different drawings — after `P4-T03`, `P3-T01`

### Phase 5 — The brain: free reasoning, guided hand

- `P5-T01` Talk to Ollama: free reasoning and forced JSON, transparently — after `P1-T01`
- `P5-T02` The first sentence that becomes a drawing — after `P5-T01`, `P3-T01`, `P4-T01`, `P2-T03`

### Phase 6 — Eyes, and editing what already exists

- `P6-T01` Aggregated perception, never entity by entity — after `P3-T02`
- `P6-T02` Selection semantics and cross-cutting edits — after `P6-T01`, `P1-T02`

### Phase 7 — Questions, briefing, session memory

- `P7-T01` Deterministic questions with proposed defaults — after `P4-T01`
- `P7-T02` Briefing before a long job, and session memory — after `P7-T01`

### Phase 8 — Project gear

- `P8-T01` Decompose a goal into ordered features and replan on failure — after `P6-T02`, `P7-T02`
- `P8-T02` Preview before commit: ghost geometry, 'like this?' — after `P8-T01`

### Phase 9 — The design conversation

- `P9-T01` Propose alternatives with their trade-offs — after `P5-T02`, `P1-T03`
- `P9-T02` Argue, accept being overruled, and self-critique first — after `P9-T01`

### Phase 10 — Memory, layer 2: the judgement

- `P10-T01` Record accepted and rejected proposals with their reasons — after `P9-T02`, `P4-T01`
- `P10-T02` Retrieve by situation, not by keyword alone — after `P10-T01`

### Phase 11 — Delegation: the long jobs

- `P11-T01` Long jobs: state on disk and exact resume — after `P8-T01`
- `P11-T02` The three shapes of long job — after `P11-T01`

### Phase 12 — Verification and critique

- `P12-T01` Geometric verification, deterministic — after `P3-T02`, `P2-T03`
- `P12-T02` Design critique against criteria — after `P12-T01`, `P10-T01`

### Phase 13 — Domain vocabularies

- `P13-T01` Domain vocabularies, loaded only when needed — after `P1-T01`, `P5-T02`

### Phase 14 — The LibreCAD live window (C++ plugin)

- `P14-T01` The C++ plugin and its loopback bridge — after `P6-T01`
- `P14-T02` The command-line channel as the safety net — after `P3-T01`

### Phase 15 — Non-text input

- `P15-T01` Sketch, PDF or scan becomes clean DXF — after `P3-T01`

### Phase 16 — Standards, scales, printing

- `P16-T01` Scales, standards and printing, consistently — after `P3-T01`, `P4-T01`

### Phase 17 — Testing, robustness, release

- `P17-T01` Pilot cases, model-size testing, and where each rung becomes reachable — after `P12-T02`, `P13-T01`
- `P17-T02` Installers, documentation and public release — after `P17-T01`, `P14-T01`

<!-- END TASK INDEX -->
