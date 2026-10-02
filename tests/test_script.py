"""The script language -- verification of backlog task P1-T02 (ADR 0006).

Round-trips every example in docs/SCRIPT.md, asserts every refused example
fails with exactly the error it states, and asserts parser errors point at the
offending line (and column). Also: forms written as lines and read back are the
same forms; a refused form is never written; damage never crashes the parser.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import copy
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lang import form as F            # noqa: E402
from lang import script as S          # noqa: E402

H = S.HEADER + "\n"


def error_of(text):
    """The first error a script produces, as text; None if it is accepted."""
    try:
        errors = S.check(S.parse(text))
    except S.ScriptError as exc:
        return str(exc)
    return str(errors[0]) if errors else None


def assert_refused(text, expected):
    got = error_of(text)
    assert got == expected, "\nexpected: %s\n     got: %s" % (expected, got)


# --------------------------------------------------------- the specification

def test_the_specification_has_examples_of_both_kinds():
    blocks = S.spec_blocks()
    kinds = [k for k, _, _ in blocks]
    assert kinds.count("linework") >= 6
    assert kinds.count("linework-refused") >= 6


def test_every_accepted_example_round_trips_exactly_and_is_sound():
    for kind, first, text in S.spec_blocks():
        if kind != "linework":
            continue
        script = S.parse(text)
        assert str(script) == text, "SCRIPT.md line %d does not print back as written" % first
        assert S.check(script) == [], "SCRIPT.md line %d: %s" % (first, S.check(script)[0])


def test_every_refused_example_fails_with_the_error_it_states():
    for kind, first, text in S.spec_blocks():
        if kind != "linework-refused":
            continue
        last = text.rstrip("\n").split("\n")[-1]
        assert last.startswith("# refused: "), "SCRIPT.md line %d has no stated error" % first
        assert_refused(text, last[len("# refused: "):])


def test_the_specification_covers_the_whole_vocabulary_of_position():
    used = set()
    for kind, _, text in S.spec_blocks():
        if kind == "linework":
            for st in S.parse(text).statements():
                used |= set(c.word for c in st.clauses if c.kind == "relation")
    # the six the backlog names, and in fact every relation in the catalogue
    for rel in ("centred_on", "along", "offset_from", "between", "aligned_with",
                "distributed_over"):
        assert rel in used, rel
    assert used == set(F.default_catalogue()["relations"]), \
        sorted(set(F.default_catalogue()["relations"]) - used)


def test_the_specification_covers_all_four_trades_and_every_act():
    domains, acts = set(), set()
    for kind, _, text in S.spec_blocks():
        if kind == "linework":
            for st in S.parse(text).statements():
                domains.add(st.domain)
                acts.add(st.act)
    assert {"mechanical", "architecture", "civil", "schematic"} <= domains
    assert acts == {"add", "change", "remove"}


# ------------------------------------------------- the engine writes the lines

def strip_said(form):
    f = copy.deepcopy(form)
    for v in f.get("dimensions", {}).values():
        v.pop("said", None)
    for r in f.get("relations", []):
        for p in ("distance", "count"):
            if p in r:
                r[p].pop("said", None)
    if "reason" in f:
        f["reason"] = " ".join(f["reason"].split())
    return f


def test_a_form_written_as_a_line_reads_back_as_the_same_form():
    n = 0
    for ref, domain, ex in F.load_examples():
        if not ex["expect"]["ok"]:
            continue
        line = str(S.statement_from_form(ex["form"]))
        text = H + "domain %s\n" % domain + line + "\n"
        back = S.parse(text).forms()[0]
        assert strip_said(back) == strip_said(ex["form"]), ref
        assert F.validate(back, known=ex["known"]).ok, ref
        n += 1
    assert n >= 15


def test_from_forms_writes_a_whole_script_and_it_round_trips():
    forms = []
    for kind, _, text in S.spec_blocks():
        if kind == "linework" and "domain general" in text:
            forms = S.parse(text).forms()
    assert forms
    written = S.from_forms(forms)
    assert S.check(written) == []
    again = S.parse(str(written))
    assert str(again) == str(written)
    assert [strip_said(f) for f in again.forms()] == [strip_said(f) for f in forms]


def test_a_refused_form_is_never_written():
    bad = [ex["form"] for _, _, ex in F.load_examples() if not ex["expect"]["ok"]][0]
    try:
        S.from_forms([bad])
    except ValueError as exc:
        assert "is refused, so it is not written" in str(exc)
    else:
        raise AssertionError("a refused form was written as a script line")


def test_no_line_the_engine_writes_contains_a_coordinate_field():
    for kind, _, text in S.spec_blocks():
        if kind == "linework":
            for st in S.parse(text).statements():
                words = set(str(st).replace(",", " ").replace(":", " ").split())
                assert not words & {"x", "y", "position", "point", "coordinates"}, str(st)


# ------------------------------------------------- errors point at the line

def test_parser_errors_name_the_line_and_the_column():
    cases = [
        ("add plate p1: at origin\n",
         'line 1: a script starts with the line "linework script 1"'),
        (H + "domain mechanical\n\tadd plate p1: at origin\n",
         "line 3, column 1: a tab: use spaces"),
        (H + "domain mechanical\ndraw plate p1: at origin\n",
         'line 3, column 1: a line starts with domain, choice, option, free, #, or an act (add, '
         'change, remove), not "draw"'),
        (H + "domain mechanics\n",
         'line 2, column 8: "mechanics" is not a domain; use one of: architecture, civil, '
         "general, mechanical, schematic"),
        (H + "domain mechanical\nadd plaque p1: at origin\n",
         'line 3, column 5: "plaque" is not an object kind'),
        (H + "domain mechanical\nadd plate P1: at origin\n",
         "line 3, column 11: the object's name must be a name (lower-case letters, digits, "
         'underscores), not "P1"'),
        (H + "domain mechanical\nadd plate p1: at origin,, width 2 mm\n",
         "line 3, column 25: an empty clause: two commas in a row, or a comma at the end"),
        (H + "domain mechanical\nadd plate p1: at origin, width 2\n",
         "line 3, column 33: the unit of width (cm, m, mm) is missing here"),
        (H + "domain mechanical\nadd plate p1: at origin, width two mm\n",
         'line 3, column 32: width needs a number, but "two" is not one'),
        (H + "domain mechanical\nadd plate p1: at origin, width 2 mm wide\n",
         'line 3, column 37: unexpected "wide" after width'),
        (H + "domain mechanical\nadd plate p1: at origin on side left\n",
         'line 3, column 25: unexpected "on": "at" takes nothing after its object'),
        (H + "domain civil\nadd pipe p: between mh1 mh2\n",
         'line 3, column 25: "between" takes two objects: between X and Y'),
        (H + "domain mechanical\nadd hole h: distributed over p1 in 4\n",
         'line 3, column 37: the word "copies" is missing here'),
        (H + "domain mechanical\nadd hole h: offset from p1 by 5 mm on axis vertical\n",
         'line 3, column 36: unexpected "on" after "offset from p1"; it takes only: by '
         "<distance>; on side <side>"),
        (H + "domain general\nadd text t: at origin, text Hello\n",
         'line 3, column 24: text is written as: text "the words"'),
        (H + 'domain general\nadd text t: at origin, text "Hello\n',
         'line 3, column 29: a text is opened with " but never closed'),
        (H + 'domain general\nadd text t: at origin, text "a \\q"\n',
         'line 3, column 32: inside a text only \\" and \\\\ may follow a backslash'),
        (H + "domain mechanical\nadd plate p1:\n",
         "line 3, column 14: an empty clause: two commas in a row, or a comma at the end"),
        (H + "domain mechanical\nadd plate p1 at origin\n",
         'line 3, column 14: a colon must follow the name "p1"; then come the clauses'),
        (H + "domain mechanical\nadd plate\n",
         "line 3, column 1: a statement starts with: <act> <kind> <name>, then a colon "
         "and its clauses"),
        (H + "domain mechanical\nadd hole h: diameter 6,5 mm\n",
         'line 3, column 22: "6,5" is not a number here: write 6.5 -- in a script the '
         "comma separates clauses"),
    ]
    for text, expected in cases:
        assert_refused(text, expected)
    assert len(cases) >= 15


def test_validation_errors_name_the_line_of_the_statement():
    text = (H + "domain mechanical\n\n# a comment\nadd plate p1: at origin, width 2 mm, "
            "height 1 mm\nadd hole h1: on p1, diameter 1 mm\nadd hole h1: on p1, "
            "diameter 2 mm\n")
    assert_refused(text, 'line 7: "h1" already exists (a hole); adding needs a new name, '
                         'or use the act "change"')


def test_check_reports_every_bad_line_not_just_the_first():
    text = (H + "domain mechanical\nadd hole h1: on p9, diameter 1 mm\n"
            "add hole h2: on p9, diameter 1 mm\n")
    lines = [e.line for e in S.check(S.parse(text))]
    assert lines == [3, 4], lines


# ----------------------------------------------------------------- layout

def test_loose_spacing_is_read_the_same_and_written_tidy():
    loose = (H + "domain   mechanical\n\n\nadd  plate  p1 :at origin ,width 200 mm,"
             "height   120 mm   #   the part\n#tidy me\n\n")
    tidy = (H + "domain mechanical\n\n\nadd plate p1: at origin, width 200 mm, "
            "height 120 mm  # the part\n# tidy me\n")
    assert str(S.parse(loose)) == tidy
    assert str(S.parse(tidy)) == tidy


def test_texts_keep_quotes_backslashes_and_hashes():
    text = H + 'domain general\nadd text t: at origin, text "a \\"b\\" \\\\ # c"  # why\n'
    script = S.parse(text)
    assert script.forms()[0]["text"] == 'a "b" \\ # c'
    assert script.forms()[0]["reason"] == "why"
    assert str(script) == text


def test_numbers_print_in_their_shortest_form():
    assert S.fmt_number(120) == "120"
    assert S.fmt_number(120.0) == "120"
    assert S.fmt_number(6.5) == "6.5"
    assert S.fmt_number(0.00001) == "0.00001"
    assert S.fmt_number(1234567.125) == "1234567.125"


def test_windows_line_endings_are_read():
    text = (H + "domain mechanical\nadd plate p1: at origin, width 2 mm, height 1 mm\n")
    assert str(S.parse(text.replace("\n", "\r\n"))) == text


# ------------------------------------------------------------- robustness

def test_damage_never_crashes_the_parser():
    rng = random.Random(20261001)
    texts = [t for k, _, t in S.spec_blocks()]
    alphabet = list(' ,:#"\\\t\r\nabcxyz0123456789.-_') + ["on ", "and ", "by ", "in "]
    for _ in range(2000):
        t = list(rng.choice(texts))
        for _ in range(rng.randint(1, 4)):
            i = rng.randrange(len(t))
            op = rng.random()
            if op < 0.4:
                t[i] = rng.choice(alphabet)
            elif op < 0.7:
                del t[i]
            else:
                t.insert(i, rng.choice(alphabet))
        text = "".join(t)
        try:
            script = S.parse(text)
            for e in S.check(script):
                assert e.line >= 1
            assert str(S.parse(str(script))) == str(script)   # printing is stable
        except S.ScriptError as exc:
            assert exc.line >= 1 and exc.message


def test_a_refused_line_does_not_create_its_object():
    # The plate is refused (no height), so it does not exist, and the hole that
    # names it is reported too: the truth, not a cascade to hide.
    text = (H + "domain mechanical\nadd plate p1: at origin, width 2 mm\n"
            "add hole h1: on p1, diameter 1 mm\n")
    errors = [str(e) for e in S.check(S.parse(text))]
    assert errors == [
        "line 3: a plate needs a height. If the user did not give one, ask: never guess "
        "a number",
        'line 4: in "on p1": there is no object called "p1"; known objects: origin'], errors
