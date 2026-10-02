# ADR 0008 — The blank page: anchoring by rule

- **Status:** accepted
- **Date:** 2026-10-02
- **Builds on:** ADR 0001, ADR 0005 (the form), ADR 0006 (the script)
- **Changes:** ADR 0005's catalogue, in one point: the side values `inside` and `outside` are removed
- **Backlog:** P1-T04 (open issue C)
- **Specification:** `docs/SCRIPT.md`, "Where the first object goes, and what 'next to' means"

## Context

In 3D you grow from the origin. In 2D "a 5 x 4 room" has no obvious *where*, and
"next to it" has no obvious *side*. If the answer is improvised at run time, the
same sentence can give two drawings, and the model has a hidden way to choose a
number. The answer must be in the grammar, the same every time, and anything it
cannot settle must be refused, not guessed.

## Decision

1. **The first object goes `at origin`**, the point (0, 0) of the sheet.
2. **One frame: the sheet.** x right, y up. `left`, `right`, `above`, `below`
   are sheet directions, never relative to an object's own rotation.
3. **Reference points by shape**: lower-left corner for rectangular things,
   centre for round things and symbols, baseline start for text, axis start for
   straight things (catalogue, `reference_points`).
4. **Every relation names its reference frame** in the catalogue: a `frame`
   sentence (what of the target it measures from) and `fixes` (which part of the
   object's position it fixes: `x`, `y`, `across`/`along` an edge or a long axis,
   or the `axis` it names, each *firm* or *default*). The catalogue check refuses
   a relation without them. `next to X on side S` touches X's edge on side S --
   firm across it, and by default flush at the left (above/below) or bottom
   (left/right) along it; `offset from` is the same with a gap; `on` and `inside`
   fix nothing.
5. **"Beside", "by", "adjacent to"** are not words of the language: they are
   committed as `next to`, which always names its side. No side said, the model
   asks.
6. **Each direction decided exactly once.** For each object, left-right and
   up-down are each governed by one relation: the firm one, or else the only
   default. Nothing deciding a direction ("not determined", "has no place"), two
   firm relations ("fixed twice"), and two defaults with no firm one ("suggested
   twice") are refused with the line and the relations involved. So are a
   direction that depends on an unknown one (distributing over a square plate),
   an object placed by an undetermined one, and a removal that leaves objects
   without what placed them.
7. **The sides `inside` and `outside` are removed.** They name no edge: "15 mm
   on side inside of the plate" fits four edges. Measuring from a named edge is
   queued as D-003 for phase 2.

`lang/anchoring.py` applies these rules to a sound script (it validates first)
and returns, per object and direction, the governing relation. The numbers are
computed by `geometry/placement.py` -- the second door -- in exact fractions of a
millimetre, for `at`, `centred on`, `next to`, `offset from`, `aligned with` and
the `inside` check, and printed in one canonical text. `along`, `between`,
`distributed over` and corner features are determined by the rules here but
computed by the phase-2 solver (queued as D-002); asked for them now, placement
refuses rather than guesses.

## Consequences

- Three examples in `docs/SCRIPT.md` written before these rules were
  ambiguous -- a column with no up-down place, a junction "on a wire" with no
  point, holes "15 mm inside" with no edge -- and passed silently. They are
  corrected, and every sound example is now proved to be one drawing.
- A change that gives relations replaces the object's relations; dimensions and
  properties given in a change are merged.
- In the v1 catalogue every default comes with a firm fix on the other axis, so
  "suggested twice" shows up first as "fixed twice"; the rule is tested on a
  modified catalogue so it holds when the vocabulary grows.

## Verification

`tests/test_anchoring.py` (P1-T04): a coordinate-free script gives
byte-identical placement twice, equal to the text `docs/SCRIPT.md` quotes; a
second one matches a hand computation exactly; units convert exactly
(0.1 m + 0.2 m = 0.3 m); `inside` is checked; every `linework-unplaced` example of
the specification is refused with its stated error and every sound example is
determinate; open choices are not anchored; invalid scripts report validation
errors; every relation's frame is in the catalogue and in `docs/CATALOGUE.md`.
Breaking the gap, the flush default, the reference point, the fixed-twice rule,
the default rule, the validate-first rule or the removal check on purpose makes
the suite fail.
