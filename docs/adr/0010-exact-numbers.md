# ADR 0010 — Exact numbers in the solver: algebraic, never floats

- **Status:** accepted
- **Date:** 2026-10-02
- **Builds on:** ADR 0001 (numbers enter through two doors: dictated or computed)
- **Backlog:** P2-T01
- **Code:** `geometry/exact.py`, `geometry/primitives.py`
- **Verified by:** `tests/test_geometry_primitives.py`

## Context

The solver is the second door through which numbers enter a drawing. If it
computes with floats, a line meeting a circle at 1 + sqrt(3) becomes
2.7320508075688772, the next construction starts from that, and "a contour
closes exactly" turns into "closes within a tolerance somebody picked". Every
later operation -- trim, fillet, closure, hatching -- would inherit the doubt.
Phase 1 already places objects in exact fractions of a millimetre
(`geometry/placement.py`); intersections need square roots and, for two
ellipses, roots of a quartic, which no fraction holds.

## Decision

1. **Every number in the solver is exact.** It is either a Fraction or a real
   algebraic number written as g(a), an element of the field Q(a), where a is
   the one root of a square-free rational polynomial inside a rational
   isolating interval (`geometry.exact.Num`). Sums, products, quotients and
   square roots stay exact; numbers from two different fields are combined in
   their common field (a primitive element, built by a resultant), and a field
   remembers the fields it contains so it is never rebuilt.
2. **Comparisons are decided, not estimated.** Zero is recognised exactly (a
   gcd with the field's polynomial, splitting the polynomial when it factors);
   a non-zero sign is found by shrinking the interval until it is certain. So
   two curves are tangent or they are not; a point is on a segment or it is not.
3. **The tolerance policy is: there is no tolerance in geometry.** No epsilon
   appears in `geometry/`. Decimals exist only at the end, on request,
   correctly rounded (`Num.decimal(digits)`); floats only through `float()`.
   Floats are refused as input -- `0.1` is not one tenth -- and numbers enter
   as int, Fraction or a decimal string.
4. **Degenerate shapes are refused when they are made**, with the reason: a
   zero-length segment, a radius not greater than zero, an ellipse ratio
   outside (0, 1], an arc whose start and end directions coincide (empty, or
   the whole curve: say which by using the full curve).
5. **Degenerate meetings are reported, not hidden.** `intersect(a, b)` returns
   the points (each marked tangent or not), the pieces two shapes share when
   they lie on one carrier (collinear segments, arcs of one circle or ellipse),
   and notes naming what was met: `parallel`, `collinear`, `tangent`,
   `concentric`, `coincident`, `outside` (the carriers meet, the pieces do not).
6. **Arcs are given by directions, not angles.** An arc runs counter-clockwise
   from a start direction to an end direction, both vectors from the centre.
   Directions with rational components keep everything rational where it can
   be; "30 degrees" has no exact rational direction, and how angles are
   dictated is left to the script (a later task), not guessed here.
7. **Ellipses are DXF-style**: centre, semi-major axis as a vector, minor/major
   ratio. With rational inputs the implicit equation has rational
   coefficients, so a line meets it at a square root and two conics meet at
   roots of a rational quartic, both exact.

## Consequences

- Two conics with irrational equations (an ellipse whose centre was itself
  computed as a square root) are refused with `NotSupported`, naming the
  limit, rather than solved approximately. Circles, lines and segments work
  with any exact inputs, irrational included.
- Exact arithmetic is slower than floats. Measured on 02/10/2026: the whole
  intersection test file runs in about five seconds in the cloud container,
  the slowest case (a rotated ellipse against a circle, a degree-4 field)
  under three. Drawings have hundreds of entities, not millions; correctness
  wins. If it ever matters, the place to optimise is `geometry/exact.py`, not
  the callers.
- Later operations (offsets, trims, fillets, closure) inherit exactness for
  free: they build on `Num` and on these intersections.

## How it is verified

`tests/test_geometry_primitives.py`: all fifteen pairs of point, segment, arc,
circle and ellipse on hand-computed cases with exact expected values
(rationals and square roots compared with `==`), every degenerate case above,
symmetry of every pair, a rotated-ellipse quartic checked by substituting the
points back into both equations with zero remainder, and the resultant against
the product formula (including a case that needs a row swap). Breaking the
code on purpose in five places made the tests fail each time.
