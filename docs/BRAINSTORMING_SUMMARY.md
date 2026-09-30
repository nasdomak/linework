> **Copied into the repository on 30/09/2026** from `00_BRAINSTORMING_SUMMARY.md`
> in the kDrive folder, unchanged below this note. It is the record of how the
> architecture was reasoned out; decisions that were frozen since live in
> `docs/adr/`, and where the two differ the ADR wins.

# 2D Design Agent — Architectural Brainstorming Summary

> Sessions 1–3 of brainstorming, 16 September 2026. Supersedes all earlier drafts.
> FreeCAD Agent (`…/000009___Freecad_copilot`) is **read-only reference input** and must never be
> modified.

---

## 1. What this is

**A design partner that learns your trade, thinks about the problem, writes readable recipes, and
executes them without getting a single number wrong.**

The goal is **the drawing and productivity** — not LibreCAD. LibreCAD is one of the windows onto
the work; it is not the protagonist.

The ambition is explicitly larger than a drafting assistant: **over time, this must become an
autonomous designer.** The human remains the decision-maker, but the design thinking is real
thinking, not lookup.

Everything runs **locally**: an open-source model served by **Ollama** on the user's own machine.
No cloud, no telemetry, nothing leaves the PC.

Ambition: **free public open-source release on GitHub** (`nasdomak`), cross-platform.
Domain: **all of 2D** — architecture, civil, mechanical, geometry, schematics.

Marco's directive: aim for the maximum, **completeness is the north star**.

---

## 2. The central distinction: two different jobs

An earlier draft of this document made a serious error — it bridled the *thinking* when only the
*hands* should be bridled. The correction is the foundation of the whole architecture.

**Designing** is deciding *what* to draw: how to lay out a flat, where the load-bearing wall goes,
how a joint resolves, what proportions work, what the brief is missing, whether the request even
makes sense. Here the model must **reason at length, propose, compare alternatives, argue, and
criticise its own work**. No bridle. The longer and better it thinks, the better the outcome.

**Drafting** is putting the exact mark on the sheet. Here creativity is a defect. Here the bridle
lives, and only here.

> **Thinking is free. The hand is guided.**

The validated form is the **last gesture** — the moment a decision already made becomes geometry.
Everything before it is full reasoning.

### The autonomy ladder

"Autonomous designer over time" is a ladder, not a switch. The architecture must make every rung
reachable, and the ceiling must rise with the model — a small model should be an excellent hand,
not a cap on the ambition.

1. **Hand** — executes what you say, never gets a number wrong.
2. **Apprentice** — knows your standard, asks the right questions, proposes sensible defaults.
3. **Assistant** — give it a goal; it decomposes, executes it all, corrects itself.
4. **Designer** — proposes solutions, compares several, argues for them, critiques its own work,
   and learns how *you* solve problems.

Rung 4 is the declared destination, not an afterthought.

---

## 3. Where the agent earns its keep

Saying "draw a line from 0,0 to 100,0" out loud is *slower* than typing it. The agent wins
elsewhere:

1. **Tedium** — thirty steps for a simple thing: dimension a whole part, number fifty rooms, hatch
   twenty areas.
2. **Cross-cutting edits** — "every external wall from 30 to 25", "move all doors 10 cm in".
3. **Understanding** — "how many square metres is this flat?", "does this meet the standard?" — on
   drawings somebody else made.
4. **Translation** — a hand sketch, a PDF, a written spec becomes a proper drawing.
5. **Repetition with variation** — forty variants of the same window.
6. **Design itself** — proposing a layout, resolving a detail, finding what the brief forgot.

Most real CAD work is **editing**, not creating. A plan that is all about creation is looking at
the wrong half of the job.

---

## 4. The bridle: it is the grammar, and it applies to the hand

Checking a model's output afterwards does not work: if it may write `10,20` it may write
`1000,200`, and both are legal. No downstream check saves you.

So at the moment of drawing, the model may not write numbers at all. It states **relations**:

```
window on wall_north, centred, width 120
```

"Centred" has exactly one meaning, computed by our code from the real wall. The model did not avoid
the mistake — **it had no way of making it**.

> **Numbers enter through two doors only: the user dictates them, or the solver computes them.**

This constrains *execution*, never *deliberation*. The model is free to reason about proportions,
to weigh options, to change its mind — and then it commits through a narrow, validated gate.

### The pipeline

```
natural language + the drawing + the memory
   │
   ▼
FREE REASONING          ← the model thinks: interprets, proposes, compares,
   │                       criticises, decomposes, decides. No constraints.
   ▼
design decision          ← discussed with the human when it matters (§6)
   │  the model fills in a form: fixed fields, values from a closed list
   ▼
validated structured intent   ← refused here if it does not fit the catalogue
   │  the ENGINE writes the script (never the model)
   ▼
readable script          ← human can read, correct, re-run, version it
   │  the solver resolves relations into exact coordinates,
   │  defaults taken from the memory
   ▼
geometry (DXF)           ← exact
```

