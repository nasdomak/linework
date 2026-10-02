"""The blank page -- verification of backlog task P1-T04 (ADR 0008).

The same coordinate-free script produces byte-identical geometry twice, with
exact hand-computed values; ambiguity is refused rather than guessed; every
relation names its reference frame.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import copy
import os
import re
import sys
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geometry import placement as P   # noqa: E402
from lang import anchoring as A       # noqa: E402
from lang import form as F            # noqa: E402
from lang import script as S          # noqa: E402

H = S.HEADER + "\n"
CAT = F.default_catalogue()


def first_problem(text, catalogue=None):
    found = A.problems(S.parse(text), catalogue)
    return str(found[0]) if found else None


def spec_placement_example():
    """The coordinate-free script of SCRIPT.md and the placement it quotes."""
    with open(S.SPEC_PATH, "r", encoding="utf-8") as fh:
        spec = fh.read()
    script = [t for k, _, t in S.spec_blocks() if k == "linework" and "add hole h_t" in t]
    quoted = re.search(r"```\n(# linework placement 1.*?)```", spec, re.S)
    assert len(script) == 1 and quoted
    return script[0], quoted.group(1)


# ------------------------------------------------- one determinate drawing

def test_a_coordinate_free_script_gives_byte_identical_geometry_twice():
    text, quoted = spec_placement_example()
    assert not re.search(r"\b(x|y|position|point)\b", text.split("\n", 1)[1])
    first = A.place(S.parse(text)).encode("utf-8")
    second = A.place(S.parse(text)).encode("utf-8")
    assert first == second
    assert first.decode("utf-8") == quoted, "SCRIPT.md quotes a different placement"


def test_the_placement_is_exact_and_matches_the_hand_computation():
    text = (H + "domain architecture\n"
            "add room living: at origin, width 5 m, length 4 m\n"
            "add room kitchen: next to living on side right, width 3 m, length 4 m\n"
            "add room bath: next to kitchen on side above, width 2 m, length 2.5 m\n"
            "add column c1: inside living, centred on living, diameter 30 cm\n"
            "add column c2: inside kitchen, aligned with c1 on axis horizontal, "
            "offset from living by 1 m on side right, width 25 cm\n")
    got = A.place(S.parse(text)).split("\n")[2:-1]
    # by hand, in mm: living 5000 x 4000 at origin; kitchen against its right
    # edge, flush at the bottom; bath on top of the kitchen, flush at the left;
    # c1 on the centre of living; c2 1 m right of living, at c1's height.
    assert got == ["living room 0 0 5000 4000",
                   "kitchen room 5000 0 8000 4000",
                   "bath room 5000 4000 7000 6500",
                   "c1 column 2350 1850 2650 2150",
                   "c2 column 6000 1875 6250 2125"], got


def test_units_are_converted_exactly_never_approximately():
    assert P.to_mm(6.5, "cm") == Fraction(65)
    assert P.to_mm(0.1, "m") + P.to_mm(0.2, "m") == P.to_mm(0.3, "m")   # 0.1 + 0.2 == 0.3
    assert P.fmt(Fraction(1, 3)) == "1/3"
    assert P.fmt(Fraction(-13, 4)) == "-3.25"


def test_inside_is_checked_not_assumed():
    text = (H + "domain architecture\nadd room living: at origin, width 5 m, length 4 m\n"
            "add column c1: inside living, at origin, offset from living by 1 m on side "
            "right, diameter 30 cm\n")
    # "at origin" and "offset ... right" both fix left-right: refused before any number
    assert first_problem(text).startswith('line 4: the left-right place of "c1" is fixed twice')
    text = (H + "domain architecture\nadd room living: at origin, width 5 m, length 4 m\n"
            "add column c1: inside living, aligned with living on axis horizontal, "
            "offset from living by 1 m on side right, diameter 30 cm\n")
    assert first_problem(text) is None          # determinate...
    try:
        A.place(S.parse(text))                  # ...but outside the room
    except P.PlacementError as exc:
        assert str(exc) == ('"c1": it is not inside "living": the relations that place it '
                            "put it partly outside")
    else:
        raise AssertionError("a column outside its room was placed")


def test_what_this_phase_cannot_compute_is_refused_not_guessed():
    text = (H + "domain civil\nadd plot plot1: at origin, width 30 m, length 45 m\n"
            "add road road1: along plot1 on side below, width 6 m\n")
    assert first_problem(text) is None          # the place is determined...
    try:
        A.place(S.parse(text))                  # ...the number is the phase-2 solver's
    except P.NotPlacedYet as exc:
        assert str(exc) == '"road1": its size is not known here, so it is placed by the ' \
                           "solver of phase 2"
    else:
        raise AssertionError("along was placed without a solver")


# ----------------------------------------------------- ambiguity is refused

def test_every_unplaced_example_of_the_specification_is_refused_as_stated():
    n = 0
    for kind, first, text in S.spec_blocks():
        if kind != "linework-unplaced":
            continue
        assert S.check(S.parse(text)) == [], "SCRIPT.md line %d is not even sound" % first
        want = text.rstrip("\n").split("\n")[-1]
        assert want.startswith("# unplaced: "), first
        assert first_problem(text) == want[len("# unplaced: "):], (first, first_problem(text))
        n += 1
    assert n >= 5


def test_every_sound_example_of_the_specification_is_one_determinate_drawing():
    n = 0
    for kind, first, text in S.spec_blocks():
        script = S.parse(text) if kind == "linework" else None
        if script is None or script.open_choices():
            continue
        assert A.problems(script) == [], (first, [str(p) for p in A.problems(script)])
        n += 1
    assert n >= 7


def test_an_open_choice_is_not_anchored():
    text = [t for k, _, t in S.spec_blocks() if k == "linework" and "entrance: open" in t][0]
    try:
        A.analyse(S.parse(text))
    except S.OpenChoiceError as exc:
        assert "cannot draw" in str(exc)
    else:
        raise AssertionError("an open choice was anchored")


def test_two_defaults_on_one_axis_are_refused_too():
    # In the v1 catalogue every default comes with a firm fix on the other axis,
    # so two defaults always show up first as "fixed twice". The rule must still
    # hold for a catalogue where that is not so.
    cat = copy.deepcopy(CAT)
    cat["relations"]["centred_on"]["fixes"] = {"x": "default", "y": "default"}
    text = (H + "domain mechanical\nadd plate p1: at origin, width 200 mm, height 120 mm\n"
            "add plate p2: at origin, width 20 mm, height 10 mm\n"
            "add hole h1: on p1, centred on p1, centred on p2, diameter 8 mm\n")
    assert first_problem(text, cat) == ('line 5: the left-right place of "h1" is suggested '
                                        'twice, by "centred on p1" and by "centred on p2"; fix '
                                        "it with one relation")


def test_an_object_placed_by_an_unplaced_one_is_reported_too():
    text = (H + "domain architecture\nadd room living: at origin, width 5 m, length 4 m\n"
            "add room kitchen: width 3 m, length 4 m\n"
            "add room bath: next to kitchen on side above, width 2 m, length 2 m\n")
    assert [str(p) for p in A.problems(S.parse(text))] == [
        'line 4: "kitchen" has no place: say where it goes relative to something that exists '
        "(the first object goes at origin)",
        'line 5: "bath" is placed by "kitchen", whose own place is not determined']


def test_a_change_that_gives_relations_replaces_them():
    text = (H + "domain architecture\nadd room living: at origin, width 5 m, length 4 m\n"
            "add room kitchen: next to living on side right, width 3 m, length 4 m\n"
            "change room kitchen: next to living on side above\n")
    assert A.place(S.parse(text)).split("\n")[3] == "kitchen room 0 4000 3000 8000"
    text = text.replace("change room kitchen: next to living on side above",
                        "change room kitchen: width 2 m")
    assert A.place(S.parse(text)).split("\n")[3] == "kitchen room 5000 0 7000 4000"


def test_corner_features_are_placed_by_their_corner():
    text = (H + "domain mechanical\nadd plate p1: at origin, width 200 mm, height 120 mm\n"
            "add fillet f: on p1, radius 5 mm, corner all\n")
    assert A.problems(S.parse(text)) == []
    assert A.analyse(S.parse(text))[1] == ("f", "corner")


# ------------------------------------------- every relation names its frame

def test_every_relation_names_its_reference_frame():
    for word, entry in CAT["relations"].items():
        assert len(entry["frame"]) > 40, word
        assert isinstance(entry["fixes"], dict), word
    assert set(CAT["parameters"]["side"]["values"]) == {"left", "right", "above", "below"}
    with open(os.path.join(ROOT, "docs", "CATALOGUE.md"), "r", encoding="utf-8") as fh:
        doc = fh.read()
    for word, entry in CAT["relations"].items():
        assert entry["frame"] in doc, word


def test_the_catalogue_check_refuses_a_relation_without_a_frame():
    from shared import catalogue as C
    cat = copy.deepcopy(CAT)
    cat["relations"]["next_to"]["frame"] = ""
    assert "relations.next_to does not name its reference frame" in C.check(cat)
    cat = copy.deepcopy(CAT)
    cat["relations"]["next_to"]["fixes"] = {"z": "firm"}
    assert any(p.startswith("relations.next_to: 'fixes'") for p in C.check(cat))


def test_the_rules_are_written_in_the_specification():
    with open(S.SPEC_PATH, "r", encoding="utf-8") as fh:
        spec = fh.read()
    for phrase in ("The first object goes `at origin`", '"Beside", "by", "adjacent to"',
                   "The sheet is the one frame", "Every object has a reference point",
                   "Every relation names its frame", "decided exactly"):
        assert phrase in spec, phrase


def test_an_invalid_script_reports_its_validation_errors_not_a_crash():
    # Anchoring runs only on a sound script: "inside" is no longer a side
    # (it names no edge), and the validator says so before anchoring starts.
    text = (H + "domain mechanical\nadd plate p1: at origin, width 200 mm, height 120 mm\n"
            "add hole h1: on p1, offset from p1 by 15 mm on side inside, diameter 8 mm\n")
    assert [str(p) for p in A.problems(S.parse(text))] == [
        'line 4: in "offset from p1 by 15 mm on side inside": "inside" is not a known value '
        "of side. Known values of side: above, below, left, right"]
