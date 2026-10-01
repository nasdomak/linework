# ADR 0007 — Design intent and alternatives in the script

- **Status:** accepted
- **Date:** 2026-10-01
- **Builds on:** ADR 0006 (the script language), ADR 0002 (the memory model)
- **Backlog:** P1-T03
- **Specification:** `docs/SCRIPT.md`, "Open choices"

## Context

Phase 9 is a design conversation: the agent proposes, compares, and waits for the
user to decide. If the script can only hold finished commands, an undecided
design has nowhere to live except the model's head, and "either this or that"
silently becomes "this". The language must carry an open choice, and must make it
impossible to draw one.

## Decision

Two new line shapes, nothing else:

```
choice entrance: open  # Where does the front door go?
option entrance street: add door d1: on wall_south, centred on wall_south, width 90 cm  # closest to the street
option entrance garden: add door d1: on wall_east, centred on wall_east, width 90 cm  # opens on the garden
```

- **`choice <name>: open`** announces a decision not yet taken. The comment is
  the design intent: the question being decided.
- **`option <choice> <label>: <statement>`** is one line of one alternative; an
  alternative may take several lines. A choice has at least two alternatives,
  and its option lines follow it directly (comments and blank lines allowed).
- **`choice <name>: decided <label>`** records the decision; the comment is the
  reason. Deciding changes that one word and nothing else: the alternatives not
  taken **stay in the script**, as the record of what was considered and why it
  was turned down -- the case library of the judgement memory (phase 10).

### Checking

Each alternative is checked on its own, from the drawing as it stands at the
choice. After a decided choice the drawing is the chosen alternative's. After an
open one it holds only what every alternative agrees on: a name that exists, with
the same kind, whichever alternative is taken. So later lines may build on the
common ground of an open choice, and never on one side of it.

### The gate to geometry

`Script.drawable()` is the only way from a script to the statements to draw. It
refuses a script with any open choice, naming each one, its line and its options:

```
line 8: cannot draw: choice "entrance" is still open -- options street, garden; decide it first
```

The solver (phase 2) consumes `drawable()` and nothing else.

## Consequences

- An alternative is a set of whole statements, not a value inside one ("width 90
  or 100"). Choosing between two numbers is written as two alternatives. This
  keeps every line a validated form, at the cost of some repetition.
- Choices do not nest. A choice inside an alternative would make the common
  ground hard to state and hard to read; it can be written as two choices.
- Intent that is not a choice stays a comment or a statement's reason (`#`).

## Verification

`tests/test_intent.py` (P1-T03): the open example of the specification checks
clean yet refuses to be drawn, with exactly the message the specification
quotes; two open choices are both named; the decided example draws exactly the
chosen alternative and what follows it; deciding changes one line and keeps the
alternatives; deciding for a missing choice or option is refused; after an open
choice only the common ground exists; each alternative is checked alone and does
not see the other; malformed choice and option lines name their line. Disabling
the open-choice gate, the common-ground rule, the chosen-option selection, the
per-alternative copy of the drawing or the two-option minimum on purpose makes
the suite fail. The refused examples in `docs/SCRIPT.md` are run by
`tests/test_script.py`.
