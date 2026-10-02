# ADR 0013 — Distributions, notable points, and edges as targets

- **Status:** accepted
- **Date:** 2026-10-02
- **Builds on:** ADR 0008 (anchoring), ADR 0010 (exact numbers)
- **Settles:** decision D-003 (taken as the reversible default, Marco not having answered)
- **Backlog:** P2-T04
- **Code:** `geometry/distribute.py`, `geometry/notable.py`, edge targets in
  `shared/catalogue_v1.json` (block `edges`), `lang/form.py`, `lang/script.py`,
  `geometry/placement.py`
- **Verified by:** `tests/test_distributions.py`

## Context

Distributing by count or by pitch is most of the tedium the agent is meant to
remove, and it is where hand work goes wrong: a pitch that does not divide the
length, a last gap quietly stretched, a bolt circle at 72 degrees typed as
0.309. Dimensions, in turn, need named points to attach to. And D-003 asked how
a user says "15 mm in from the top edge of the plate": the script had no way to
measure from one edge of an object.

## Decision

1. **Distributions are exact, and their leftover is reported, never absorbed.**
   `along` a segment by count (ends `include` or `exclude`), by pitch (ends
   `start` or `centred`), or both (refused when they do not fit, with both
   lengths); `on_circle` by count or by a rational pitch in degrees, positions
   from the exact cosine of a rational part of a turn (cyclotomic polynomials,
   so 72 degrees is (sqrt 5 - 1) / 4, not 0.309); `grid` and `grid_in`. Each
   returns the points, the pitch, the leftover and the rule applied.
2. **Notable points are named.** Segments: start, end, mid. Circles: centre and
   the four quadrant points. Arcs: centre, start, end, mid and the quadrant
   points on them. Ellipses: centre and the four vertices. Placed rectangles:
   centre, four corners, four edge midpoints. A dimension will say what it
   measures ("plate1 top_left"), never a coordinate.
3. **A target may name an edge or a corner** (D-003): `offset from plate1 top
   by 15 mm on side below`. The words are a closed block of the catalogue,
   each with its meaning. Only the relations that measure from a place take
   them (`at`, `centred on`, `next to`, `offset from`, `aligned with`; the
   catalogue flag `edge_targets`); `inside plate1 top`, an unknown edge word,
   and `origin top` are refused with their reasons. An edge is measured as a
   zero-thickness strip of the object, a corner as a point, so the existing
   anchoring rules apply unchanged.

## Consequences

- Distributing *script objects* by relation (`distributed over`, `along`,
  `between`) is not here: it is P2-T05 (decision D-002), which uses these
  functions.
- Angles that are not rational parts of a turn have no exact cosine in this
  module; a distribution asked for at such a pitch would be refused. Drawings
  use rational degrees.

## How it is verified

`tests/test_distributions.py`, 15 tests: counts, pitches, leftovers and both
end rules on hand-computed cases, an irrational length, circles of 4, 5, 6 and
8 points and a 7.5-degree pitch checked exactly (every point exactly on the
circle), grids, notable points of every shape, and holes placed from named
edges and corners on hand-computed coordinates, with the round trip of the
script and every refusal. Breaking the code on purpose in seven places made
the tests fail each time.