The model never emits executable text, and never a final coordinate. It thinks freely and commits
narrowly.

### Why the script earns its place

It is three things at once: what the agent **will do**, the record of what it **did**, and the
document you can **correct and re-run**. Memory, undo, reproducibility and audit collapse into one
artefact — and the model's mistakes become visible in a line of text instead of hidden in a
drawing.

---

## 5. The memory: two layers, not one

The program ships **empty** and learns its user. An agent that must ask about everything is not
working for you, it is making you its secretary.

### Layer 1 — the standard (the draughtsman's memory)

Thicknesses, layer names, line weights, text heights, dimension styles, the scales actually used.
Values.

### Layer 2 — the judgement (the designer's memory)

**How you solve problems.** The typologies you reach for, the solutions you rejected and *why*, the
criteria by which you call a drawing good, the reasoning behind a decision rather than its result.

Layer 2 is what separates remembering your standard from learning your trade. It is also what makes
rung 4 of the ladder possible: a designer reasons *from cases*, and this is the case library.

### Three channels fill both layers

1. **A short first-run interview** — five or six questions, the ones without which nothing can be
   done. Then it stops. Nobody finishes a sixty-question form.
2. **Learning while working** — every question answered becomes a rule; every hand-corrected script
   line is offered as one; **every proposal you accept or reject feeds layer 2, together with the
   reason you gave.**
3. **Deduction from the user's own old drawings** — feed it three DXF files and it reads your
   standard out of them: layer names, weights, colours, text heights, dimension styles, real
   scales. More accurate than what you would say out loud — nobody can recite their own standard,
   they just draw it. You then correct the two wrong lines.

Channel 3 is one of the strongest ideas in the project and works for anyone who downloads it.

### Form

Plain text, one line one decision, with **provenance and date**:

```
external walls: thickness 30        (deduced from your drawings, 12/03/26)
text at 1:50: height 2.5            (answered by you, 14/03/26)
corridors: never below 120          (you rejected 110 on 03/04/26, reason: wheelchair)
dimension style: ISO                (program default)
```

Provenance tells you what to trust; the date matters because decisions age — a year later it can
ask "I am using a rule from last March, does it still hold?" instead of applying it blindly.

### Three levels, nearest wins

Program defaults → your profile (always) → current project (here only). Conflicts are reported,
never silent.

### Privacy — a hard requirement

Outside the program folder, so an update cannot wipe it. No sync, no telemetry. Hand-exportable for
a new PC, a backup, or a colleague. It stays a **file, never model weights** — so deleting it
actually deletes it.

### How memory and script fit together

**The script says *what*; the memory says *how*.**

```
external wall: from A to B
```

The thickness is not in the script. It is in the memory. Four consequences:

- **The script stays short and readable**, not stuffed with repeated numbers.
- **Change one rule and everything realigns.** Walls from 30 to 25 in the memory, re-run: the whole
  project updates. Parametric at the level of the **office**, not of the file.
- **Scripts become transferable.** Hand one to a colleague and it comes out in *his* standard. The
  recipe is the geometry; the memory is the hand that draws it.
- **Learning becomes natural.** Correct a script line and the agent sees the difference and asks
  "shall I make this a rule?" It does not guess what you taught it — you wrote it by correcting.

Working rule: **the script carries only what is specific to this drawing; anything that is "I always
do it this way" belongs in the memory.** A number repeated identically across twenty lines is in
the wrong place.

---

## 6. The design conversation

Before drawing anything substantial, the agent can **discuss the design**:

- propose two or three approaches and state the trade-off of each;
- say what the brief is missing or where it contradicts itself;
- argue for a choice, and accept being overruled;
- criticise its own proposal before you have to.

This is what a designer does and a draughtsman does not. It is also the cheapest possible place to
catch an error: a paragraph of argument costs seconds, a wrong drawing costs hours.

Every accepted or rejected proposal, with its reason, feeds memory layer 2.

---

## 7. Autonomy: where the human sits

**The agent acts alone on anything that can be undone, and stops only where being wrong is
expensive** — overwriting a file, deleting the user's work, or an assumption that changes
everything downstream *(settled with Marco)*.

Two things keep this honest: a **preview** (ghost geometry on a temporary layer, "like this?" —
cheap in 2D and the practical answer to an unreliable model) and **reversibility** (one feature,
one undo step).

---

## 8. The three gears

- **Direct** — one command: reason briefly, form, script line, geometry.
- **Project** — a whole goal: propose the approach, decompose into features, then per feature plan
  → execute → re-perceive → replan, holding the real geometry each time.
- **Delegation** — a long job handed over and left running: state on disk, checkpoints, resume.

### Delegation: ask before, never during

An eight-hour job only holds up if it does not need you during those eight hours. So the agent
**briefs**: reads the request, works out what it does not know, asks *everything* up front, once.
Then it goes. Those answers land in the memory, so the next briefing is shorter.

Three shapes of long job, three engines behind one handle:

