# ADR 0002 — The memory model

- **Status:** accepted
- **Date:** 2026-09-30
- **Source:** brainstorming sessions 1–3 (16/09/2026), `docs/BRAINSTORMING_SUMMARY.md` §5, §6, §11
- **Backlog:** P0-T03 (this ADR); implemented by P4-T01..T04 and P10-T01..T02

## Context

The program ships **empty** and must learn its user. An agent that has to ask
about everything is not working for you; it is making you its secretary.

Two kinds of knowledge are involved, and they are not the same thing. Remembering
that external walls are 30 cm is remembering a *setting*. Remembering that the
user rejected a 110 cm corridor because a wheelchair must pass is learning a
*trade*. The first makes an apprentice; only the second makes the rung-4 designer
this project is aimed at. The shape of the memory has to be fixed before anything
writes to it, because every later phase reads or feeds it.

## Decision

### Two layers

1. **Layer 1 — the standard** (the draughtsman's memory). Values: thicknesses,
   layer names, line weights, colours, text heights, dimension styles, the scales
   actually used.
2. **Layer 2 — the judgement** (the designer's memory). How the user solves
   problems: the typologies they reach for, the proposals they accepted or rejected
   **and the reason they gave**, the criteria by which they call a drawing good.
   Reasoning, not results. This is the case library a designer reasons from, and
   what makes rung 4 reachable.

### Three levels, nearest wins

```
program defaults  →  the user's profile (always)  →  the current project (here only)
```

The nearest level wins. **A conflict between levels is reported, never silent**:
the agent says which rule it applied and which one it overrode.

### Three fill channels

1. **The short first-run interview.** At most five or six questions — the ones
   without which nothing can be done — each with a proposed default. It can be
   skipped entirely and the program still works. Then it stops.
2. **Learning while working.** Every answered question becomes a rule; every
   hand-corrected script line is offered as a rule ("shall I make this a rule?");
   every accepted or rejected proposal feeds layer 2, together with its reason.
3. **Deduction from the user's own drawings.** Given a few of the user's DXF files,
   the program reads their standard out of them: layer names, weights, colours,
   text heights, dimension styles, real scales. More accurate than what anyone
   would say out loud — nobody can recite their own standard, they just draw it.
   The user then corrects the two lines that came out wrong.

### Format: plain text, one line one decision, with provenance and date

```
external walls: thickness 30        (deduced from your drawings, 12/03/26)
text at 1:50: height 2.5            (answered by you, 14/03/26)
corridors: never below 120          (you rejected 110 on 03/04/26, reason: wheelchair)
dimension style: ISO                (program default)
```

- **Provenance** says what to trust: program default, answered by you, deduced from
  your drawings, learned from a correction, reason you gave.
- **The date** matters because decisions age. A year later the agent can ask "I am
  using a rule from last March — does it still hold?" instead of applying it blindly.
- It stays human-readable after any number of writes. No database, no vector store:
  retrieval of layer 2 by situation (open issue E, P10-T02) must be solved without
  giving up readability.

### Privacy — a hard requirement

- Stored **outside the program folder**, so an update or reinstall cannot wipe it.
- **No sync, no telemetry.** Nothing leaves the machine.
- **Hand-exportable**: copy a folder to move to a new PC, keep a backup, or hand
  one's standard to a colleague.
- **Never model weights.** It is a file, so deleting it actually deletes it — there
  is no fine-tuned model that silently remembers.

### The script-versus-memory separation rule

**The script says *what*; the memory says *how*.**

```
external wall: from A to B
```

The thickness is not in the script; it is in the memory.

**The script carries only what is specific to this drawing. Anything that is "I
always do it this way" belongs in the memory.** A number repeated identically
across twenty script lines is in the wrong place.

## Consequences

- **Scripts stay short and readable**, not stuffed with repeated numbers.
- **Change one rule and everything realigns.** Walls from 30 to 25 in the memory,
  re-run, and the whole project updates: parametric at the level of the office,
  not of the file.
- **Scripts are transferable.** Hand one to a colleague and it comes out in *their*
  standard. P4-T04 proves this: one script, two profiles, two correctly different
  drawings.
- **Learning is natural.** A correction to a script line is a diff the agent can
  see and offer as a rule; it never has to guess what it was taught.
- **Layer 2 is harder than layer 1** and is deliberately scheduled later (phase 10),
  after the design conversation (phase 9) exists to produce accepted and rejected
  proposals worth remembering.
- The memory module (`memory/`) imports nothing outside the standard library.

## Verification

`tests/test_repo_shape.py` asserts that this ADR exists and names both layers and
all three channels. The behaviour is tested from phase 4 on: resolution order and
conflict reporting (P4-T01), the capped interview (P4-T02), deduction from a
synthetic drawing with a known standard (P4-T03), and two profiles producing two
correctly different drawings (P4-T04).
