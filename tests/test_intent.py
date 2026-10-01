"""Design intent and alternatives -- verification of backlog task P1-T03 (ADR 0007).

A script with an unresolved choice refuses to produce geometry and names the
choice; a decided one draws exactly the chosen alternative; the alternatives
not taken stay in the script as the record of what was considered.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lang import script as S   # noqa: E402

H = S.HEADER + "\n"


def spec_choice_examples():
    """The open and the decided example of docs/SCRIPT.md, and the refusal it quotes."""
    blocks = [t for k, _, t in S.spec_blocks() if k == "linework" and "choice entrance" in t]
    opened = [t for t in blocks if "choice entrance: open" in t]
    decided = [t for t in blocks if "choice entrance: decided" in t]
    with open(S.SPEC_PATH, "r", encoding="utf-8") as fh:
        quoted = re.findall(r"^(line \d+: cannot draw: .*)$", fh.read(), re.M)
    assert len(opened) == 1 and len(decided) == 1 and len(quoted) == 1
    return opened[0], decided[0], quoted[0]


def refusal(script):
    try:
        script.drawable()
    except S.OpenChoiceError as exc:
        return str(exc)
    return None


def test_an_open_choice_refuses_to_produce_geometry_and_names_it():
    opened, _, quoted = spec_choice_examples()
    script = S.parse(opened)
    assert S.check(script) == []          # the script itself is sound...
    assert refusal(script) == quoted      # ...but it cannot be drawn, and says why
    assert '"entrance"' in quoted and "street, garden" in quoted


def test_two_open_choices_are_both_named():
    text = (H + "domain mechanical\nadd plate p1: at origin, width 200 mm, height 120 mm\n"
            "choice fixing: open\n"
            "option fixing bolts: add hole h1: on p1, centred on p1, diameter 9 mm\n"
            "option fixing studs: add threaded_hole h1: on p1, centred on p1, thread M8\n"
            "choice edge: open  # sharp or soft?\n"
            "option edge round: add fillet e: on p1, radius 5 mm, corner all\n"
            "option edge bevel: add chamfer e: on p1, length 3 mm, corner all\n")
    assert refusal(S.parse(text)) == (
        'line 4: cannot draw: 2 choices are still open: "fixing" (line 4, options bolts, '
        'studs); "edge" (line 7, options round, bevel); decide them first')


def test_a_decided_choice_draws_exactly_the_chosen_alternative():
    _, decided, _ = spec_choice_examples()
    script = S.parse(decided)
    assert S.check(script) == []
    drawn = [str(s) for s in script.drawable()]
    assert "add door d1: on wall_east, centred on wall_east, width 90 cm  # opens on the garden" \
        in drawn
    assert not any("wall_south, centred on wall_south, width 90 cm" in d for d in drawn)
    assert drawn[-1].startswith("add column c1:")      # what follows the choice is kept
    assert len(drawn) == 3 + 2 + 1


def test_deciding_changes_one_word_and_keeps_the_alternatives():
    opened, decided, _ = spec_choice_examples()
    script = S.parse(opened).decide("entrance", "garden",
                                    "The user wants to step out onto the garden.")
    before, after = str(S.parse(opened)).split("\n"), str(script).split("\n")
    changed = [(a, b) for a, b in zip(before, after) if a != b]
    assert changed == [("choice entrance: open  # Where does the front door go? The user has "
                        "not said yet.",
                        "choice entrance: decided garden  # The user wants to step out onto "
                        "the garden.")]
    assert sum(1 for line in after if line.startswith("option entrance street:")) == 1
    assert decided.split("\n")[7] == after[7]


def test_deciding_for_something_that_is_not_there_is_refused():
    opened, _, _ = spec_choice_examples()
    script = S.parse(opened)
    for args, message in ((("roof", "flat"), 'there is no choice called "roof"'),
                          (("entrance", "back"), 'choice "entrance" has no option "back"; its '
                                                 "options are street, garden")):
        try:
            script.decide(*args)
        except ValueError as exc:
            assert str(exc) == message, str(exc)
        else:
            raise AssertionError("decide%r was accepted" % (args,))


def test_after_an_open_choice_only_what_every_option_agrees_on_exists():
    opened, _, _ = spec_choice_examples()
    ok = opened + "add window w3: on wall_south, width 60 cm\n"
    assert S.check(S.parse(ok)) == []
    bad = opened + "change window w_garden: width 100 cm\n"
    errors = [str(e) for e in S.check(S.parse(bad))]
    assert errors == ['line 14: there is no object called "w_garden" to change'], errors


def test_each_alternative_is_checked_on_its_own():
    text = (H + "domain mechanical\nadd plate p1: at origin, width 200 mm, height 120 mm\n"
            "choice fixing: open\n"
            "option fixing bolts: add hole h1: on p1, centred on p1, diameter 9 mm\n"
            "option fixing studs: add threaded_hole h1: on p9, centred on p1, thread M8\n")
    errors = [str(e) for e in S.check(S.parse(text))]
    assert errors == ['line 6: in "on p9": there is no object called "p9"; known objects: '
                      "origin, p1"], errors


def test_an_alternative_does_not_see_another_alternative():
    text = (H + "domain mechanical\nadd plate p1: at origin, width 200 mm, height 120 mm\n"
            "choice fixing: open\n"
            "option fixing bolts: add hole h1: on p1, centred on p1, diameter 9 mm\n"
            "option fixing studs: add slot s1: on p1, aligned with h1 on axis vertical, "
            "length 30 mm, width 6 mm\n")
    errors = [str(e) for e in S.check(S.parse(text))]
    assert len(errors) == 1 and errors[0].startswith(
        'line 6: in "aligned with h1 on axis vertical": there is no object called "h1"'), errors


def test_malformed_choice_lines_name_their_line():
    cases = [
        (H + "domain mechanical\nchoice fixing open\n",
         "line 3, column 15: a choice is written as: choice <name>: open -- or -- choice "
         "<name>: decided <option>"),
        (H + "domain mechanical\nchoice fixing: maybe\n",
         'line 3, column 16: after "choice fixing:" comes "open" or "decided <option>"'),
        (H + "domain mechanical\noption fixing a: add plate p1: at origin\n",
         'line 3: there is no choice called "fixing": write "choice fixing: open" first'),
        (H + "domain mechanical\nchoice fixing: open\noption fixing a:\n",
         "line 4, column 16: an option holds a statement after its colon"),
        (H + "domain mechanical\nchoice f: open\noption f a: draw plate p1: at origin\n",
         'line 4, column 13: a statement starts with an act (add, change, remove), not '
         '"draw"'),
        (H + "domain mechanical\nchoice f: open\noption f a: add plate p1: width 2 mm\n"
         "option f b: add plate p1: width 3 mm\nchoice f: open\n",
         'line 6: there is already a choice called "f" (line 3)'),
    ]
    for text, expected in cases:
        try:
            S.parse(text)
        except S.ScriptError as exc:
            assert str(exc) == expected, "\nexpected: %s\n     got: %s" % (expected, exc)
        else:
            raise AssertionError("accepted: %r" % text)


def test_a_script_without_choices_draws_its_statements_unchanged():
    for kind, _, text in S.spec_blocks():
        if kind == "linework" and "choice" not in text:
            script = S.parse(text)
            assert script.drawable() == script.statements()