- **The huge drawing** — generative: the script grows, feature by feature, checkpointed.
- **Forty variants** — parametric: one script plus a table of parameters. Nearly free once the
  language exists.
- **Dimensioning or standardising an existing drawing** — analytic: it reads and produces a list of
  corrections you approve in bulk.

---

## 9. Channels onto the drawing

The drawing is the protagonist, so the engine works on **DXF** (via `ezdxf`) as its home ground:
that channel can do everything the format allows, including the dimensions and hatching LibreCAD's
plugin API cannot create at all.

LibreCAD is reached through two further channels, added later because nothing depends on them:

- **A C++/Qt plugin** — the live window: watch it draw, undo per feature, on-screen highlighting,
  perception of the current selection. Deliberately dumb: bridge, eyes, primitives, undo. It is the
  only part compiled for three operating systems, so if a function may change its mind, it does not
  belong there.
- **The command line** — safety net: LibreCAD can load a text file of commands. Blind, but works on
  a stock install.

Because the goal is the drawing, C++ is not the wall that blocks everything at the start. The
product is useful from day one, before the plugin exists.

---

## 10. On the model

Everything is local, via Ollama, model-agnostic, with forced JSON output where structure is needed
and free text where reasoning is needed.

**The system must have a ceiling that rises with the model.** A small model (4B class) is an
excellent *hand*: it never computes a coordinate, so its weaknesses barely show. A larger model is
a *designer*: it proposes, compares and argues. The architecture must be built so the 4B is the
**floor, not the roof** — no design decision may assume a small model is all there will ever be.

Practically: the reasoning stage scales with whatever model is present; the drafting stage is
identical for all of them. Where a step benefits from a different model (long deliberation vs. quick
form-filling), the engine may use more than one.

---

## 11. Founding principles (the constitution)

1. **Privacy-first / local-first.** Everything local by default.
2. **Host CAD untouched.** No forks, no patches. Improvements go upstream as pull requests.
3. **Separate, interchangeable brain.** The engine is its own process; the model is external.
4. **The model acts, it does not ask permission** — within the autonomy rule of §7.
5. **Precision from the closed vocabulary, power from the free channel — but transparent.**
6. **Safety = reversibility.** Human confirmation only where undo cannot help.
7. **Never trust the user.** The agent perceives and checks feasibility.
8. **Correctness before speed.**
9. **Adapt, do not exclude.** Any model; the ceiling rises with it.
10. **Thinking is free, the hand is guided.** Deliberation is unconstrained; commitment goes
    through a narrow validated gate.
11. **The model never invents a number.** It states relations; the user dictates or the solver
    computes.
12. **The model never emits executable text.** It fills a validated form; the engine writes the
    script.
13. **The drawing is verified, and the design is critiqued.** Deterministic geometric self-checks,
    plus judgement against criteria.
14. **The program learns the person** — both the standard and the judgement. Local, readable,
    editable, exportable, with provenance and dates. Never model weights.
15. **Long work is restartable, and asks up front.** Persistent state, checkpoints, exact resume,
    briefing before departure.
16. **The ambition is a designer, not a draughtsman.** Every design decision is measured against
    whether it makes rung 4 of the ladder reachable.

---

## 12. Open issues

- **A. The script language.** Its grammar is the bridle on the hand, so it is the most important
  design artefact in the project. It must also be able to carry **design intent and alternatives**,
  not only finished commands. How rich before it stops being safe?
- **B. The escape hatch.** What happens when something cannot be said in the language. A free
  channel must exist and be visibly flagged — it is the hole in the fence, so its boundary needs
  designing, not improvising.
- **C. The blank page.** In 3D you grow from the origin. In 2D, "a 5x4 room" — *where*? "Add a
  bathroom next to it" — which side? Answer it in the grammar, not at runtime.
- **D. Non-text input.** Photographed hand sketch, old PDF plan, scan → clean DXF. 2D is exactly
  where vision models work; this may be the most useful thing the tool could do.
- **E. Memory retrieval.** Rules always loaded, cases looked up by keyword. No vector database — it
  must stay readable. Layer 2 (judgement) is harder to retrieve than layer 1 and needs design.
- **F. Design criteria.** To critique its own work the agent needs standards to judge against —
  per domain, partly from norms, partly from the user. Where do they come from and how are they
  expressed?
- **G. Project name and GitHub repository.** It is a 2D design agent that speaks DXF and plugs into
  LibreCAD — the name must not corner it.
- **H. Plugin binary compatibility** and panel persistence after `execComm` returns. A late-phase
  problem, not a blocker.

---

## 13. Prior art

The text-to-CAD field is crowded but elsewhere: cloud services, mostly 3D, none inside a CAD the
user already owns. LLM floor-plan generation is active research but academic. The space "local,
free, 2D, learns you, reasons about the design, inside your own CAD" is empty.

---

## 14. Status

Brainstorming complete. Next: `01_ACTION_PLAN.md`, then session 2 per `02_PROMPT_Session2.md`.
