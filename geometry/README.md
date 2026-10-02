# `geometry/`

The solver: relations and dictated numbers become exact coordinates.

The second of the two doors through which numbers enter (ADR 0001). Pure computation, no I/O beyond what the standard library offers.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library (no numpy, no sympy); dxf; tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `geometry/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".

## What is here

- `placement.py` -- exact positions from anchoring decisions (ADR 0008): at,
  centred on, next to, offset from, aligned with, and the inside check, in
  fractions of a millimetre, with one canonical text per drawing. Works on plain
  records; imports nothing from `lang/`.
- `exact.py` -- exact real numbers (ADR 0010): Fractions and real algebraic
  numbers g(a) in Q(a), with exact `+ - * /`, `sqrt`, comparison and zero test;
  polynomials, Sturm root isolation, resultants. No tolerance anywhere; decimals
  only on request, correctly rounded.
- `primitives.py` -- point, segment, arc, circle, ellipse (and elliptical arc),
  degenerate shapes refused when made, and `intersect(a, b)` for every pair:
  points (tangent or not), shared pieces, and notes naming parallel, collinear,
  tangent, concentric, coincident, outside.
- `ops.py` -- offset, split, trim, extend, fillet, chamfer, tangents from a
  point and between circles (ADR 0011): exact, and refused with the reason
  when the request is ambiguous or does not fit.
