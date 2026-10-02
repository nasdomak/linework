"""Distributions and notable points -- verification of backlog task P2-T04
(ADR 0013), including the edge and corner targets of decision D-003.

Counts, pitches and endpoint behaviour on hand-computed cases (the arithmetic
is in the comments), exact points on circles from exact cosines, the notable
points every dimension will attach to, and offsets measured from a named edge
or corner landing on hand-computed coordinates.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import sys
from fractions import Fraction as Fr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geometry.exact import sqrt                                           # noqa: E402
from geometry.primitives import Point, Segment, Circle, Arc, Ellipse      # noqa: E402
from geometry.distribute import (along, on_circle, grid, grid_in,         # noqa: E402
                                 DistributionRefused)
from geometry.notable import notable, point                               # noqa: E402
from geometry import placement as PL                                      # noqa: E402
from lang import anchoring as A                                           # noqa: E402
from lang import form as F                                                # noqa: E402
from lang import script as S                                              # noqa: E402

X100 = Segment((0, 0), (100, 0))
C10 = Circle((0, 0), 10)


def raises(exc, fn, *args, **kw):
    try:
        fn(*args, **kw)
    except exc as e:
        return str(e)
    raise AssertionError("%s was not raised" % exc.__name__)


def xs(d):
    return [p.x for p in d.points]


def pts_are(d, expected):
    assert len(d.points) == len(expected), (d, expected)
    for p, (x, y) in zip(d.points, expected):
        assert p == Point(x, y), (p, (x, y))


# ---------------------------------------------------------------- along a segment

def test_by_count_ends_included_and_excluded():
    d = along(X100, count=5)                         # 4 gaps of 100 / 4
    assert xs(d) == [0, 25, 50, 75, 100] and d.pitch == 25 and d.leftover == 0
    d = along(X100, count=4, ends="exclude")         # 5 equal gaps of 20
    assert xs(d) == [20, 40, 60, 80] and d.pitch == 20
    assert xs(along(X100, count=1, ends="exclude")) == [50]
    assert "both ends" in raises(DistributionRefused, along, X100, count=1)
    # slanted, length 50: (0, 0), (15, 20), (30, 40)
    pts_are(along(Segment((0, 0), (30, 40)), count=3), [(0, 0), (15, 20), (30, 40)])


def test_by_pitch_the_leftover_is_computed_not_absorbed():
    d = along(X100, pitch=30)                        # 0, 30, 60, 90 and 10 left over
    assert xs(d) == [0, 30, 60, 90] and d.leftover == 10 and d.rule == "start"
    d = along(X100, pitch=30, ends="centred")        # the 10 split: 5 at each end
    assert xs(d) == [5, 35, 65, 95]
    d = along(X100, pitch=25)                        # divides exactly: the last is on the end
    assert xs(d) == [0, 25, 50, 75, 100] and d.leftover == 0
    d = along(X100, pitch="12.5")
    assert len(d) == 9 and d.points[-1] == Point(100, 0)


def test_count_and_pitch_together():
    assert xs(along(X100, count=3, pitch=40)) == [0, 40, 80]
    assert xs(along(X100, count=3, pitch=40, ends="centred")) == [10, 50, 90]
    msg = raises(DistributionRefused, along, X100, count=4, pitch=40)
    assert "need 120" in msg and "only 100" in msg


def test_by_pitch_on_an_irrational_length():
    # (0, 0)-(10, 10) is 10 sqrt 2 long; at a pitch of 5, floor(2 sqrt 2) + 1 = 3 points
    d = along(Segment((0, 0), (10, 10)), pitch=5)
    h = 5 * sqrt(2) / 2
    pts_are(d, [(0, 0), (h, h), (2 * h, 2 * h)])
    assert d.leftover == 10 * sqrt(2) - 10


def test_refusals_name_the_problem():
    assert "how many" in raises(DistributionRefused, along, X100)
    assert "greater than zero" in raises(DistributionRefused, along, X100, pitch=0)
    assert "whole number" in raises(DistributionRefused, along, X100, count=2.5)
    assert "segment" in raises(DistributionRefused, along, C10, count=3)
    assert '"exclude"' in raises(DistributionRefused, along, X100, count=3, ends="middle")


# ---------------------------------------------------------------- on a circle

def test_on_a_circle_by_count():
    pts_are(on_circle(C10, count=4), [(10, 0), (0, 10), (-10, 0), (0, -10)])
    h = 5 * sqrt(3)
    pts_are(on_circle(C10, count=6), [(10, 0), (5, h), (-5, h), (-10, 0), (-5, -h), (5, -h)])
    q = 5 * sqrt(2)
    d = on_circle(C10, count=8)
    assert d.points[1] == Point(q, q) and d.points[5] == Point(-q, -q)
    # five: cos 72 = (sqrt 5 - 1) / 4, sin 72 = sqrt(10 + 2 sqrt 5) / 4
    d = on_circle(C10, count=5)
    assert d.points[1] == Point(10 * (sqrt(5) - 1) / 4, 10 * (10 + 2 * sqrt(5)).sqrt() / 4)
    for p in d.points:
        assert p.x * p.x + p.y * p.y == 100
    assert d.pitch == 72


def test_on_a_circle_by_pitch_and_from_a_start():
    pts_are(on_circle(C10, pitch_deg=90), [(10, 0), (0, 10), (-10, 0), (0, -10)])
    assert len(on_circle(C10, pitch_deg=30)) == 12
    q = 5 * sqrt(2)
    d = on_circle(C10, count=3, pitch_deg=45)        # a partial pattern
    pts_are(d, [(10, 0), (q, q), (0, 10)])
    assert d.leftover == 225
    pts_are(on_circle(C10, count=4, start=(0, 1)), [(0, 10), (-10, 0), (0, -10), (10, 0)])
    pts_are(on_circle(Circle((1, 2), 10), count=2, start=(3, 4)), [(7, 10), (-5, -6)])
    assert "whole number of times" in raises(DistributionRefused, on_circle, C10, pitch_deg=7)
    assert "more than once" in raises(DistributionRefused, on_circle, C10, count=5,
                                      pitch_deg=90)


def test_on_a_circle_with_a_fractional_pitch():
    d = on_circle(C10, count=3, pitch_deg="7.5")
    for p in d.points:
        assert p.x * p.x + p.y * p.y == 100
    # cos(15) = (sqrt 6 + sqrt 2) / 4
    assert d.points[2].x == 10 * (sqrt(6) + sqrt(2)) / 4


# ---------------------------------------------------------------- grids

def test_grids():
    pts_are(grid((0, 0), 3, 2, 10, 20), [(0, 0), (10, 0), (20, 0), (0, 20), (10, 20), (20, 20)])
    pts_are(grid((5, 5), 2, 1, -10, 0), [(5, 5), (-5, 5)])
    pts_are(grid_in((0, 0), (100, 60), 3, 2), [(0, 0), (50, 0), (100, 0), (0, 60), (50, 60),
                                                (100, 60)])
    pts_are(grid_in((0, 0), (100, 60), 3, 2, ends="exclude"),
            [(25, 20), (50, 20), (75, 20), (25, 40), (50, 40), (75, 40)])
    assert "zero pitch" in raises(DistributionRefused, grid, (0, 0), 2, 2, 0, 5)
    assert "lower-left" in raises(DistributionRefused, grid_in, (10, 0), (0, 10), 2, 2)


# ---------------------------------------------------------------- notable points

def test_notable_points_of_lines_and_circles():
    assert point(Segment((0, 0), (4, 2)), "mid") == Point(2, 1)
    c = dict(notable(Circle((1, 1), 2)))
    assert c["centre"] == Point(1, 1) and c["quadrant_90"] == Point(1, 3)
    assert c["quadrant_180"] == Point(-1, 1)
    up = dict(notable(Arc((0, 0), 5, (1, 0), (-1, 0))))
    assert up["start"] == Point(5, 0) and up["end"] == Point(-5, 0) and up["mid"] == Point(0, 5)
    assert set(up) == {"centre", "start", "end", "mid", "quadrant_0", "quadrant_90",
                       "quadrant_180"}
    h = 5 * sqrt(2) / 2
    assert point(Arc((0, 0), 5, (1, 0), (0, 1)), "mid") == Point(h, h)
    assert point(Arc((0, 0), 5, (1, 0), (0, -1)), "mid") == Point(-h, h)     # 270 degrees
    assert "has no notable point" in raises(KeyError, point, C10, "mid")


def test_notable_points_of_ellipses_and_placed_rectangles():
    e = dict(notable(Ellipse((0, 0), (5, 0), Fr(3, 5))))
    assert e["major_1"] == Point(5, 0) and e["minor_1"] == Point(0, 3)
    r = dict(notable(Ellipse((0, 0), (3, 4), Fr(2, 5))))
    assert r["minor_1"] == Point(Fr(-8, 5), Fr(6, 5)) and r["major_2"] == Point(-3, -4)
    plate = PL.Extent(Fr(0), Fr(0), Fr(200), Fr(120), "box")
    n = dict(notable(plate))
    assert n["top_left"] == Point(0, 120) and n["top"] == Point(100, 120)
    assert n["centre"] == Point(100, 60) and n["bottom_right"] == Point(200, 0)


# ---------------------------------------------------------------- edges and corners (D-003)

HEAD = S.HEADER + "\ndomain mechanical\n\nadd plate plate1: at origin, width 200 mm, height 120 mm\n"


def placed(lines):
    text = A.place(S.parse(HEAD + lines))
    return dict((l.split()[0], l.split()[2:]) for l in text.splitlines() if not l.startswith("#"))


def test_offset_from_a_named_edge_lands_exactly():
    # 15 mm in from the top (its top edge at 120 - 15 = 105) and 20 mm in from the left
    got = placed("add hole h1: on plate1, offset from plate1 top by 15 mm on side below, "
                 "offset from plate1 left by 20 mm on side right, diameter 10 mm\n")
    assert got["h1"] == ["20", "95", "30", "105"]
    got = placed("add hole h2: on plate1, offset from plate1 bottom by 12.5 mm on side above, "
                 "offset from plate1 right by 8 mm on side left, diameter 6 mm\n")
    assert got["h2"] == ["186", "12.5", "192", "18.5"]


def test_corners_and_centred_on_an_edge():
    # circles (not holes, which must stay on the plate) centred on a corner or an edge
    got = placed("domain general\nadd circle c3: at plate1 top_right, diameter 10 mm\n")
    assert got["c3"] == ["195", "115", "205", "125"]
    got = placed("domain general\nadd circle c4: centred on plate1 top, diameter 10 mm\n")
    assert got["c4"] == ["95", "115", "105", "125"]
    got = placed("domain general\nadd circle c5: aligned with plate1 bottom_left on axis "
                 "horizontal, offset from plate1 left by 30 mm on side right, diameter 4 mm\n")
    assert got["c5"] == ["30", "-2", "34", "2"]
    # a hole there would hang off its plate, and "on" refuses it
    try:
        placed("add hole h3: on plate1, at plate1 top_right, diameter 10 mm\n")
    except PL.PlacementError as exc:
        assert 'it is not on "plate1"' in str(exc)
    else:
        raise AssertionError("a hole off its plate was placed")


def test_edge_targets_round_trip_and_reach_the_form():
    text = (HEAD + "add hole h1: on plate1, offset from plate1 top by 15 mm on side below, "
            "offset from plate1 left by 20 mm on side right, diameter 10 mm\n")
    s = S.parse(text)
    assert S.check(s) == []
    assert str(s) == text
    f = [st for st in s.items if getattr(st, "name", None) == "h1"][0].form()
    assert ["plate1 top"] in [r["to"] for r in f["relations"]]


def test_edges_are_refused_where_they_mean_nothing():
    probs = S.check(S.parse(HEAD + "add hole h1: on plate1, inside plate1 top, "
                            "centred on plate1, diameter 5 mm\n"))
    assert probs and "measures from the whole object" in str(probs[0])
    probs = S.check(S.parse(S.HEADER + "\ndomain mechanical\n\nadd plate p: at origin top, "
                            "width 10 mm, height 10 mm\n"))
    assert probs and "is a point" in str(probs[0])
    try:
        S.parse(HEAD + "add hole h1: on plate1, offset from plate1 middle by 5 mm on side "
                "below, diameter 5 mm\n")
    except S.ScriptError as exc:
        assert 'unexpected "middle"' in str(exc)
    else:
        raise AssertionError("an unknown edge word was accepted")
    v = F.validate({"form": F.FORM_VERSION, "domain": "mechanical", "act": "add",
                    "object": {"kind": "hole", "name": "h9"},
                    "relations": [{"relation": "on", "to": ["plate1"]},
                                  {"relation": "centred_on", "to": ["plate1 diagonal"]}],
                    "dimensions": {"diameter": {"value": 5, "unit": "mm", "said": "5 mm"}}},
                   user_text="a 5 mm hole", known={"plate1": "plate"})
    assert not v.ok and any("diagonal" in m for m in v.messages())
