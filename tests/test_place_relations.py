"""Place by relations -- verification of backlog task P2-T05 (ADR 0014, decision
D-002; spacing D-004 and "between" rectangles D-005 taken as their defaults).

At least one hand-computed case per relation the anchoring rules left to the
solver -- along, between, distributed over, the corner features -- plus the
refusals, the "on" check, and the civil example of SCRIPT.md placed in full.
The arithmetic is in the comments; every value is compared exactly.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geometry import placement as PL                     # noqa: E402
from geometry.primitives import Point, Segment            # noqa: E402
from geometry.ops import fillet                           # noqa: E402
from lang import anchoring as A                           # noqa: E402
from lang import script as S                              # noqa: E402

H = S.HEADER + "\n"


def run(body):
    """The placement text, as {name: [fields]} for the boxes and {name: [...]}
    for the AXES section (keyed "axis:<name>")."""
    text = A.place(S.parse(H + body))
    out, axes = {}, False
    for line in text.splitlines():
        if line.startswith("# AXES"):
            axes = True
        if line.startswith("#"):
            continue
        f = line.split()
        out[("axis:" if axes else "") + f[0]] = f[2:]
    return out


def refused(body, exc=PL.PlacementError):
    try:
        A.place(S.parse(H + body))
    except exc as e:
        return str(e)
    raise AssertionError("placed, but should have been refused")


CIVIL = ("domain civil\n"
         "add plot plot1: at origin, width 30 m, length 45 m\n"
         "add road road1: along plot1 on side below, width 6 m\n"
         "add manhole mh1: inside plot1, offset from road1 by 2 m on side above, diameter 1 m\n"
         "add manhole mh2: next to mh1 on side right, diameter 1 m\n"
         "add pipe sewer1: between mh1 and mh2, diameter 300 mm, pipe_use sewer\n")

ROOMS = ("domain architecture\n"
         "add room living: at origin, width 5 m, length 4 m\n"
         "add room kitchen: next to living on side right, width 3 m, length 4 m\n")


# ---------------------------------------------------------------- along

def test_along_a_side_runs_the_whole_length_outside_the_target():
    got = run(CIVIL)
    # plot 0..30000 x 0..45000; the road below it, 6000 deep, the whole 30000 long
    assert got["road1"] == ["0", "-6000", "30000", "0"]
    assert got["axis:road1"] == ["0", "-3000", "30000", "-3000", "6000"]
    got = run(ROOMS + "add wall wall_north: along living on side above, thickness 30 cm\n")
    assert got["wall_north"] == ["0", "4000", "5000", "4300"]
    assert got["axis:wall_north"] == ["0", "4150", "5000", "4150", "300"]


def test_along_with_its_own_length_and_on_the_long_axis():
    got = run(CIVIL + "add road r2: along plot1 on side right, width 4 m, length 20 m\n")
    assert got["r2"] == ["30000", "0", "34000", "20000"]          # starts where plot1 starts
    got = run(CIVIL + "domain general\nadd line l1: along plot1\n")
    # no side: on the long axis of the plot, which is vertical (30 m wide, 45 m long)
    assert got["l1"] == ["15000", "0", "15000", "45000"]
    assert got["axis:l1"] == ["15000", "0", "15000", "45000", "0"]


def test_along_a_square_has_no_long_axis():
    body = ("domain civil\nadd plot sq: at origin, width 10 m, length 10 m\n"
            "domain general\nadd line l1: along sq\n")
    probs = A.problems(S.parse(H + body))
    assert probs and "needs the direction" in str(probs[0])


# ---------------------------------------------------------------- between

def test_between_round_things_runs_centre_to_centre():
    got = run(CIVIL)
    # mh1: 2 m above the road's top (y 0), flush left: 0..1000 x 2000..3000; mh2 to its right
    assert got["mh1"] == ["0", "2000", "1000", "3000"]
    assert got["mh2"] == ["1000", "2000", "2000", "3000"]
    # centres (500, 2500) and (1500, 2500); 300 wide across the horizontal axis
    assert got["sewer1"] == ["500", "2350", "1500", "2650"]
    assert got["axis:sewer1"] == ["500", "2500", "1500", "2500", "300"]


def test_between_on_a_slant_gives_the_exact_axis():
    body = ("domain general\nadd circle a: at origin, diameter 10 mm\n"
            "add circle b: offset from a by 30 mm on side right, diameter 10 mm\n"
            "add circle c: offset from a by 20 mm on side above, diameter 10 mm\n"
            "domain schematic\nadd wire n1: between b and c\n")
    got = run(body)
    # a: -5..5; b: 35..45 flush at the bottom, centre (40, 0); c: 25..35 up, centre (0, 30)
    assert got["axis:n1"] == ["40", "0", "0", "30", "0"]
    assert got["n1"] == ["0", "0", "40", "30"]


def test_between_two_rooms_is_their_shared_edge():
    got = run(ROOMS + "add wall wall_east: between living and kitchen, thickness 20 cm\n")
    # living 0..5000, kitchen 5000..8000, both 0..4000: the shared edge is x = 5000
    assert got["axis:wall_east"] == ["5000", "0", "5000", "4000", "200"]
    assert got["wall_east"] == ["4900", "0", "5100", "4000"]
    # the same rooms stacked: the shared edge is horizontal
    stacked = ("domain architecture\nadd room a: at origin, width 4 m, length 3 m\n"
               "add room b: next to a on side above, width 6 m, length 2 m\n"
               "add wall w: between a and b, thickness 10 cm\n")
    got = run(stacked)
    assert got["axis:w"] == ["0", "3000", "4000", "3000", "100"]   # where they overlap
    assert got["w"] == ["0", "2950", "4000", "3050"]


def test_between_refusals():
    apart = ("domain architecture\nadd room a: at origin, width 4 m, length 3 m\n"
             "add room b: offset from a by 1 m on side right, width 4 m, length 3 m\n"
             "add wall w: between a and b, thickness 10 cm\n")
    assert "share no edge" in refused(apart)
    corner = ("domain architecture\nadd room a: at origin, width 4 m, length 3 m\n"
              "add room b: at a top_right, width 2 m, length 2 m\n"     # touch at one point
              "add wall w: between a and b, thickness 10 cm\n")
    assert "share no edge" in refused(corner)
    same = ("domain general\nadd circle a: at origin, diameter 10 mm\n"
            "add circle b: centred on a, diameter 4 mm\n"
            "domain schematic\nadd wire n1: between a and b\n")
    assert "same point" in refused(same)
    round_one = ("domain general\nadd circle a: at origin, diameter 10 mm\n"
                 "add circle b: offset from a by 30 mm on side right, diameter 10 mm\n"
                 "add circle m: between a and b, diameter 2 mm\n")
    assert "a circle is not one" in refused(round_one)


def test_no_relation_is_left_for_later():
    # D-002: every relation that fixes a position is computed, or refused with a reason
    import json
    with open(os.path.join(ROOT, "shared", "catalogue_v1.json")) as fh:
        cat = json.load(fh)
    fixing = sorted(w for w, e in cat["relations"].items() if e["fixes"])
    assert set(fixing) <= set(PL.SUPPORTED) | {"between"}, fixing


# ---------------------------------------------------------------- distributed over

PLATE = "domain mechanical\nadd plate plate1: at origin, width 200 mm, height 120 mm\n"


def test_distributed_over_by_count():
    got = run(PLATE + "add hole hs: on plate1, distributed over plate1 in 3 copies, "
              "diameter 10 mm\n")
    # 3 copies, 4 equal spaces of 50: centres 50, 100, 150; across, centred at 60
    assert [got["hs.%d" % i] for i in (1, 2, 3)] == [["45", "55", "55", "65"],
                                                     ["95", "55", "105", "65"],
                                                     ["145", "55", "155", "65"]]
    # the bracket: 4 copies of 6.5 over 200 -> centres 40, 80, 120, 160; 40 mm above a
    # hole whose top is at 64
    got = run(PLATE + "add threaded_hole hc: on plate1, centred on plate1, thread M8\n"
              "add hole ht: on plate1, distributed over plate1 in 4 copies, offset from hc by "
              "40 mm on side above, diameter 6.5 mm\n")
    assert got["ht.1"] == ["36.75", "104", "43.25", "110.5"]
    assert got["ht.4"] == ["156.75", "104", "163.25", "110.5"]


def test_distributed_over_a_vertical_target_and_refusals():
    tall = "domain mechanical\nadd plate p: at origin, width 100 mm, height 300 mm\n"
    got = run(tall + "add hole h: on p, distributed over p in 2 copies, diameter 20 mm\n")
    assert got["h.1"] == ["40", "90", "60", "110"] and got["h.2"] == ["40", "190", "60", "210"]
    msg = refused(PLATE + "add hole h: on plate1, distributed over plate1 in 20 copies, "
                  "diameter 10 mm\n")
    assert "do not fit side by side" in msg and "200/21" in msg


# ---------------------------------------------------------------- corner features

def test_fillets_and_chamfers_take_the_corner_square():
    got = run(PLATE + "add fillet r: on plate1, radius 5 mm, corner all\n"
              "add chamfer c: on plate1, length 3 mm, corner top_left\n")
    assert got["r.bottom_left"] == ["0", "0", "5", "5"]
    assert got["r.bottom_right"] == ["195", "0", "200", "5"]
    assert got["r.top_left"] == ["0", "115", "5", "120"]
    assert got["r.top_right"] == ["195", "115", "200", "120"]
    assert got["c.top_left"] == ["0", "117", "3", "120"]


def test_the_fillet_arc_agrees_with_the_drafting_operation():
    # the top-left fillet of radius 5: ops.fillet on the two edges meeting at (0, 120)
    r = fillet(Segment((0, 120), (200, 120)), Segment((0, 120), (0, 0)), 5)
    assert r.piece.c == Point(5, 115)                 # the inner corner of the square above
    assert r.first.p == Point(5, 120) and r.second.p == Point(0, 115)


def test_corner_features_that_do_not_fit_are_refused():
    assert "does not fit" in refused(PLATE + "add fillet r: on plate1, radius 70 mm, "
                                     "corner all\n")              # 70 > 120 / 2
    got = run(PLATE + "add fillet r: on plate1, radius 100 mm, corner bottom_left\n")
    assert got["r.bottom_left"] == ["0", "0", "100", "100"]       # one corner: up to 120
    assert "does not fit" in refused(PLATE + "add fillet r: on plate1, radius 130 mm, "
                                     "corner bottom_left\n")


# ---------------------------------------------------------------- "on" checks

def test_a_feature_on_a_plate_must_stay_on_it():
    msg = refused(PLATE + "add hole h: on plate1, offset from plate1 by 5 mm on side right, "
                  "diameter 4 mm\n")
    assert msg == '"h": it is not on "plate1": the relations that place it put it partly off it'


def test_placement_is_the_same_to_the_byte_every_time():
    body = PLATE + ("add hole hs: on plate1, distributed over plate1 in 3 copies, "
                    "diameter 10 mm\nadd fillet r: on plate1, radius 5 mm, corner all\n")
    a = A.place(S.parse(H + body))
    b = A.place(S.parse(H + body))
    assert a == b and a.encode("ascii")
