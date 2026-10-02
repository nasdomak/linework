# ADR 0011 — Drafting operations: exact, and refused when ambiguous

- **Status:** accepted
- **Date:** 2026-10-02
- **Builds on:** ADR 0010 (exact numbers, no tolerance in geometry)
- **Backlog:** P2-T02
- **Code:** `geometry/ops.py`
- **Verified by:** `tests/test_geometry_ops.py`

## Context

Offset, trim, extend, fillet, chamfer and tangent are what a draughtsman does a
hundred times a day. A model that approximates them puts small errors exactly
where a drawing is checked: at tangent points, at corners, at the ends of
lines. Each operation also has a question a human answers by looking (which
side? which piece? does it fit?), and a program that guesses that answer is
worse than one that asks.

## Decision

1. **Tolerance policy: none, for every operation.** All of them compute on the
   exact numbers of ADR 0010. A result is exact or it is not produced.
2. **Ambiguity is refused with the reason** (`OperationRefused`), never
   settled by a hidden rule:
   - a trim pick that falls exactly on a cut point ("say which side");
   - a fillet or chamfer whose segment runs through the corner ("say which
     part to keep");
   - parallel segments (no corner), a radius or distance that does not fit
     the segment ("too short", with both lengths), an inside offset not
     smaller than the radius, a non-positive distance;
   - a cutter that lies along the shape (no single cut point), nothing that
     cuts at all, a boundary an extension never meets.
3. **What each operation means**, fixed here:
   - `offset`: segments to the `left` or `right` of the direction p -> q;
     circles and arcs `outside` or `inside`. The offset of an ellipse is not an
     ellipse, so it is refused as `NotSupported` rather than approximated.
   - `trim(shape, cutters, pick)`: the pick names the piece to *remove*; it is
     projected onto the shape (a click need not be on the line), and the
     remaining pieces come back in order.
   - `extend`: a segment from end `p` or `q`, an arc from its `start`
     (clockwise) or `end` (counter-clockwise), to the *first* boundary hit,
     never wrapping past its own other end.
   - `fillet(a, b, r)` and `chamfer(a, b, d1, d2)`: the corner is where the two
     carrier lines meet; each segment keeps its far end and is trimmed, or
     extended, to the tangent or chamfer point. Any angle, acute or obtuse.
   - `tangents_from_point` and `tangents_between`: every tangent, with its
     touching points; a touching pair of circles gives the one tangent at the
     touching point; the same circle twice is refused (infinitely many).

## Consequences

- Fillets between a segment and an arc, or between two arcs, are not in this
  version; they will be added when a task needs them, on the same rules.
- The pick of a trim is a point, so the conversation layer has to turn "remove
  the bit between the two holes" into one; that is phase 6's job, not this
  module's.

## How it is verified

`tests/test_geometry_ops.py`, 15 tests: every operation on hand-computed cases
with exact expected values, fillets and chamfers on right, acute (3-4-5),
obtuse and 45-degree (irrational) corners, every refusal above by its message,
and an independent exact check that each common tangent really touches both
circles at right angles to the radius. Breaking the code on purpose in five
places made the tests fail each time.
