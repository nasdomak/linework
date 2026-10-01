"""The commitment form -- verification of backlog task P1-T01 (ADR 0005).

Feeds valid and invalid forms to lang.form.validate and asserts acceptance,
refusal, and the exact wording of each refusal. Also checks that the catalogue
is consistent, that the generated schema and catalogue document are current,
that the schema is never looser than the validator, and that the validator
refuses garbage instead of crashing.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import copy
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lang import form as F          # noqa: E402
from shared import catalogue as C   # noqa: E402

CAT = C.load()
DOMAINS = ("mechanical", "architecture", "civil", "schematic")


def base():
    """A form that is accepted: the window of ADR 0001."""
    return {
        "form": "linework/commitment", "version": 1,
        "domain": "architecture", "act": "add",
        "object": {"kind": "window", "name": "w1"},
        "relations": [{"relation": "on", "to": ["wall_north"]},
                      {"relation": "centred_on", "to": ["wall_north"]}],
        "dimensions": {"width": {"value": 120, "unit": "cm", "said": "width 120"}},
    }


USER = "a window on the north wall, centred, width 120"
KNOWN = {"wall_north": "wall", "wall_east": "wall", "plate1": "plate", "w9": "window"}


def verdict(form, user=USER, known=KNOWN):
    return F.validate(form, user_text=user, known=known)


def refused_with(form, message, user=USER, known=KNOWN):
    v = verdict(form, user, known)
    assert not v.ok, "expected a refusal, got acceptance"
    assert message in v.messages(), "expected %r, got %s" % (message, v.messages())
    return v


# ------------------------------------------------------------ the catalogue

def test_catalogue_is_consistent():
    assert C.check(CAT) == []


def test_catalogue_check_catches_a_dangling_reference():
    broken = copy.deepcopy(CAT)
    broken["objects"]["window"]["host"] = ["wal"]
    assert "objects.window is hosted by unknown kind 'wal'" in C.check(broken)
    broken = copy.deepcopy(CAT)
    broken["relations"]["on"]["meaning"] = " "
    assert "relations.on has no meaning" in C.check(broken)


def test_every_vocabulary_word_has_one_entry_with_a_meaning():
    pairs = C.words(CAT)
    assert len(pairs) == len(set(pairs)), "a word appears twice in one block"
    assert len(pairs) > 100
    for block, word in pairs:
        assert re.match(r"^[A-Za-z][A-Za-z0-9_]*$", word), (block, word)


def test_the_four_domains_and_the_position_vocabulary_exist():
    for d in DOMAINS:
        assert any(e["domain"] == d for e in CAT["objects"].values()), d
    # P1-T02 needs these; they are committed through the form first.
    for r in ("centred_on", "along", "offset_from", "between", "aligned_with",
              "distributed_over"):
        assert r in CAT["relations"], r


def test_no_field_anywhere_is_a_coordinate_word():
    words = set(F.FIELDS) | set(F.OBJECT_FIELDS) | set(F.VALUE_FIELDS)
    words |= set(CAT["quantities"]) | set(CAT["properties"]) | set(CAT["parameters"])
    assert not words & F.COORDINATE_WORDS, words & F.COORDINATE_WORDS


# ----------------------------------------------------------- generated files

def test_generated_schema_and_catalogue_document_are_current():
    stale = F.stale_files()
    assert stale == [], "run: python3 -m lang.form write  (stale: %s)" % stale


def test_schema_lists_match_the_catalogue():
    s = F.build_schema()
    p = s["properties"]
    assert p["domain"]["enum"] == sorted(CAT["domains"])
    assert p["object"]["properties"]["kind"]["enum"] == sorted(CAT["objects"])
    assert sorted(p["dimensions"]["properties"]) == sorted(CAT["quantities"])
    assert [r["properties"]["relation"]["const"] for r in p["relations"]["items"]["oneOf"]] \
        == sorted(CAT["relations"])


def test_schema_is_closed_everywhere():
    def walk(node, where):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, where
            for k, v in node.items():
                walk(v, where + "/" + k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s[%d]" % (where, i))
    walk(F.build_schema(), "")


# A small reader for the subset of JSON Schema that build_schema uses. It lets
# the suite prove, without the jsonschema package, that the published schema is
# never looser than the validator.
def schema_ok(node, value):
    if "const" in node and value != node["const"]:
        return False
    if "enum" in node and (not isinstance(value, (str, int)) or isinstance(value, bool)
                           or value not in node["enum"]):
        return False
    if "not" in node and schema_ok(node["not"], value):
        return False
    t = node.get("type")
    if t == "object":
        if not isinstance(value, dict):
            return False
        props = node.get("properties", {})
        if any(k not in props for k in value) and node.get("additionalProperties") is False:
            return False
        if any(k not in value for k in node.get("required", [])):
            return False
        return all(schema_ok(props[k], v) for k, v in value.items() if k in props)
    if t == "array":
        if not isinstance(value, list):
            return False
        if len(value) < node.get("minItems", 0) or len(value) > node.get("maxItems", 10 ** 9):
            return False
        return all(schema_ok(node["items"], v) for v in value)
    if t == "string":
        if not isinstance(value, str) or len(value) < node.get("minLength", 0) \
                or len(value) > node.get("maxLength", 10 ** 9):
            return False
        return "pattern" not in node or re.match(node["pattern"], value) is not None
    if t in ("number", "integer"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if t == "integer" and not float(value).is_integer():
            return False
        if "minimum" in node and value < node["minimum"]:
            return False
        if "exclusiveMinimum" in node and value <= node["exclusiveMinimum"]:
            return False
        if "exclusiveMaximum" in node and value >= node["exclusiveMaximum"]:
            return False
    if "oneOf" in node:
        return sum(1 for n in node["oneOf"] if schema_ok(n, value)) == 1
    return True


def test_schema_reader_accepts_the_base_form_and_refuses_a_coordinate():
    s = F.build_schema()
    assert schema_ok(s, base())
    f = base()
    f["x"] = 3
    assert not schema_ok(s, f)


def test_whatever_the_schema_refuses_the_validator_refuses_too():
    s = F.build_schema()
    forms = [ex["form"] for _, _, ex in F.load_examples()] + list(mutations(400))
    checked = 0
    for f in forms:
        if not schema_ok(s, f):
            checked += 1
            assert not F.validate(f).ok, "schema refuses, validator accepts: %s" % json.dumps(f)
    assert checked > 50


# ------------------------------------------------------------ worked examples

def test_worked_examples_cover_all_four_domains_both_ways():
    seen = dict((d, set()) for d in DOMAINS)
    for ref, domain, ex in F.load_examples():
        seen[domain].add(ex["expect"]["ok"])
        assert ex["form"]["domain"] == domain, ref
    for d in DOMAINS:
        assert seen[d] == {True, False}, "%s lacks an accepted or a refused example" % d


def test_every_worked_example_behaves_as_it_says():
    examples = F.load_examples()
    assert len(examples) >= 30
    for ref, _, ex in examples:
        assert F.check_example(ex) == [], "%s %s: %s" % (ref, ex["title"], F.check_example(ex))


def test_every_refused_example_states_its_reasons_word_for_word():
    for ref, _, ex in F.load_examples():
        if not ex["expect"]["ok"]:
            assert ex["expect"].get("messages"), ref


# ------------------------------------------------------------- acceptance

def test_the_window_of_adr_0001_is_accepted():
    v = verdict(base())
    assert v.ok, v.explain()
    assert v.explain() == "accepted"


def test_acceptance_without_drawing_or_user_text_checks_only_the_form():
    assert F.validate(base()).ok


def test_change_and_remove_are_accepted_on_existing_objects():
    f = base()
    f["act"] = "change"
    f["object"]["name"] = "w9"
    del f["relations"]
    assert verdict(f).ok
    f = {"form": "linework/commitment", "version": 1, "domain": "architecture",
         "act": "remove", "object": {"kind": "window", "name": "w9"}}
    assert verdict(f).ok


# -------------------------------------------------------------- refusals

def test_refusal_wording():
    # (what to do to the base form, the exact refusal it must produce)
    cases = [
        (lambda f: f.update(x=10),
         'x: field "x" would carry a coordinate; the form never takes coordinates '
         "-- state a relation instead (ADR 0001)"),
        (lambda f: f.update(colour="red"),
         'colour: field "colour" is not part of the form; it has only: act, dimensions, '
         "domain, form, object, properties, reason, relations, text, version"),
        (lambda f: f.pop("act"), 'field "act" is missing'),
        (lambda f: f.update(form="other"), 'form: must be "linework/commitment"'),
        (lambda f: f.update(version=2),
         "version: this is form version 2; this validator speaks version 1"),
        (lambda f: f.update(domain="architektur"),
         'domain: "architektur" is not a known domain. Did you mean "architecture"? Known '
         "domains: architecture, civil, general, mechanical, schematic"),
        (lambda f: f.update(act="draw"),
         'act: "draw" is not a known act. Known acts: add, change, remove'),
        (lambda f: f["object"].update(kind="windw"),
         'object.kind: "windw" is not a known object kind. Did you mean "window"? Known '
         "object kinds in architecture and general: circle, column, door, line, opening, "
         "rectangle, regular_polygon, room, text, wall, window"),
        (lambda f: f["object"].update(name="Window 1"),
         'object.name: "Window 1" is not a usable name: use lower-case letters, digits and '
         "underscores, starting with a letter, at most 40 characters"),
        (lambda f: f["object"].update(name="origin"),
         'object.name: "origin" is reserved (the origin of the drawing) and cannot be the '
         "name of an object"),
        (lambda f: f["object"].update(name="w9"),
         'object.name: "w9" already exists (a window); adding needs a new name, or use the '
         'act "change"'),
        (lambda f: f["dimensions"]["width"].update(value=1200),
         'dimensions.width.value: 1200 does not appear in what the user said ("width 120"); '
         "a number must be copied as the user said it, in the user's unit -- never "
         "converted, never guessed"),
        (lambda f: f["dimensions"]["width"].update(value=-120),
         "dimensions.width.value: a width must be greater than zero, not -120"),
        (lambda f: f["dimensions"]["width"].update(value="120"),
         "dimensions.width.value: must be a number, not a string"),
        (lambda f: f["dimensions"]["width"].update(unit="deg"),
         'dimensions.width.unit: "deg" measures angle, but a width is a length; use one '
         "of: cm, m, mm"),
        (lambda f: f["dimensions"]["width"].update(unit="inch"),
         'dimensions.width.unit: "inch" is not a known unit. Known units for width: '
         "cm, m, mm"),
        (lambda f: f["dimensions"]["width"].pop("said"),
         'dimensions.width: field "said" is missing'),
        (lambda f: f["dimensions"]["width"].update(said="width 120 please"),
         'dimensions.width.said: "width 120 please" is not in the user\'s words; "said" '
         "must quote them exactly"),
        (lambda f: f["dimensions"].update(radius={"value": 5, "unit": "cm", "said": "120"}),
         'dimensions.radius: a window has no dimension "radius"; it takes: height, '
         "sill_height, width"),
        (lambda f: f["dimensions"].pop("width"),
         "dimensions: a window needs a width. If the user did not give one, ask: never "
         "guess a number"),
        (lambda f: f.update(properties={"thread": "M8"}),
         'properties.thread: a window has no property "thread"; it takes: none'),
        (lambda f: f.update(relations=[f["relations"][1]]),
         'relations: a window must be placed on a wall: add the relation "on"'),
        (lambda f: f["relations"][0].update(to=["plate1"]),
         "relations[0].to[0]: a window goes on a wall, not on a plate"),
        (lambda f: f["relations"][0].update(to=["wall_south"]),
         'relations[0].to[0]: there is no object called "wall_south"; known objects: '
         "origin, plate1, w9, wall_east, wall_north"),
        (lambda f: f["relations"][0].update(to=["w1"]),
         "relations[0].to[0]: an object cannot be placed relative to itself"),
        (lambda f: f["relations"][0].update(to=["wall_north", "wall_east"]),
         'relations[0].to: "on" takes 1 target, not 2'),
        (lambda f: f["relations"][0].update(side="left"),
         'relations[0].side: "on" takes no "side"'),
        (lambda f: f["relations"][0].update(relation="centered_on"),
         'relations[0].relation: "centered_on" is not a known relation. Did you mean '
         '"centred_on"? Known relations: aligned_with, along, at, between, centred_on, '
         "distributed_over, inside, next_to, offset_from, on"),
        (lambda f: f["relations"].append({"relation": "next_to", "to": ["wall_east"]}),
         'relations[2]: "next_to" needs a side'),
        (lambda f: f["relations"].append({"relation": "next_to", "to": ["wall_east"],
                                          "side": "north"}),
         'relations[2].side: "north" is not a known value of side. Known values of side: '
         "above, below, inside, left, outside, right"),
        (lambda f: f["relations"].append({"relation": "between",
                                          "to": ["wall_east", "wall_east"]}),
         'relations[2].to[1]: "wall_east" is named twice; "between" needs 2 different '
         "targets"),
        (lambda f: f.update(text="North window"), "text: a window takes no text"),
        (lambda f: f.update(reason=7), "reason: reason must be a string of at most 500 "
         "characters"),
        (lambda f: f.update(domain="mechanical"),
         'object.kind: object kind "window" belongs to architecture, not mechanical'),
    ]
    for i, (mutate, message) in enumerate(cases):
        f = base()
        mutate(f)
        refused_with(f, message)
    assert len(cases) >= 30


def test_a_number_in_another_unit_than_the_user_said_is_refused():
    f = base()
    f["dimensions"]["width"] = {"value": 1200, "unit": "mm", "said": "width 120 cm"}
    v = refused_with(f, 'dimensions.width.unit: the user said cm ("width 120 cm"), not mm; '
                        "the unit is copied as the user said it, never converted",
                     user="a window, width 120 cm")
    assert "not-said" in v.codes()


def test_numbers_as_the_user_writes_them():
    def accepted(said, value, unit="cm"):
        f = base()
        f["dimensions"]["width"] = {"value": value, "unit": unit, "said": said}
        return F.validate(f, user_text=said).ok
    assert accepted("width 120", 120)
    assert accepted("1,20 m wide", 1.2, "m")       # Italian decimal comma
    assert accepted("1.20 m wide", 1.2, "m")
    assert accepted("a 1,500 mm window", 1500, "mm")  # thousands separator
    assert accepted("dodici centimetri", 12)
    assert not accepted("width 120", 12)
    assert not accepted("width 12", 120)


def test_count_takes_no_unit_and_must_be_whole():
    f = {"form": "linework/commitment", "version": 1, "domain": "mechanical", "act": "add",
         "object": {"kind": "hole", "name": "h1"},
         "relations": [{"relation": "on", "to": ["plate1"]},
                       {"relation": "distributed_over", "to": ["plate1"],
                        "count": {"value": 4.5, "said": "4.5 holes"}}],
         "dimensions": {"diameter": {"value": 6, "unit": "mm", "said": "6 mm"}}}
    refused_with(f, "relations[1].count.value: count must be a whole number, not 4.5",
                 user="4.5 holes of 6 mm")
    f["relations"][1]["count"] = {"value": 4, "unit": "mm", "said": "4 holes"}
    refused_with(f, "relations[1].count.unit: a count is a count and takes no unit",
                 user="4 holes of 6 mm")


def test_remove_takes_only_the_object():
    f = base()
    f["act"] = "remove"
    f["object"]["name"] = "w9"
    refused_with(f, 'dimensions: removing takes only the object; drop "dimensions"')
    refused_with(f, 'relations: removing takes only the object; drop "relations"')


def test_change_must_change_something_and_must_exist():
    f = {"form": "linework/commitment", "version": 1, "domain": "architecture",
         "act": "change", "object": {"kind": "window", "name": "w9"}}
    refused_with(f, "a change must change something: give dimensions, properties, "
                    "relations or text")
    f["object"]["name"] = "w5"
    refused_with(f, 'object.name: there is no object called "w5" to change')
    f["object"] = {"kind": "door", "name": "w9"}
    refused_with(f, 'object.kind: "w9" is a window, not a door')


def test_coordinates_are_refused_wherever_they_are_smuggled():
    for word in sorted(F.COORDINATE_WORDS):
        for where in ("top", "object", "relation", "dimensions", "value"):
            f = base()
            target = {"top": f, "object": f["object"], "relation": f["relations"][0],
                      "dimensions": f["dimensions"], "value": f["dimensions"]["width"]}[where]
            target[word] = [10, 20] if where != "dimensions" else \
                {"value": 10, "unit": "cm", "said": "120"}
            v = verdict(f)
            assert not v.ok and "coordinate" in v.codes(), (word, where, v.explain())


# ----------------------------------------------------- robustness: no crashes

JUNK = [None, True, 0, -1, 1e308, float("nan"), "", "x", [], {}, [1, 2], {"a": 1},
        "M8", "origin", "\n", "a" * 300]


def mutations(n, seed=20261001):
    """Deterministic random damage to accepted forms: replace, drop, add."""
    rng = random.Random(seed)
    bases = [ex["form"] for _, _, ex in F.load_examples() if ex["expect"]["ok"]]

    def nodes(obj, path=()):
        yield path, obj
        if isinstance(obj, dict):
            for k, v in obj.items():
                for p in nodes(v, path + (k,)):
                    yield p
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                for p in nodes(v, path + (i,)):
                    yield p

    for _ in range(n):
        f = copy.deepcopy(rng.choice(bases))
        paths = [p for p, _ in nodes(f) if p]
        path = rng.choice(paths)
        parent = f
        for k in path[:-1]:
            parent = parent[k]
        op = rng.random()
        if op < 0.6:
            parent[path[-1]] = copy.deepcopy(rng.choice(JUNK))
        elif op < 0.8 and isinstance(parent, dict):
            del parent[path[-1]]
        elif isinstance(parent, dict):
            parent[rng.choice(["x", "junk", "unit", "said", "to", "side"])] = rng.choice(JUNK)
        yield f


def test_the_validator_never_crashes_and_refuses_damage():
    for f in list(mutations(1500)) + JUNK:
        v = F.validate(f, user_text="anything 1 2 3", known=KNOWN)
        assert isinstance(v.ok, bool)
        assert "internal" not in v.codes(), v.explain()
        if not v.ok:
            assert v.explain().startswith("refused -- ")
            assert all(p.message for p in v.problems)
