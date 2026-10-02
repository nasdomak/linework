# ADR 0014 — Every relation computed exactly

- **Status:** accepted
- **Date:** 2026-10-02
- **Builds on:** ADR 0008 (anchoring), ADR 0013 (distributions, edges)
- **Settles:** D-002 (this task exists); applies the defaults of D-004 and D-005,
  both still open for Marco and reversible
- **Backlog:** P2-T05
- **Code:** `geometry/placement.py`, `lang/anchoring.py`
- **Verified by:** `tests/test_place_relations.py`

## Context

Phase 1 decided *which* relation fixes each direction of every object and
computed five of them. `along`, `between`, `distributed over` and the corner
features (fillet, chamfer) were left raising "placed by the solver of phase 2".
Without this task nothing in the plan would ever compute them.

## Decision

1. **`along X [on side S]`** places a straight thing (wall, road, pipe, wire,
   line): against X's edge on side S, outside X, or on X's long axis when no
   side is named; it starts where X starts and runs X's whole length unless it
   gives its own. Its width across is its thickness (wall), width (road) or
   diameter (pipe); a wire or a line has none.
2. **`between A and B`** spans a straight thing from A's reference point to B's
   (centres of round things and symbols). **D-005 (default):** when A and B are
   rectangles touching along an edge, the axis is that shared edge -- a wall
   between two rooms straddles their common wall line, centred; rectangles that
   share no edge, or touch only at a corner, are refused. Anything that is not
   straight is refused with the reason ("between" means spanning).
3. **`distributed over X in N copies`** -- **D-004 (default):** N copies along
   X's long axis, N + 1 equal spaces between X's ends and the copies' centres
   (4 holes over 200 mm: 40, 80, 120, 160); across, centred on X unless another
   relation fixes it. Copies that would overlap are refused, with the pitch.
   Each copy is listed (`name.1`, `name.2`, ...).
4. **Corner features** take the square of side *radius* (fillet) or *length*
   (chamfer) out of the host's named corner, or out of all four; a feature
   that does not fit the host (more than half the shorter side when all four
   corners are taken) is refused. The arc itself is the one `geometry.ops`
   computes from the two edges.
5. **`on` checks**, as SCRIPT.md always said it would: an object on a host must
   lie on it. The check found a real error in SCRIPT.md: the bracket's slot ran
   4 mm off the bottom of its plate; the example now offsets it 10 mm, not 20.
6. **A size is never invented.** An object whose size is not in the script
   raises `SizeNotKnown`, naming the dimension and where it will come from (the
   drawing standard in memory, phase 4). Straight things are listed a second
   time in an `AXES` section of the placement text: start, end and width.

## Consequences

- Of SCRIPT.md's examples, the mechanical bracket now places in full. The
  architecture, civil and schematic ones stop at sizes the standard will give
  (a wall's thickness, a parking bay, a schematic symbol), each named.
- Objects hosted on a wall (windows, doors) still need their size across the
  wall from the wall itself; that comes with the drawing, phase 3.

## How it is verified

`tests/test_place_relations.py`, 16 tests: every relation on hand-computed
cases (the civil example placed in full, rooms with their shared wall, a
slanted wire, distributions over horizontal and vertical plates, the bracket's
holes, all four fillets and a chamfer), the fillet square checked against
`geometry.ops.fillet`, every refusal, the `on` check, byte-identical output, and
a check that every position-fixing relation in the catalogue is computed.
Breaking the code on purpose in eight places made the tests fail each time.
