# ADR 0012 — Contours close exactly, or are reported open

- **Status:** accepted
- **Date:** 2026-10-02
- **Builds on:** ADR 0010 (exact numbers), ADR 0011 (drafting operations)
- **Changes:** ADR 0010, point 1 -- see "Change to ADR 0010" below
- **Backlog:** P2-T03
- **Code:** `geometry/contours.py`, `geometry/factor.py`
- **Verified by:** `tests/test_contours.py`, `tests/test_exact_factor.py`

## Context

A hatch, an area, an offset of a profile: all need a closed contour. CAD
programs usually close a contour "within a tolerance", which means a gap of a
hundredth of a millimetre is filled silently and travels into every hatch and
every exported profile. The plan says it plainly: a contour closes exactly, not
almost, and an open contour is reported, never quietly closed.

## Decision

1. **Two piece ends meet only when their exact coordinates are equal.** There
   is no closing tolerance (ADR 0010: none anywhere in geometry).
2. `find_contours(pieces)` chains loose segments, arcs and elliptical arcs,
   in any order and either direction, into **closed contours** -- every
   junction joins exactly two ends -- and returns them walked in order, each
   piece marked when it is walked backwards. Full circles and ellipses are
   closed contours on their own.
3. **Nothing is closed that does not close, and nothing is dropped silently.**
   The report lists open chains with their loose ends; every loose end paired
   with the nearest other loose end and the exact gap between them ("gap of
   0.001000 mm between ..."); branch points where three or more ends meet; and
   pieces given twice. `all_closed` is true only when there is nothing else.
4. **Closure is guaranteed upstream by construction**: the operations of ADR
   0011 hand neighbouring pieces the very same exact point, so a profile built
   by them (fillets and chamfers at irrational corners included) closes with
   zero gap.

## Change to ADR 0010

ADR 0010 let a field's polynomial be any square-free polynomial, split lazily
when a factor turned up. Building the first rounded contour showed the cost: a
square root that was already in the field still doubled it, and a triangle
with two 45-degree fillets reached degree 16 and ran for minutes. **Every field
is now described by the minimal polynomial of its generator**: polynomials are
factored over Q (`geometry/factor.py`: factor modulo a prime, Hensel lifting,
recombination, every factor checked by exact division; the random choices use
a fixed seed, so runs are reproducible). Fields keep their true degree; the
same triangle now stays in Q(sqrt 2) and takes milliseconds. The lazy split
remains as a safety net and costs nothing when the polynomial is irreducible.

## How it is verified

`tests/test_contours.py`: a shuffled, reversed square; a triangle rounded by
three fillets (45, 90, 45 degrees) and a square cut by four chamfers, both
closing with zero gap; a contour off by 1/1000 mm reported open with that gap;
two misses smaller than any float can show (a 30-digit decimal against sqrt 2,
and sqrt 2 against sqrt 2 + sqrt 3 / 10^15) reported open; branches and
duplicates named; mixed pieces and several contours at once.
`tests/test_exact_factor.py`: irreducible polynomials kept whole, products
split into their exact factors, a square root already in a field not growing
it, and the rounded triangle staying at degree 2 in under five seconds.
Breaking the code on purpose (always closing, merging ends by a float
tolerance, ignoring branches, skipping the factoring) made the tests fail each
time.
