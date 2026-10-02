"""The escape hatch -- verification of backlog task P1-T05 (ADR 0009).

Free-channel content is always flagged, in the script and in the output, can be
listed and reviewed on its own, and is never silently mixed with validated
geometry: checked objects can never be placed by it.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lang import anchoring as A   # noqa: E402
from lang import escape as E      # noqa: E402
from lang import script as S      # noqa: E402

H = S.HEADER + "\n"
PLATE = "domain mechanical\nadd plate plate1: at origin, width 200 mm, height 120 mm\n"


def spec_free_example():
    blocks = [t for k, _, t in S.spec_blocks() if k == "linework" and "\nfree " in t]
    with open(S.SPEC_PATH, "r", encoding="utf-8") as fh:
        spec = fh.read()
    quoted = re.search(r"```\n(# linework free channel.*?)```", spec, re.S)
    assert len(blocks) == 1 and quoted
    return blocks[0], quoted.group(1)


def free_line(name="cam", source="user", where="centred on plate1",
              shape="circle 0 0 radius 30", why="the user's cam"):
    return 'free %s: source %s, %s, unit mm, shape "%s"  # %s\n' % (name, source, where,
                                                                   shape, why)


# ---------------------------------------------------------- flagged in the script

def test_free_lines_are_flagged_in_the_script_and_round_trip():
    text, _ = spec_free_example()
    script = S.parse(text)
    assert str(script) == text
    assert S.check(script) == []
    free = script.free()
    assert [f.name for f in free] == ["cam", "mark"]
    for f in free:
        line = str(f)
        assert line.startswith("free ")                 # the word that flags it
        assert "source %s" % f.source in line           # where it came from
        assert "  # " in line and f.reason               # why the language was not enough
    assert all(not isinstance(s, S.Free) for s in script.statements())


def test_a_free_line_without_its_source_unit_shape_or_reason_is_refused():
    cases = [
        ('free cam: centred on plate1, unit mm, shape "circle 0 0 radius 30"  # cam\n',
         "line 4, column 9: a free object must give its source"),
        ('free cam: source user, centred on plate1, shape "circle 0 0 radius 30"  # cam\n',
         "line 4, column 9: a free object must give its unit"),
        ("free cam: source user, centred on plate1, unit mm  # cam\n",
         "line 4, column 9: a free object must give its shape"),
        ('free cam: source user, centred on plate1, unit mm, shape "circle 0 0 radius 30"\n',
         "line 4, column 80: a free object must say why the language could not say it: "
         "end the line with # and the reason"),
        ('free cam: source friend, centred on plate1, unit mm, shape "circle 0 0 radius 3"'
         "  # x\n", 'line 4, column 18: "friend" is not a source; a free object comes from: '
                    "user, model, import"),
        ('free cam: source user, source model, at origin, unit mm, shape "circle 0 0 '
         'radius 3"  # x\n', 'line 4, column 24: "source" is given twice'),
        ('free cam: source user, at origin, unit mm, width 3 mm, shape "circle 0 0 radius '
         '3"  # x\n', 'line 4, column 44: a free object takes source, unit, shape and the '
                      'relations that place it; "width" is a word for catalogue objects'),
        ('free cam: source user, at origin, unit mm, shape "circle 0 0 radius 0"  # x\n',
         'line 4, column 50: in the shape, part 1 "circle 0 0 radius 0": a radius must be '
         "greater than zero"),
        ('free cam: source user, at origin, unit mm, shape "line 0 0 to 1,5 0"  # x\n',
         'line 4, column 50: in the shape, part 1 "line 0 0 to 1,5 0": "1,5" is not a '
         "number: write 1.5"),
    ]
    for line, expected in cases:
        try:
            errors = S.check(S.parse(H + PLATE + line))
            got = str(errors[0]) if errors else None
        except S.ScriptError as exc:
            got = str(exc)
        assert got == expected, "\nexpected: %s\n     got: %s" % (expected, got)


def test_the_shape_has_a_ceiling():
    parts = "; ".join("line 0 0 to %d 0" % (i + 1) for i in range(100))
    S.parse(H + PLATE + free_line(shape=parts))
    try:
        S.parse(H + PLATE + free_line(shape=parts + "; line 0 0 to 0 1"))
    except S.ScriptError as exc:
        assert "at most 100 parts, not 101" in str(exc)
    else:
        raise AssertionError("a free shape of 101 parts was accepted")


# --------------------------------------- never mixed with validated geometry

def test_checked_geometry_is_never_placed_by_free_geometry():
    for rel in ("on cam", "centred on cam", "next to cam on side right",
                "offset from cam by 5 mm on side above", "aligned with cam on axis vertical",
                "inside cam", "at cam"):
        text = H + PLATE + free_line() + "add hole h1: %s, diameter 8 mm\n" % rel
        errors = [str(e) for e in S.check(S.parse(text))]
        assert len(errors) == 1 and '"cam" is free geometry, and checked geometry is never ' \
            "placed by it" in errors[0], (rel, errors)


def test_free_geometry_may_lean_on_checked_and_on_free():
    text = (H + PLATE + free_line()
            + free_line(name="cam2", where="next to cam on side right"))
    assert S.check(S.parse(text)) == []


def test_free_geometry_is_anchored_like_everything_else():
    text = H + PLATE + 'free cam: source user, unit mm, shape "circle 0 0 radius 3"  # x\n'
    assert [str(e) for e in S.check(S.parse(text))] == [
        'line 4: "cam" has no place: a free shape is placed by relations like everything else '
        "(the first object goes at origin)"]
    text = H + PLATE + free_line(where="aligned with plate1 on axis vertical")
    assert [str(p) for p in A.problems(S.parse(text))] == [
        'line 4: the up-down place of "cam" is not determined; add a relation that fixes it, '
        "such as centred on, aligned with ... on axis horizontal, or offset from ... on side "
        "below"]


def test_free_geometry_is_a_separate_section_of_the_output():
    text, _ = spec_free_example()
    out = A.place(S.parse(text)).split("\n")
    marker = out.index("# FREE CHANNEL -- not checked by the language; review separately")
    checked, free = out[:marker], out[marker + 1:]
    assert checked[2:] == ["plate1 plate 0 0 200 120", "h1 hole 96 56 104 64"]
    assert free[1:-1] == ["cam FREE user 100 60", "mark FREE model 200 0"]
    assert not any("FREE" in line for line in checked)
    assert not any(line.split(" ")[0] in ("plate1", "h1") for line in free)


def test_no_free_section_when_nothing_came_through_the_hatch():
    text = H + PLATE + "add hole h1: on plate1, centred on plate1, diameter 8 mm\n"
    assert "FREE" not in A.place(S.parse(text))
    assert E.report(S.parse(text)) == ("# linework free channel -- empty: every object "
                                       "passed the gate\n")


# ------------------------------------------ listed and reviewed separately

def test_the_free_channel_lists_exactly_what_the_specification_quotes():
    text, quoted = spec_free_example()
    assert E.report(S.parse(text)) == quoted


def test_free_content_is_always_flagged_whatever_the_script():
    # Random scripts mixing checked and free lines: every free line is listed,
    # marked in the output, and no checked line is ever marked or listed.
    rng = random.Random(20261002)
    for _ in range(200):
        lines, free_names, checked = [], [], ["plate1"]
        for i in range(rng.randint(1, 8)):
            if rng.random() < 0.5:
                name = "f%d" % i
                lines.append(free_line(name=name, source=rng.choice(S.FREE_SOURCES),
                                       where="offset from %s by %d mm on side %s"
                                       % (rng.choice(checked + free_names), rng.randint(1, 9),
                                          rng.choice(["left", "right", "above", "below"]))))
                free_names.append(name)
            else:
                name = "h%d" % i
                # circles, not holes: a hole must stay on its plate, and these
                # are placed anywhere around it
                lines.append("add circle %s: offset from %s by %d mm on side %s, "
                             "diameter 4 mm\n" % (name, rng.choice(checked), rng.randint(1, 9),
                                                  rng.choice(["left", "right", "above",
                                                              "below"])))
                checked.append(name)
        script = S.parse(H + PLATE + "domain general\n" + "".join(lines))
        assert S.check(script) == []
        report = E.report(script)
        out = A.place(script)
        for name in free_names:
            assert re.search(r"^%s  line \d+  source " % name, report, re.M), name
            assert re.search(r"^%s FREE " % name, out, re.M), name
        for name in checked:
            assert not re.search(r"^%s  line" % name, report, re.M), name
            assert not re.search(r"^%s FREE" % name, out, re.M), name
