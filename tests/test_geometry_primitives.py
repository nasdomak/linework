"""Primitives and exact intersections -- verification of backlog task P2-T01
(ADR 0010).

Every pair of shapes (point, segment, arc, circle, ellipse: fifteen pairs) is
intersected on hand-computed cases, and every degenerate case the plan names
(parallel, tangent, coincident, zero-length) is met on purpose. Expected values
are exact: rationals and square roots compared with ==, never with a tolerance.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import sys
from fractions import Fraction as Fr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geometry.exact import Num, NotExact, sqrt, num, real_roots   # noqa: E402
from geometry.primitives import (Point, Segment, Circle, Arc, Ellipse, Degenerate,  # noqa: E402
                                 NotSupported, intersect, turn_le)

O = (0, 0)
E53 = Ellipse(O, (5, 0), Fr(3, 5))        # x^2/25 + y^2/9 = 1
UP = ((1, 0), (-1, 0))                     # the upper half, counter-clockwise


def pts(r):
    return [(p.x, p.y) for p in r.points]


def same(r, expected):
    """The points of r are exactly `expected` ((x, y) pairs, any exact values)."""
    got = pts(r)
    assert len(got) == len(expected), (r, expected)
    for (x, y), (ex, ey) in zip(got, expected):
        assert x == ex and y == ey, (r, expected)


def raises(exc, fn, *args):
    try:
        fn(*args)
    except exc as e:
        return str(e)
    raise AssertionError("%s was not raised" % exc.__name__)


# ---------------------------------------------------------------- the numbers

def test_exact_numbers_never_round():
    r2 = sqrt(2)
    assert r2 * r2 == 2
    assert sqrt(8) == 2 * r2
    assert sqrt(2) * sqrt(3) == sqrt(6)
    assert (1 + r2).inverse() == r2 - 1
    assert sqrt(r2) * sqrt(r2) == r2
    assert sqrt(Fr(9, 4)) == Fr(3, 2) and sqrt(Fr(9, 4)).is_rational()
    assert Fr(141, 100) < r2 < Fr(142, 100)
    assert (sqrt(2) + sqrt(3)) * (sqrt(3) - sqrt(2)) == 1
    assert sqrt(2).decimal(30) == "1.414213562373095048801688724210"
    assert num("0.1") * 3 == Fr(3, 10)


def test_floats_are_refused():
    assert "float" in raises(NotExact, num, 0.1)
    assert "float" in raises(NotExact, Point, 0.5, 1)


def test_real_roots_are_exact_and_rational_when_they_can_be():
    assert real_roots([Fr(6), -5, 1]) == [2, 3]
    roots = real_roots([Fr(-2), 0, 1])
    assert len(roots) == 2
    a, b = [Num(r, [0, 1]) for r in roots]
    assert a == -sqrt(2) and b == sqrt(2)
    # (x - 1/3)^2 (x^2 - 2): the repeated rational root comes back once, exactly
    roots = real_roots([Fr(-2, 9), Fr(4, 3), Fr(-17, 9), Fr(-2, 3), 1])
    assert Fr(1, 3) in roots and len(roots) == 3


def test_resultant_matches_the_product_formula():
    # Res(P, Q) = lc(P)^deg Q * product of Q over the roots of P, sign included
    from itertools import product
    from geometry.exact import resultant, pmul, peval

    def poly(roots, lead=1):
        p = [Fr(lead)]
        for r in roots:
            p = pmul(p, [Fr(-r), Fr(1)])
        return p

    def as_main(p):
        return [[c] if c else [] for c in p]

    cases = [((1, 2, -3), (5, -1)), ((0, 0, 4), (1,)), ((2,), (7, 7, -1)),
             ((1, -1), (2, 3, 4, 5)), ((0, 1, 2, 3), (0, 9)), ((3,), (3,)),
             ((2, -2), (1, 0, -1))]          # this one needs a row swap in Bareiss
    for (rp, rq), lead in product(cases, (1, -2)):
        P, Q = poly(rp, lead), poly(rq)
        expected = Fr(lead) ** len(rq)
        for r in rp:
            expected *= peval(Q, Fr(r))
        got = resultant(as_main(P), as_main(Q))
        assert (got[0] if got else 0) == expected, (rp, rq, lead, got, expected)


# ---------------------------------------------------------------- degenerate shapes

def test_degenerate_shapes_are_refused_when_made():
    assert "zero length" in raises(Degenerate, Segment, (1, 2), (1, 2))
    assert "radius" in raises(Degenerate, Circle, O, 0)
    assert "radius" in raises(Degenerate, Circle, O, -1)
    assert "same" in raises(Degenerate, Arc, O, 1, (1, 0), (2, 0))
    assert "zero vector" in raises(Degenerate, Arc, O, 1, (0, 0), (1, 0))
    assert "ratio" in raises(Degenerate, Ellipse, O, (5, 0), 0)
    assert "ratio" in raises(Degenerate, Ellipse, O, (5, 0), Fr(6, 5))
    assert "zero vector" in raises(Degenerate, Ellipse, O, (0, 0), Fr(1, 2))
    assert "both" in raises(Degenerate, Ellipse, O, (5, 0), Fr(1, 2), (1, 0), None)


def test_angular_sweep():
    # counter-clockwise turns from +x
    assert turn_le((1, 0), (0, 1), (-1, 0))
    assert not turn_le((1, 0), (0, -1), (-1, 0))
    assert turn_le((1, 0), (1, 0), (0, -1))       # zero turn first
    assert turn_le((1, 0), (-1, 0), (0, -1))      # half a turn before three quarters


# ---------------------------------------------------------------- point with everything

def test_point_point():
    same(intersect(Point(1, 2), Point(1, 2)), [(1, 2)])
    assert intersect(Point(1, 2), Point(2, 1)).kind == "none"


def test_point_segment():
    s = Segment((0, 0), (4, 2))
    same(intersect(Point(2, 1), s), [(2, 1)])                 # inside
    same(intersect(s, Point(4, 2)), [(4, 2)])                 # an endpoint, either order
    r = intersect(Point(6, 3), s)                             # on the line, past the end
    assert r.kind == "none" and r.notes == ("outside",)
    assert intersect(Point(2, 2), s).kind == "none"


def test_point_arc_circle_ellipse():
    c = Circle(O, 5)
    same(intersect(Point(3, 4), c), [(3, 4)])
    assert intersect(Point(3, 3), c).kind == "none"
    a = Arc(O, 5, *UP)
    same(intersect(Point(-3, 4), a), [(-3, 4)])
    assert intersect(Point(3, -4), a).notes == ("outside",)
    same(intersect(Point(-5, 0), a), [(-5, 0)])               # the arc's end, inclusive
    same(intersect(Point(5, 0), E53), [(5, 0)])
    same(intersect(Point(4, Fr(9, 5)), E53), [(4, Fr(9, 5))])  # 16/25 + 9/25 = 1
    assert intersect(Point(4, 2), E53).kind == "none"


# ---------------------------------------------------------------- segment pairs

def test_segment_segment_crossing_and_outside():
    same(intersect(Segment((0, 0), (4, 4)), Segment((0, 4), (4, 0))), [(2, 2)])
    same(intersect(Segment((0, 0), (3, 1)), Segment((1, 0), (0, 3))),
         [(Fr(9, 10), Fr(3, 10))])                            # t = 3/10
    r = intersect(Segment((0, 0), (1, 1)), Segment((3, 0), (0, 3)))
    assert r.kind == "none" and r.notes == ("outside",)       # lines meet at (3/2, 3/2)
    same(intersect(Segment((0, 0), (4, 0)), Segment((2, 0), (2, 5))), [(2, 0)])  # T


def test_segment_segment_parallel_and_collinear():
    r = intersect(Segment((0, 0), (4, 0)), Segment((0, 1), (4, 1)))
    assert r.kind == "none" and r.notes == ("parallel",)
    r = intersect(Segment((0, 0), (4, 0)), Segment((2, 0), (6, 0)))
    assert r.kind == "overlap" and r.notes == ("collinear",)
    assert r.overlap == [Segment((2, 0), (4, 0))]
    r = intersect(Segment((0, 0), (4, 0)), Segment((6, 0), (4, 0)))    # end to end
    same(r, [(4, 0)])
    assert r.notes == ("collinear",) and not r.overlap
    r = intersect(Segment((0, 0), (4, 0)), Segment((5, 0), (7, 0)))
    assert r.kind == "none" and r.notes == ("collinear",)
    r = intersect(Segment((1, 1), (3, 3)), Segment((4, 4), (0, 0)))    # contained, reversed
    assert r.overlap == [Segment((1, 1), (3, 3))]


def test_segment_circle():
    c = Circle(O, 2)
    same(intersect(Segment((-10, 1), (10, 1)), c), [(-sqrt(3), 1), (sqrt(3), 1)])
    same(intersect(Segment((-10, 0), (10, 0)), Circle(O, 5)), [(-5, 0), (5, 0)])
    r = intersect(Segment((-10, 5), (10, 5)), Circle(O, 5))
    same(r, [(0, 5)])
    assert r.tangent == [True] and r.notes == ("tangent",)
    assert intersect(Segment((-10, 6), (10, 6)), Circle(O, 5)).kind == "none"
    same(intersect(Segment((0, 0), (10, 0)), Circle(O, 5)), [(5, 0)])   # starts inside
    r = intersect(Segment((0, 0), (1, 0)), Circle(O, 5))
    assert r.kind == "none" and r.notes == ("outside",)
    # a slanted chord: y = x meets r = 2 at (sqrt 2, sqrt 2)
    same(intersect(Segment((0, 0), (3, 3)), c), [(sqrt(2), sqrt(2))])


def test_segment_arc():
    a = Arc(O, 2, *UP)
    same(intersect(Segment((-10, 1), (10, 1)), a), [(-sqrt(3), 1), (sqrt(3), 1)])
    assert intersect(Segment((-10, -1), (10, -1)), a).notes == ("outside",)
    same(intersect(Segment((-2, -5), (-2, 5)), a), [(-2, 0)])   # through the arc's end
    q1 = Arc(O, 2, (1, 0), (0, 1))                               # first quadrant only
    same(intersect(Segment((-10, 1), (10, 1)), q1), [(sqrt(3), 1)])


def test_segment_ellipse():
    same(intersect(Segment((4, -10), (4, 10)), E53), [(4, Fr(-9, 5)), (4, Fr(9, 5))])
    r = intersect(Segment((5, -10), (5, 10)), E53)
    same(r, [(5, 0)])
    assert r.tangent == [True]
    # rotated: major axis along (3, 4), a = 5, b = 2; the major axis itself
    rot = Ellipse(O, (3, 4), Fr(2, 5))
    same(intersect(Segment((-6, -8), (6, 8)), rot), [(-3, -4), (3, 4)])
    # and the minor axis, direction (-4, 3): its ends are (-8/5, 6/5) and (8/5, -6/5)
    same(intersect(Segment((-8, 6), (8, -6)), rot), [(Fr(-8, 5), Fr(6, 5)), (Fr(8, 5), Fr(-6, 5))])
    # an elliptical arc: the upper half of E53
    half = Ellipse(O, (5, 0), Fr(3, 5), *UP)
    same(intersect(Segment((4, -10), (4, 10)), half), [(4, Fr(9, 5))])


# ---------------------------------------------------------------- conic pairs

def test_circle_circle():
    same(intersect(Circle(O, 5), Circle((8, 0), 5)), [(4, -3), (4, 3)])
    r = intersect(Circle(O, 2), Circle((4, 0), 2))              # outside each other
    same(r, [(2, 0)])
    assert r.tangent == [True] and r.notes == ("tangent",)
    r = intersect(Circle(O, 5), Circle((2, 0), 3))              # inside, touching
    same(r, [(5, 0)])
    assert r.tangent == [True]
    r = intersect(Circle(O, 5), Circle(O, 3))
    assert r.kind == "none" and r.notes == ("concentric",)
    assert intersect(Circle(O, 1), Circle((10, 0), 1)).kind == "none"
    assert intersect(Circle(O, 5), Circle((1, 0), 1)).kind == "none"
    r = intersect(Circle(O, 5), Circle((0, 0), 5))
    assert r.notes == ("coincident",) and r.overlap == [Circle(O, 5)]
    # irrational: r = 2 at the origin and at (2, 2) meet at (2, 0) and (0, 2)
    same(intersect(Circle(O, 2), Circle((2, 2), 2)), [(0, 2), (2, 0)])
    # unit circles one apart: (1/2, +- sqrt(3)/2)
    same(intersect(Circle(O, 1), Circle((1, 0), 1)),
         [(Fr(1, 2), -sqrt(3) / 2), (Fr(1, 2), sqrt(3) / 2)])


def test_arc_circle_and_arc_arc():
    up = Arc(O, 5, *UP)
    same(intersect(up, Circle((8, 0), 5)), [(4, 3)])
    lower = Arc((8, 0), 5, (-1, 0), (1, 0))       # lower half of the other circle
    r = intersect(up, lower)
    assert r.kind == "none" and r.notes == ("outside",)
    # same circle: the overlap of two arcs is an arc
    r = intersect(Arc(O, 2, (1, 0), (-1, 0)), Arc(O, 2, (0, 1), (0, -1)))
    assert r.notes == ("coincident",)
    assert r.overlap == [Arc(O, 2, (0, 1), (-1, 0))]
    # ... or two arcs, when each covers the other's start
    r = intersect(Arc(O, 2, (1, 0), (0, -1)), Arc(O, 2, (-1, 0), (0, 1)))
    assert len(r.overlap) == 2
    assert Arc(O, 2, (-1, 0), (0, -1)) in r.overlap and Arc(O, 2, (1, 0), (0, 1)) in r.overlap
    # ... or one point, where one ends and the other starts
    r = intersect(Arc(O, 2, (1, 0), (0, 1)), Arc(O, 2, (0, 1), (-1, 0)))
    same(r, [(0, 2)])
    assert not r.overlap
    # circle with arc on the same circle: the arc
    r = intersect(Circle(O, 2), Arc(O, 2, (0, 1), (-1, 0)))
    assert r.overlap == [Arc(O, 2, (0, 1), (-1, 0))]


def test_circle_ellipse_and_arc_ellipse():
    # x^2 + y^2 = 16 with x^2/25 + y^2/9 = 1: x = +-5 sqrt(7)/4, y = +-9/4
    x = 5 * sqrt(7) / 4
    same(intersect(Circle(O, 4), E53),
         [(-x, Fr(-9, 4)), (-x, Fr(9, 4)), (x, Fr(-9, 4)), (x, Fr(9, 4))])
    r = intersect(Circle(O, 3), E53)                     # touches at the minor vertices
    same(r, [(0, -3), (0, 3)])
    assert r.tangent == [True, True]
    r = intersect(E53, Circle(O, 5))                     # ... and at the major ones
    same(r, [(-5, 0), (5, 0)])
    assert r.tangent == [True, True]
    assert intersect(Circle(O, 2), E53).kind == "none"   # inside, never meeting
    q1 = Arc(O, 4, (1, 0), (0, 1))
    same(intersect(q1, E53), [(x, Fr(9, 4))])
    # two points on one vertical: (x - 8)^2 + y^2 = 25 meets E53 where
    # x^2 - 25 x + 75 = 0, so x = (25 - 5 sqrt(13)) / 2 (the other root is off the ellipse)
    r = intersect(Circle((8, 0), 5), E53)
    x = (25 - 5 * sqrt(13)) / 2
    y = (9 - 9 * x * x / 25).sqrt()
    same(r, [(x, -y), (x, y)])
    r = intersect(Circle(O, 5), Ellipse(O, (5, 0), 1))   # an ellipse that is the circle
    assert r.notes == ("coincident",)


def test_ellipse_ellipse():
    # the same ellipse turned a quarter: x^2 = y^2 = 225/34
    t = 15 * sqrt(34) / 34
    same(intersect(E53, Ellipse(O, (0, 5), Fr(3, 5))),
         [(-t, -t), (-t, t), (t, -t), (t, t)])
    r = intersect(E53, Ellipse((10, 0), (5, 0), Fr(3, 5)))    # side by side, touching
    same(r, [(5, 0)])
    assert r.tangent == [True]
    assert intersect(E53, Ellipse((20, 0), (5, 0), Fr(3, 5))).kind == "none"
    r = intersect(E53, Ellipse(O, (-5, 0), Fr(3, 5)))          # same curve, axis reversed
    assert r.notes == ("coincident",) and len(r.overlap) == 1
    r = intersect(Ellipse(O, (5, 0), Fr(3, 5), *UP), Ellipse(O, (5, 0), Fr(3, 5), (0, 1), (0, -1)))
    assert r.notes == ("coincident",) and len(r.overlap) == 1
    piece = r.overlap[0]                                       # from straight up to the left
    assert piece.start[0] == 0 and piece.start[1] == 1
    assert piece.end[0] == -1 and piece.end[1] == 0
    assert piece.endpoints()[0] == Point(0, 3) and piece.endpoints()[1] == Point(-5, 0)


def test_quartic_points_lie_exactly_on_both_curves():
    # no hand values here: a rotated, off-centre ellipse against a circle. The
    # check is exact: each point satisfies both equations with zero remainder.
    a, b = Circle(O, 3), Ellipse((1, 0), (3, 4), Fr(1, 2))
    r = intersect(a, b)
    assert len(r.points) == 2
    for p in r.points:
        assert a.value(p).is_zero() and b.value(p).is_zero()
    assert r.points[0].text(6) == "(-2.510946, -1.641691)"
    assert r.points[1].text(6) == "(0.369703, 2.977133)"


def test_symmetry_every_pair_both_ways():
    shapes = [Point(4, 3), Segment((-10, 3), (10, 3)), Arc(O, 5, *UP), Circle((8, 0), 5),
              Ellipse(O, (5, 0), Fr(3, 5))]
    for i, a in enumerate(shapes):
        for b in shapes[i:]:
            r1, r2 = intersect(a, b), intersect(b, a)
            assert pts(r1) == pts(r2) or all(
                x1 == x2 and y1 == y2 for (x1, y1), (x2, y2) in zip(pts(r1), pts(r2)))
            assert r1.notes == r2.notes


def test_irrational_conics_are_named_not_guessed():
    a = Ellipse((sqrt(2), 0), (5, 0), Fr(1, 2))
    b = Ellipse(O, (0, 3), Fr(1, 2))
    assert "quartic" in raises(NotSupported, intersect, a, b)
