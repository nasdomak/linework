"""Offsets, trim, extend, fillet, chamfer, tangents -- verification of backlog
task P2-T02 (ADR 0011).

Every expected value is computed by hand (shown in the comments) and compared
exactly. Fillets and chamfers are checked on acute, obtuse and irrational
corners, not only on right angles. Every refusal names its reason.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import sys
from fractions import Fraction as Fr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geometry.exact import sqrt                                       # noqa: E402
from geometry.primitives import Point, Segment, Circle, Arc, Ellipse, NotSupported  # noqa: E402
from geometry.ops import (offset, split, trim, extend, fillet, chamfer,  # noqa: E402
                          tangents_from_point, tangents_between, OperationRefused)

O = (0, 0)
R2 = sqrt(2)


def raises(exc, fn, *args):
    try:
        fn(*args)
    except exc as e:
        return str(e)
    raise AssertionError("%s was not raised" % exc.__name__)


def is_seg(s, a, b):
    return isinstance(s, Segment) and s.p == Point(*a) and s.q == Point(*b)


def is_arc(arc, c, r, start, end):
    return (isinstance(arc, Arc) and arc.c == Point(*c) and arc.r == r
            and arc.endpoints()[0] == Point(*start) and arc.endpoints()[1] == Point(*end))


# ---------------------------------------------------------------- offsets

def test_offset_segments_both_sides_exactly():
    assert is_seg(offset(Segment((0, 0), (4, 0)), 1, "left"), (0, 1), (4, 1))
    assert is_seg(offset(Segment((0, 0), (4, 0)), 1, "right"), (0, -1), (4, -1))
    # along (3, 4), length 5: the left normal is (-4, 3) / 5, times 5
    assert is_seg(offset(Segment((0, 0), (3, 4)), 5, "left"), (-4, 3), (-1, 7))
    # along (1, 1): the left normal is (-1, 1) / sqrt 2
    h = R2 / 2
    assert is_seg(offset(Segment((0, 0), (1, 1)), 1, "left"), (-h, h), (1 - h, 1 + h))
    assert is_seg(offset(Segment((0, 0), (4, 0)), "0.25", "left"), (0, Fr(1, 4)), (4, Fr(1, 4)))


def test_offset_circles_and_arcs():
    assert offset(Circle(O, 5), 2, "outside") == Circle(O, 7)
    assert offset(Circle(O, 5), 2, "inside") == Circle(O, 3)
    a = offset(Arc(O, 5, (1, 0), (0, 1)), 1, "outside")
    assert is_arc(a, O, 6, (6, 0), (0, 6))
    assert "nothing would be left" in raises(OperationRefused, offset, Circle(O, 5), 5, "inside")
    assert "greater than zero" in raises(OperationRefused, offset, Circle(O, 5), 0, "inside")
    assert "left" in raises(OperationRefused, offset, Segment(O, (1, 0)), 1, "outside")
    assert "not an ellipse" in raises(NotSupported, offset, Ellipse(O, (5, 0), Fr(1, 2)), 1,
                                      "outside")


# ---------------------------------------------------------------- split and trim

def test_split_segment_and_arc_in_order():
    s = split(Segment((0, 0), (10, 0)), [Point(6, 0), Point(4, 0), Point(4, 0)])
    assert len(s) == 3
    assert is_seg(s[0], (0, 0), (4, 0)) and is_seg(s[1], (4, 0), (6, 0)) and is_seg(s[2], (6, 0), (10, 0))
    a = split(Arc(O, 5, (1, 0), (-1, 0)), [Point(-3, 4), Point(3, 4)])
    assert [p.endpoints()[0] for p in a] == [Point(5, 0), Point(3, 4), Point(-3, 4)]
    assert "not on" in raises(OperationRefused, split, Segment((0, 0), (1, 0)), [Point(0, 1)])
    assert "two cut points" in raises(OperationRefused, split, Circle(O, 5), [Point(5, 0)])


def test_trim_segment_between_cutters():
    s = Segment((0, 0), (10, 0))
    cut = [Segment((4, -1), (4, 1)), Segment((6, -1), (6, 1))]
    left, right = trim(s, cut, Point(5, 0))
    assert is_seg(left, (0, 0), (4, 0)) and is_seg(right, (6, 0), (10, 0))
    (rest,) = trim(s, cut[:1], Point(2, 0))
    assert is_seg(rest, (4, 0), (10, 0))
    (rest,) = trim(s, cut[:1], Point(7, 3))                 # a pick off the line projects
    assert is_seg(rest, (0, 0), (4, 0))
    assert "cut point" in raises(OperationRefused, trim, s, cut, Point(4, 0))
    assert "nothing cuts" in raises(OperationRefused, trim, s, [Segment((0, 5), (1, 5))],
                                    Point(1, 0))
    assert "lies along" in raises(OperationRefused, trim, s, [Segment((2, 0), (3, 0))],
                                  Point(1, 0))


def test_trim_circle_and_arc():
    # y = 3 cuts r = 5 at (-4, 3) and (4, 3); remove the top, keep the big arc below
    (rest,) = trim(Circle(O, 5), [Segment((-10, 3), (10, 3))], Point(0, 9))
    assert is_arc(rest, O, 5, (-4, 3), (4, 3))
    # y = 1 cuts r = 2 at (+-sqrt 3, 1); trim the upper-half arc in the middle
    a = Arc(O, 2, (1, 0), (-1, 0))
    left, right = trim(a, [Segment((-5, 1), (5, 1))], Point(0, 2))
    assert is_arc(left, O, 2, (2, 0), (sqrt(3), 1))
    assert is_arc(right, O, 2, (-sqrt(3), 1), (-2, 0))
    assert "centre" in raises(OperationRefused, trim, a, [Segment((-5, 1), (5, 1))], Point(0, 0))


# ---------------------------------------------------------------- extend

def test_extend_segment_to_the_nearest_boundary():
    s = Segment((0, 0), (2, 0))
    assert is_seg(extend(s, Segment((5, -1), (5, 1)), "q"), (0, 0), (5, 0))
    assert is_seg(extend(s, Circle((10, 0), 2), "q"), (0, 0), (8, 0))       # first hit
    assert is_seg(extend(Segment((2, 0), (4, 0)), Segment((0, -1), (0, 1)), "p"), (0, 0), (4, 0))
    # a slanted boundary: x + y = 6 meets y = 0 at (6, 0)
    assert is_seg(extend(s, Segment((6, 0), (0, 6)), "q"), (0, 0), (6, 0))
    # an irrational stop: the circle r = 2 at (5, 1) is met by y = 0 at 5 - sqrt 3
    assert is_seg(extend(s, Circle((5, 1), 2), "q"), (0, 0), (5 - sqrt(3), 0))
    assert "never meets" in raises(OperationRefused, extend, s, Segment((5, 1), (5, 3)), "q")
    assert "never meets" in raises(OperationRefused, extend, s, Segment((5, -1), (5, 1)), "p")


def test_extend_arc_both_ways():
    a = Arc(O, 5, (1, 0), (0, 1))                          # first quadrant
    assert is_arc(extend(a, Segment((-10, 3), (10, 3)), "end"), O, 5, (5, 0), (-4, 3))
    assert is_arc(extend(a, Segment((-10, -3), (10, -3)), "start"), O, 5, (4, -3), (0, 5))
    assert "never meets" in raises(OperationRefused, extend, a, Segment((10, 0), (11, 0)), "end")


# ---------------------------------------------------------------- fillets

def test_fillet_right_angle():
    r = fillet(Segment((0, 0), (10, 0)), Segment((0, 0), (0, 10)), 2)
    assert is_seg(r.first, (2, 0), (10, 0)) and is_seg(r.second, (0, 2), (0, 10))
    assert is_arc(r.piece, (2, 2), 2, (0, 2), (2, 0))


def test_fillet_acute_and_obtuse_rational():
    # acute: (1, 0) and (3, 4) / 5, tan(theta / 2) = (4/5) / (1 + 3/5) = 1/2:
    # the tangent points are r / (1/2) = 2 from the corner
    r = fillet(Segment((0, 0), (10, 0)), Segment((0, 0), (3, 4)), 1)
    assert is_seg(r.first, (2, 0), (10, 0))
    assert is_seg(r.second, (Fr(6, 5), Fr(8, 5)), (3, 4))
    assert is_arc(r.piece, (2, 1), 1, (Fr(6, 5), Fr(8, 5)), (2, 0))
    # obtuse: (1, 0) and (-3, 4) / 5, tan(theta / 2) = (4/5) / (2/5) = 2: r = 2 gives 1
    r = fillet(Segment((0, 0), (10, 0)), Segment((0, 0), (-3, 4)), 2)
    assert is_seg(r.first, (1, 0), (10, 0))
    assert is_seg(r.second, (Fr(-3, 5), Fr(4, 5)), (-3, 4))
    assert r.piece.c == Point(1, 2) and r.piece.r == 2


def test_fillet_irrational_and_open_corner():
    # 45 degrees: tan(22.5) = sqrt 2 - 1, so the tangent points are 1 + sqrt 2 out
    r = fillet(Segment((0, 0), (10, 0)), Segment((0, 0), (10, 10)), 1)
    t = 1 + R2
    assert is_seg(r.first, (t, 0), (10, 0))
    assert is_seg(r.second, (t * R2 / 2, t * R2 / 2), (10, 10))
    assert r.piece.c == Point(t, 1)
    for end in r.piece.endpoints():            # both tangent points are exactly r from the centre
        dx, dy = end.x - r.piece.c.x, end.y - r.piece.c.y
        assert dx * dx + dy * dy == 1
    assert {r.piece.endpoints()[0].y == 0, r.piece.endpoints()[1].y == 0} == {True, False}
    # segments that do not reach the corner are extended to the tangent points
    r = fillet(Segment((3, 0), (10, 0)), Segment((0, 1), (0, 10)), 2)
    assert is_seg(r.first, (2, 0), (10, 0)) and is_seg(r.second, (0, 2), (0, 10))
    # reversed segment directions change nothing
    r = fillet(Segment((10, 0), (0, 0)), Segment((0, 10), (0, 0)), 2)
    assert is_arc(r.piece, (2, 2), 2, (0, 2), (2, 0))


def test_fillet_refusals():
    a, b = Segment((0, 0), (10, 0)), Segment((0, 0), (0, 10))
    assert "parallel" in raises(OperationRefused, fillet, a, Segment((0, 1), (10, 1)), 1)
    assert "too short" in raises(OperationRefused, fillet, a, b, 10)
    assert "runs through the corner" in raises(OperationRefused, fillet,
                                               Segment((-5, 0), (5, 0)), b, 1)
    assert "greater than zero" in raises(OperationRefused, fillet, a, b, 0)


# ---------------------------------------------------------------- chamfers

def test_chamfer_any_angle():
    r = chamfer(Segment((0, 0), (10, 0)), Segment((0, 0), (0, 10)), 2)
    assert is_seg(r.piece, (2, 0), (0, 2))
    r = chamfer(Segment((0, 0), (10, 0)), Segment((0, 0), (0, 10)), 2, 3)
    assert is_seg(r.piece, (2, 0), (0, 3)) and is_seg(r.second, (0, 3), (0, 10))
    r = chamfer(Segment((0, 0), (10, 0)), Segment((0, 0), (3, 4)), 1)
    assert is_seg(r.piece, (1, 0), (Fr(3, 5), Fr(4, 5)))
    r = chamfer(Segment((0, 0), (10, 0)), Segment((0, 0), (10, 10)), 1)
    assert is_seg(r.piece, (1, 0), (R2 / 2, R2 / 2))
    assert "too short" in raises(OperationRefused, chamfer, Segment((0, 0), (10, 0)),
                                 Segment((0, 0), (3, 4)), 5)


# ---------------------------------------------------------------- tangents

def test_tangents_from_a_point():
    # r = 3, from (5, 0): d = 5, the points are (9/5, +-12/5)
    ts = tangents_from_point(Point(5, 0), Circle(O, 3))
    assert len(ts) == 2 and Point(Fr(9, 5), Fr(12, 5)) in ts and Point(Fr(9, 5), Fr(-12, 5)) in ts
    assert tangents_from_point(Point(3, 0), Circle(O, 3)) == [Point(3, 0)]
    assert tangents_from_point(Point(1, 0), Circle(O, 3)) == []
    # irrational: r = 1 from (2, 0): (1/2, +-sqrt(3)/2)
    ts = tangents_from_point(Point(2, 0), Circle(O, 1))
    assert Point(Fr(1, 2), sqrt(3) / 2) in ts and Point(Fr(1, 2), -sqrt(3) / 2) in ts


def test_tangents_between_circles():
    ts = tangents_between(Circle(O, 1), Circle((4, 0), 1))
    ext = [(t.t1, t.t2) for t in ts if t.kind == "external"]
    inn = [(t.t1, t.t2) for t in ts if t.kind == "internal"]
    assert (Point(0, 1), Point(4, 1)) in ext and (Point(0, -1), Point(4, -1)) in ext
    h = sqrt(3) / 2
    assert (Point(Fr(1, 2), h), Point(Fr(7, 2), -h)) in inn
    assert (Point(Fr(1, 2), -h), Point(Fr(7, 2), h)) in inn
    # r1 = 4, r2 = 1, d = 5: externals touch at (12/5, +-16/5) and (28/5, +-4/5); the
    # circles touch at (4, 0), so there is exactly one internal tangent
    ts = tangents_between(Circle(O, 4), Circle((5, 0), 1))
    assert len(ts) == 3
    assert [(t.t1, t.t2) for t in ts if t.kind == "internal"] == [(Point(4, 0), Point(4, 0))]
    ext = [(t.t1, t.t2) for t in ts if t.kind == "external"]
    assert (Point(Fr(12, 5), Fr(16, 5)), Point(Fr(28, 5), Fr(4, 5))) in ext
    # one inside the other: none; inside and touching: one external
    assert tangents_between(Circle(O, 5), Circle((1, 0), 1)) == []
    ts = tangents_between(Circle(O, 5), Circle((3, 0), 2))
    assert len(ts) == 1 and ts[0].t1 == Point(5, 0) == ts[0].t2
    assert tangents_between(Circle(O, 5), Circle(O, 3)) == []
    assert "same circle" in raises(OperationRefused, tangents_between, Circle(O, 5), Circle(O, 5))


def test_every_tangent_really_touches():
    # independent check, exact: each touching point is on its circle and the
    # line t1-t2 is perpendicular to the radius there
    c1, c2 = Circle((1, 2), 3), Circle((9, 5), 2)
    ts = tangents_between(c1, c2)
    assert len(ts) == 4
    for t in ts:
        assert c1.on(t.t1) and c2.on(t.t2)
        dx, dy = t.t2.x - t.t1.x, t.t2.y - t.t1.y
        assert (dx * (t.t1.x - c1.c.x) + dy * (t.t1.y - c1.c.y)).is_zero()
        assert (dx * (t.t2.x - c2.c.x) + dy * (t.t2.y - c2.c.y)).is_zero()
