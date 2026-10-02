"""Contour closure, exactly -- verification of backlog task P2-T03 (ADR 0012).

Closed contours are recognised from loose, shuffled, reversed pieces; a contour
built by the solver's own operations (fillets at irrational corners included)
closes with zero gap; a contour that misses by a thousandth of a millimetre,
or by less than any float could show, is reported open with its gap, never
quietly closed.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import sys
from fractions import Fraction as Fr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geometry.exact import sqrt                                    # noqa: E402
from geometry.primitives import Point, Segment, Arc, Circle, Ellipse  # noqa: E402
from geometry.ops import fillet, chamfer                           # noqa: E402
from geometry.contours import find_contours, ends                  # noqa: E402


def polyline(*pts):
    return [Segment(a, b) for a, b in zip(pts, pts[1:])]


def walk_is_continuous(contour):
    """Exact check: each step ends where the next begins (and the last where
    the first begins, for a closed one)."""
    pairs = []
    for piece, rev in contour.steps:
        a, b = ends(piece)
        pairs.append((b, a) if rev else (a, b))
    for (_, b), (c, _) in zip(pairs, pairs[1:]):
        assert b == c
    if contour.closed:
        assert pairs[-1][1] == pairs[0][0]
    return True


def test_a_shuffled_reversed_square_closes():
    s = polyline((0, 0), (10, 0), (10, 10), (0, 10), (0, 0))
    pieces = [s[2], Segment(s[0].q, s[0].p), s[3], Segment(s[1].q, s[1].p)]
    rep = find_contours(pieces)
    assert len(rep.closed) == 1 and not rep.open and not rep.gaps and rep.all_closed
    c = rep.closed[0]
    assert len(c.steps) == 4 and walk_is_continuous(c)
    assert len(c.vertices()) == 4


def test_a_rounded_triangle_built_by_fillets_closes_exactly():
    # corners of 45, 90 and 45 degrees: the tangent points are irrational
    a = Segment((0, 0), (10, 0))
    b = Segment((10, 0), (10, 10))
    c = Segment((10, 10), (0, 0))
    r1 = fillet(a, b, 1)
    r2 = fillet(r1.second, c, 1)
    r3 = fillet(r2.second, r1.first, 1)
    pieces = [r3.second, r1.piece, r2.first, r2.piece, r3.first, r3.piece]
    rep = find_contours(pieces)
    assert rep.all_closed and len(rep.closed) == 1 and not rep.gaps
    contour = rep.closed[0]
    assert len(contour.steps) == 6 and walk_is_continuous(contour)
    irrational = [p for p in contour.vertices() if not p.x.is_rational()]
    assert irrational, "the 45-degree corners must give irrational tangent points"


def test_a_chamfered_square_closes_exactly():
    s = polyline((0, 0), (10, 0), (10, 10), (0, 10), (0, 0))
    k1 = chamfer(s[0], s[1], 2)
    k2 = chamfer(k1.second, s[2], 2)
    k3 = chamfer(k2.second, s[3], 2)
    k4 = chamfer(k3.second, k1.first, 2)
    rep = find_contours([k4.second, k1.piece, k2.first, k2.piece, k3.first, k3.piece,
                         k4.first, k4.piece])
    assert rep.all_closed and len(rep.closed[0].steps) == 8


def test_a_contour_off_by_a_thousandth_is_open_and_says_so():
    pts = [(0, 0), (10, 0), (10, 10), (0, 10), (0, Fr(1, 1000))]
    rep = find_contours(polyline(*pts))
    assert not rep.closed and len(rep.open) == 1 and not rep.all_closed
    assert len(rep.gaps) == 1 and rep.gaps[0].distance == Fr(1, 1000)
    assert "gap of 0.001000 mm" in rep.describe()
    assert "open: from" in rep.describe()


def test_a_miss_smaller_than_any_float_is_still_open():
    # (sqrt 2, 0) against its 30-digit decimal: equal as floats, not as numbers
    near = Fr("1.414213562373095048801688724210")
    assert float(near) == float(sqrt(2))
    # a triangle (sqrt 2, 0) -> (0, 1) -> (0, 0) -> back to (sqrt 2, 0), whose
    # last side stops at the decimal instead
    pieces = [Segment((sqrt(2), 0), (0, 1)), Segment((0, 1), (0, 0)), Segment((0, 0), (near, 0))]
    rep = find_contours(pieces)
    assert not rep.closed and rep.branches == [] and len(rep.open) == 1
    gap = rep.gaps[0].distance
    assert gap.sign() > 0 and gap < Fr(1, 10 ** 29)
    # and two irrational ends a hair apart: sqrt 2 against sqrt 2 + sqrt 3 / 10^15
    hair = sqrt(2) + sqrt(3) / 10 ** 15
    pieces = [Segment((sqrt(2), 0), (0, 1)), Segment((0, 1), (0, 0)), Segment((0, 0), (hair, 0))]
    rep = find_contours(pieces)
    assert not rep.closed and len(rep.open) == 1
    assert rep.gaps[0].distance == sqrt(3) / 10 ** 15


def test_branches_and_duplicates_are_named_not_resolved():
    t = [Segment((0, 0), (5, 0)), Segment((5, 0), (10, 0)), Segment((5, 0), (5, 5))]
    rep = find_contours(t)
    assert rep.branches == [Point(5, 0)]
    assert not rep.closed and not rep.open
    assert "branch: three or more ends meet at (5.000000, 0.000000)" in rep.describe()
    sq = polyline((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))
    rep = find_contours(sq + [Segment((1, 0), (0, 0))])     # one side given twice, reversed
    assert len(rep.duplicates) == 1 and len(rep.closed) == 1 and not rep.all_closed
    assert "given twice" in rep.describe()


def test_mixed_pieces_and_several_contours():
    # a D shape: the upper half of r = 5 closed by its diameter
    d = [Arc((0, 0), 5, (1, 0), (-1, 0)), Segment((-5, 0), (5, 0))]
    # a full circle and a full ellipse are closed on their own
    others = [Circle((20, 0), 2), Ellipse((40, 0), (5, 0), Fr(1, 2))]
    # an elliptical half closed by its major axis
    half = [Ellipse((60, 0), (5, 0), Fr(3, 5), (1, 0), (-1, 0)), Segment((55, 0), (65, 0))]
    loose = polyline((0, 20), (5, 25), (10, 20))
    rep = find_contours(d + others + half + loose)
    assert len(rep.closed) == 4 and len(rep.open) == 1
    for c in rep.closed:
        if len(c.steps) > 1:
            assert walk_is_continuous(c)
    assert rep.gaps[0].distance == 10 and len(rep.gaps) == 1


def test_never_closed_quietly():
    for pts in ([(0, 0), (10, 0), (10, 10)],
                [(0, 0), (10, 0), (10, 10), (0, 10), (Fr(-1, 10 ** 6), 0)]):
        rep = find_contours(polyline(*pts))
        assert rep.closed == [] and len(rep.open) == 1
