"""lang.form -- the commitment form: the narrow gate the model commits through.

ADR 0001: thinking is free, the hand is guided. ADR 0005: what the gate is.

The model reasons freely, then commits one decision by filling this form: fixed
fields, every word from the closed catalogue (shared/catalogue_v1.json). This
module decides whether a filled form may pass. It never repairs a form and never
guesses: a form that does not fit is refused with a readable reason for every
problem, and handed back.

    verdict = validate(form, user_text="...", known={"wall_north": "wall"})
    verdict.ok          True or False
    verdict.problems    [Problem(code, path, message), ...]
    verdict.explain()   the text handed back to the model

The two-doors rule is enforced here for the first door: every number in a form
carries "said", the user's own words, and the number must appear in them as the
user said it -- in the user's unit, never converted, never guessed. The second
door (the solver) never passes through a form at all.

Command line (from the repository root):

    python3 -m lang.form check FILE...     validate forms or worked examples
    python3 -m lang.form write             regenerate the schema and the catalogue doc
    python3 -m lang.form verify            exit 1 if the generated files are stale

Standard library only (CORE package).
"""

import difflib
import json
import os
import re
import sys

from shared import catalogue as _catalogue

FORM_TAG = "linework/commitment"
FORM_VERSION = 1

FIELDS = ("form", "version", "domain", "act", "object",
          "relations", "dimensions", "properties", "text", "reason")
REQUIRED_FIELDS = ("form", "version", "domain", "act", "object")
OBJECT_FIELDS = ("kind", "name")
VALUE_FIELDS = ("value", "unit", "said")

# Field names that would smuggle a coordinate through the gate. They are refused
# with their own message, because the right answer is not "rename the field" but
# "state a relation instead".
COORDINATE_WORDS = frozenset((
    "x", "y", "z", "xy", "point", "points", "coordinate", "coordinates",
    "position", "location", "start", "end", "start_point", "end_point",
    "centre", "center", "vertex", "vertices", "insert", "insertion"))

NAME_PATTERN = r"^[a-z][a-z0-9_]{0,39}$"
_NAME_RE = re.compile(NAME_PATTERN)
TEXT_MAX = 200
REASON_MAX = 500

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "shared", "form_schema_v%d.json" % FORM_VERSION)
CATALOGUE_DOC_PATH = os.path.join(ROOT, "docs", "CATALOGUE.md")
EXAMPLES_DIR = os.path.join(ROOT, "lang", "examples", "forms")

_CAT = None


def default_catalogue():
    global _CAT
    if _CAT is None:
        _CAT = _catalogue.load()
    return _CAT


def split_target(target):
    """("plate1", "top") for "plate1 top", ("plate1", None) for "plate1". A target
    names an object, optionally followed by one of its edges or corners (D-003)."""
    if isinstance(target, str) and " " in target:
        base, _, edge = target.partition(" ")
        return base, edge
    return target, None


def target_pattern(cat=None):
    """The JSON-schema pattern of a target: a name, optionally an edge or corner."""
    cat = cat or default_catalogue()
    edges = "|".join(sorted(cat.get("edges", {})))
    return NAME_PATTERN[:-1] + ("( (%s))?$" % edges if edges else "$")


# --------------------------------------------------------------------- verdict

class Problem(object):
    """One reason a form was refused. `code` is stable; `message` is for reading."""

    __slots__ = ("code", "path", "message")

    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message

    def __str__(self):
        return "%s: %s" % (self.path, self.message) if self.path else self.message

    def __repr__(self):
        return "Problem(%r, %r, %r)" % (self.code, self.path, self.message)


class Verdict(object):
    def __init__(self, problems):
        self.problems = list(problems)
        self.ok = not self.problems

    def codes(self):
        return [p.code for p in self.problems]

    def messages(self):
        return [str(p) for p in self.problems]

    def explain(self):
        """The text handed back to the model when the form is refused."""
        if self.ok:
            return "accepted"
        n = len(self.problems)
        head = "refused -- %d problem%s:" % (n, "" if n == 1 else "s")
        return "\n".join([head] + ["  - %s" % p for p in self.problems])


# ------------------------------------------------------------------- helpers

def _type_name(v):
    if isinstance(v, bool):
        return "true/false"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "object"
    if v is None:
        return "null"
    return type(v).__name__


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v \
        and v not in (float("inf"), float("-inf"))


def _fmt_num(v):
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _a(word):
    return ("an " if word[:1] in "aeiou" else "a ") + word


def _natural(word):
    """Sort key that puts M3 before M10."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(word))]


def _join(words):
    return ", ".join(sorted(words, key=_natural)) if words else "none"


def _unknown_word(path, word, label, plural, choices):
    msg = '"%s" is not a known %s.' % (word, label)
    if isinstance(word, str):
        close = difflib.get_close_matches(word, list(choices), n=1, cutoff=0.6)
        if close:
            msg += ' Did you mean "%s"?' % close[0]
    msg += " Known %s: %s" % (plural, _join(choices))
    return Problem("unknown-word", path, msg)


# Small whole numbers written as words are exact, so they count as said.
# English and Italian: the project is English, Marco speaks Italian (ADR 0005).
NUMBER_WORDS = dict(
    [(w, i) for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())]
    + [(w, i) for i, w in enumerate(
        "zero uno due tre quattro cinque sei sette otto nove dieci undici dodici tredici "
        "quattordici quindici sedici diciassette diciotto diciannove venti".split())]
    + [("a dozen", 12), ("una dozzina", 12)])


def _numbers_in(text):
    """Every number written in `text`, with the readings a comma allows."""
    out = []
    for tok in re.findall(r"-?\d+(?:[.,]\d+)*", text):
        if "," in tok:
            out.append(tok.replace(",", ""))            # 1,500 -> 1500
            if tok.count(",") == 1 and "." not in tok:
                out.append(tok.replace(",", "."))       # 1,5 -> 1.5
        else:
            out.append(tok)
    vals = []
    low = text.casefold()
    for word, n in NUMBER_WORDS.items():
        if re.search(r"(?<![a-z])%s(?![a-z])" % word, low):
            vals.append(float(n))
    for t in out:
        try:
            vals.append(float(t))
        except ValueError:
            pass
    return vals


# How users write the catalogue's units. Longest spellings first, so "mm" is
# not read as "m".
UNIT_SPELLINGS = (
    ("millimetres", "mm"), ("millimeters", "mm"), ("millimetre", "mm"),
    ("millimeter", "mm"), ("centimetres", "cm"), ("centimeters", "cm"),
    ("centimetre", "cm"), ("centimeter", "cm"), ("metres", "m"), ("meters", "m"),
    ("metre", "m"), ("meter", "m"), ("degrees", "deg"), ("degree", "deg"),
    ("deg", "deg"), ("mm", "mm"), ("cm", "cm"), ("m", "m"))


def _units_in(text):
    """The catalogue units written right after a number in `text`, as a set.

    "120 cm" and "5m" name a unit; "M8" (a thread) and "the m wall" do not.
    """
    found = set()
    low = text.casefold()
    for _ in re.findall(r"\d\s*\u00b0", low):
        found.add("deg")
    for spelling, unit in UNIT_SPELLINGS:
        pattern = r"(\d\s*)%s(?![a-z0-9])" % spelling
        if re.search(pattern, low):
            found.add(unit)
            low = re.sub(pattern, r"\1 ", low)
    return found


def _word_in(word, block):
    return isinstance(word, str) and word in block


def _norm(text):
    return " ".join(text.split()).casefold()


# ----------------------------------------------------------------- validator

class _Check(object):
    def __init__(self, cat, user_text, known):
        self.cat = cat
        self.user_text = user_text
        self.known = dict(known) if known is not None else None
        if self.known is not None:
            for r in cat["reserved_names"]:
                self.known[r] = r
        self.p = []

    def add(self, code, path, message):
        self.p.append(Problem(code, path, message))

    # -- fields of a dict, with the coordinate trap
    def fields(self, path, d, allowed, what):
        ok = True
        for key in d:
            here = "%s.%s" % (path, key) if path else str(key)
            if key in allowed:
                continue
            ok = False
            if isinstance(key, str) and key.lower() in COORDINATE_WORDS:
                self.add("coordinate", here,
                         'field "%s" would carry a coordinate; the form never takes '
                         "coordinates -- state a relation instead (ADR 0001)" % key)
            else:
                self.add("unknown-field", here,
                         'field "%s" is not part of %s; it has only: %s'
                         % (key, what, _join(allowed)))
        return ok

    def name(self, path, name, role):
        if not isinstance(name, str):
            self.add("type", path, "%s must be a string, not a %s" % (role, _type_name(name)))
            return False
        if not _NAME_RE.match(name):
            self.add("bad-name", path,
                     '"%s" is not a usable name: use lower-case letters, digits and '
                     "underscores, starting with a letter, at most 40 characters" % name)
            return False
        return True

    # -- a number, through the first door
    def value(self, path, v, quantity):
        q = self.cat["quantities"][quantity]
        measure = q["measure"]
        if not isinstance(v, dict):
            self.add("type", path,
                     'must be an object {"value": ..., %s"said": ...}, not a %s'
                     % ('' if measure == "count" else '"unit": ..., ', _type_name(v)))
            return
        allowed = ("value", "said") if measure == "count" else VALUE_FIELDS
        if measure == "count" and "unit" in v:
            self.add("wrong-unit", path + ".unit", "a %s is a count and takes no unit" % quantity)
            v = dict((k, x) for k, x in v.items() if k != "unit")
        self.fields(path, v, allowed, "a number")
        for f in allowed:
            if f not in v:
                self.add("missing-field", path, 'field "%s" is missing' % f)
        val = v.get("value")
        good = False
        if "value" in v:
            if not _is_number(val):
                self.add("type", path + ".value", "must be a number, not a %s" % _type_name(val))
            elif measure == "count":
                if float(val) != int(val):
                    self.add("not-whole", path + ".value",
                             "%s must be a whole number, not %s" % (quantity, _fmt_num(val)))
                elif val < q.get("min", 1):
                    self.add("too-small", path + ".value", "%s must be at least %d, not %s"
                             % (quantity, q.get("min", 1), _fmt_num(val)))
                else:
                    good = True
            elif measure == "angle":
                if not -360 < val < 360:
                    self.add("out-of-range", path + ".value",
                             "an angle must lie between -360 and 360 degrees, not %s" % _fmt_num(val))
                else:
                    good = True
            else:
                if val <= 0:
                    self.add("too-small", path + ".value", "%s must be greater than zero, not %s"
                             % (_a(quantity), _fmt_num(val)))
                else:
                    good = True
        if measure != "count" and "unit" in v:
            unit = v["unit"]
            units = [u for u, e in self.cat["units"].items() if e["measure"] == measure]
            if not isinstance(unit, str) or unit not in self.cat["units"]:
                self.p.append(_unknown_word(path + ".unit", unit, "unit",
                                            "units for %s" % quantity, units))
            elif self.cat["units"][unit]["measure"] != measure:
                self.add("wrong-unit", path + ".unit",
                         '"%s" measures %s, but %s is %s; use one of: %s'
                         % (unit, self.cat["units"][unit]["measure"], _a(quantity),
                            _a(measure), _join(units)))
        if "said" in v:
            said = v["said"]
            if not isinstance(said, str) or not said.strip():
                self.add("type", path + ".said",
                         "must be the user's own words, as a non-empty string")
            else:
                if good:
                    target = abs(float(val)) if measure == "angle" else float(val)
                    heard = [abs(n) if measure == "angle" else n for n in _numbers_in(said)]
                    if not any(abs(n - target) < 1e-9 for n in heard):
                        self.add("not-said", path + ".value",
                                 '%s does not appear in what the user said ("%s"); a number '
                                 "must be copied as the user said it, in the user's unit -- "
                                 "never converted, never guessed" % (_fmt_num(val), said))
                if measure != "count" and isinstance(v.get("unit"), str):
                    heard_units = _units_in(said)
                    if heard_units and v["unit"] not in heard_units:
                        self.add("not-said", path + ".unit",
                                 'the user said %s ("%s"), not %s; the unit is copied as '
                                 "the user said it, never converted"
                                 % (" or ".join(sorted(heard_units)), said, v["unit"]))
                if self.user_text is not None and _norm(said) not in _norm(self.user_text):
                    self.add("not-quoted", path + ".said",
                             '"%s" is not in the user\'s words; "said" must quote them exactly'
                             % said)

    # -- the whole form
    def form(self, f):
        cat = self.cat
        if not isinstance(f, dict):
            self.add("not-a-form", "",
                     "a form is a JSON object with named fields, not a %s" % _type_name(f))
            return
        self.fields("", f, FIELDS, "the form")
        for k in REQUIRED_FIELDS:
            if k not in f:
                self.add("missing-field", "", 'field "%s" is missing' % k)

        if "form" in f and f["form"] != FORM_TAG:
            self.add("not-a-form", "form", 'must be "%s"' % FORM_TAG)
        if "version" in f and f["version"] != FORM_VERSION:
            self.add("version", "version", "this is form version %s; this validator speaks "
                     "version %d" % (json.dumps(f["version"]), FORM_VERSION))
            return  # every other rule may mean something else in another version

        domain = f.get("domain")
        if "domain" in f and not _word_in(domain, cat["domains"]):
            self.p.append(_unknown_word("domain", domain, "domain", "domains", cat["domains"]))
            domain = None
        act = f.get("act")
        if "act" in f and not _word_in(act, cat["acts"]):
            self.p.append(_unknown_word("act", act, "act", "acts", cat["acts"]))
            act = None

        # the object
        kind = name = None
        obj = f.get("object")
        if "object" in f:
            if not isinstance(obj, dict):
                self.add("type", "object", 'must be an object {"kind": ..., "name": ...}, '
                         "not a %s" % _type_name(obj))
            else:
                self.fields("object", obj, OBJECT_FIELDS, "the object")
                for k in OBJECT_FIELDS:
                    if k not in obj:
                        self.add("missing-field", "object", 'field "%s" is missing' % k)
                if "kind" in obj:
                    kind = obj["kind"]
                    if not _word_in(kind, cat["objects"]):
                        doms = [d for d in (domain, "general") if d]
                        pool = [k for k, e in cat["objects"].items()
                                if not domain or e["domain"] in doms]
                        label = "object kinds in %s" % " and ".join(doms) if domain \
                            else "object kinds"
                        self.p.append(_unknown_word("object.kind", kind, "object kind",
                                                    label, pool))
                        kind = None
                    elif domain and cat["objects"][kind]["domain"] not in (domain, "general"):
                        self.add("wrong-domain", "object.kind",
                                 'object kind "%s" belongs to %s, not %s'
                                 % (kind, cat["objects"][kind]["domain"], domain))
                if "name" in obj:
                    if self.name("object.name", obj["name"], "the name"):
                        name = obj["name"]
                        if name in cat["reserved_names"]:
                            self.add("reserved-name", "object.name",
                                     '"%s" is a reserved name: it always exists, and cannot be '
                                     "the name of an object" % name)
                            name = None

        entry = cat["objects"].get(kind) if kind else None

        # the act against what already exists
        if act and name and self.known is not None:
            exists = name in self.known
            if act == "add" and exists:
                self.add("name-taken", "object.name",
                         '"%s" already exists (%s); adding needs a new name, or use the act '
                         '"change"' % (name, _a(self.known[name])))
            if act in ("change", "remove") and not exists:
                self.add("unknown-object", "object.name",
                         'there is no object called "%s" to %s' % (name, act))
            if act in ("change", "remove") and exists and kind and self.known[name] != kind:
                self.add("kind-mismatch", "object.kind",
                         '"%s" is %s, not %s' % (name, _a(self.known[name]), _a(kind)))

        if act == "remove":
            for k in ("relations", "dimensions", "properties", "text"):
                if k in f:
                    self.add("remove-takes-nothing", k,
                             'removing takes only the object; drop "%s"' % k)
            return
        if act == "change" and not any(k in f for k in
                                       ("relations", "dimensions", "properties", "text")):
            self.add("empty-change", "",
                     "a change must change something: give dimensions, properties, "
                     "relations or text")

        self.dimensions(f, kind, entry, act)
        self.properties(f, kind, entry, act)
        self.relations(f, kind, name, entry, act)
        self.text(f, kind, entry)
        if "reason" in f and (not isinstance(f["reason"], str)
                              or len(f["reason"]) > REASON_MAX):
            self.add("bad-text", "reason",
                     "reason must be a string of at most %d characters" % REASON_MAX)

    def dimensions(self, f, kind, entry, act):
        cat = self.cat
        dims = f.get("dimensions", {})
        if "dimensions" in f and not isinstance(dims, dict):
            self.add("type", "dimensions",
                     'must be an object {"width": {...}, ...}, not a %s' % _type_name(dims))
            dims = {}
        allowed = entry.get("dimensions", {}) if entry else None
        for q, v in dims.items():
            path = "dimensions.%s" % q
            if isinstance(q, str) and q.lower() in COORDINATE_WORDS and q not in cat["quantities"]:
                self.add("coordinate", path,
                         'field "%s" would carry a coordinate; the form never takes '
                         "coordinates -- state a relation instead (ADR 0001)" % q)
                continue
            if q not in cat["quantities"] and allowed is not None and not allowed:
                self.add("unknown-word", path, '"%s" is not a known quantity, and %s takes '
                         "no dimensions at all" % (q, _a(kind)))
                continue
            if q not in cat["quantities"]:
                self.p.append(_unknown_word(path, q, "quantity", "quantities",
                                            allowed if allowed is not None else cat["quantities"]))
                continue
            if allowed is not None and q not in allowed:
                self.add("not-for-kind", path, '%s has no dimension "%s"; it takes: %s'
                         % (_a(kind), q, _join(allowed)))
                continue
            self.value(path, v, q)
        if entry and act == "add":
            for q, need in sorted(allowed.items()):
                if need == "required" and q not in dims:
                    self.add("missing-dimension", "dimensions",
                             "%s needs %s. If the user did not give one, ask: never guess "
                             "a number" % (_a(kind), _a(q)))
        if entry:
            for group in entry.get("exactly_one_of", []):
                given = [q for q in group if q in dims]
                if len(given) > 1:
                    self.add("one-of", "dimensions", "give either %s for %s, not both"
                             % (" or ".join(group), _a(kind)))
                elif not given and act == "add":
                    self.add("missing-dimension", "dimensions",
                             "%s needs %s. If the user did not give one, ask: never guess "
                             "a number" % (_a(kind), " or ".join(_a(q) for q in group)))

    def properties(self, f, kind, entry, act):
        cat = self.cat
        props = f.get("properties", {})
        if "properties" in f and not isinstance(props, dict):
            self.add("type", "properties",
                     'must be an object {"thread": "M8", ...}, not a %s' % _type_name(props))
            props = {}
        allowed = entry.get("properties", {}) if entry else None
        for prop, v in props.items():
            path = "properties.%s" % prop
            if prop not in cat["properties"]:
                self.p.append(_unknown_word(path, prop, "property", "properties",
                                            allowed if allowed is not None else cat["properties"]))
                continue
            if allowed is not None and prop not in allowed:
                self.add("not-for-kind", path, '%s has no property "%s"; it takes: %s'
                         % (_a(kind), prop, _join(allowed)))
                continue
            values = cat["properties"][prop]["values"]
            if not isinstance(v, str) or v not in values:
                self.p.append(_unknown_word(path, v, "value of %s" % prop,
                                            "values of %s" % prop, values))
        if entry and act == "add":
            for prop, need in sorted(allowed.items()):
                if need == "required" and prop not in props:
                    self.add("missing-property", "properties",
                             "%s needs %s. If the user did not say, ask: never guess"
                             % (_a(kind), _a(prop)))

    def relations(self, f, kind, name, entry, act):
        cat = self.cat
        rels = f.get("relations", [])
        if "relations" in f and not isinstance(rels, list):
            self.add("type", "relations",
                     'must be a list of relations, not a %s' % _type_name(rels))
            rels = []
        used = []
        for i, r in enumerate(rels):
            path = "relations[%d]" % i
            if not isinstance(r, dict):
                self.add("type", path, 'must be an object {"relation": ..., "to": [...]}, '
                         "not a %s" % _type_name(r))
                continue
            if "relation" not in r:
                self.add("missing-field", path, 'field "relation" is missing')
                continue
            word = r["relation"]
            if not _word_in(word, cat["relations"]):
                self.p.append(_unknown_word(path + ".relation", word, "relation",
                                            "relations", cat["relations"]))
                continue
            used.append(word)
            rel = cat["relations"][word]
            params = rel.get("params", {})
            allowed = ("relation", "to") + tuple(params)
            for key in r:
                if key in allowed:
                    continue
                here = "%s.%s" % (path, key)
                if isinstance(key, str) and key.lower() in COORDINATE_WORDS:
                    self.add("coordinate", here,
                             'field "%s" would carry a coordinate; the form never takes '
                             "coordinates -- state a relation instead (ADR 0001)" % key)
                elif params:
                    self.add("not-for-relation", here, '"%s" takes only: %s'
                             % (word, _join(params)))
                else:
                    self.add("not-for-relation", here, '"%s" takes no "%s"' % (word, key))
            for param, need in sorted(params.items()):
                if need == "required" and param not in r:
                    self.add("missing-parameter", path, '"%s" needs %s' % (word, _a(param)))
            for param in params:
                if param not in r:
                    continue
                spec = cat["parameters"][param]
                if spec["type"] == "word":
                    if not isinstance(r[param], str) or r[param] not in spec["values"]:
                        self.p.append(_unknown_word("%s.%s" % (path, param), r[param],
                                                    "value of %s" % param,
                                                    "values of %s" % param, spec["values"]))
                else:
                    self.value("%s.%s" % (path, param), r[param], spec["quantity"])
            # targets
            if "to" not in r:
                self.add("missing-field", path, 'field "to" is missing')
                continue
            to = r["to"]
            if not isinstance(to, list):
                self.add("type", path + ".to",
                         "must be a list of object names, not a %s" % _type_name(to))
                continue
            if len(to) != rel["targets"]:
                self.add("arity", path + ".to", '"%s" takes %d target%s, not %d'
                         % (word, rel["targets"], "" if rel["targets"] == 1 else "s", len(to)))
            for j, t in enumerate(to):
                tp = "%s.to[%d]" % (path, j)
                if isinstance(t, str) and " " in t:
                    # a target may name an edge or a corner: "plate1 top" (D-003)
                    base, _, edge = t.partition(" ")
                    if edge not in cat.get("edges", {}):
                        self.p.append(_unknown_word(tp, edge, "edge or corner", "edges",
                                                    cat.get("edges", {})))
                        continue
                    if not rel.get("edge_targets"):
                        self.add("no-edge", tp, '"%s" measures from the whole object, not from '
                                 'an edge or a corner: write "%s" alone'
                                 % (word.replace("_", " "), base))
                        continue
                    if base in cat["reserved_names"]:
                        self.add("no-edge", tp, '"%s" is a point; it has no %s'
                                 % (base, edge.replace("_", "-")))
                        continue
                    t = base
                if not self.name(tp, t, "a target"):
                    continue
                if t in [split_target(x)[0] for x in to[:j]]:
                    self.add("same-target", tp,
                             '"%s" is named twice; "%s" needs %d different targets'
                             % (t, word, rel["targets"]))
                    continue
                if name and t == name:
                    self.add("self", tp, "an object cannot be placed relative to itself")
                    continue
                if self.known is not None and t not in self.known:
                    self.add("unknown-target", tp,
                             'there is no object called "%s"; known objects: %s'
                             % (t, _join(self.known)))
                    continue
                if (word == "on" and entry and entry.get("host") and self.known is not None
                        and self.known[t] not in entry["host"]):
                    self.add("wrong-host", tp, "%s goes on %s, not on %s"
                             % (_a(kind), " or ".join(_a(h) for h in entry["host"]),
                                _a(self.known[t])))
        if entry and act == "add":
            needs = entry.get("needs_relation", [])
            if needs and not any(n in used for n in needs):
                if entry.get("host"):
                    self.add("needs-relation", "relations",
                             '%s must be placed on %s: add the relation "on"'
                             % (_a(kind), " or ".join(_a(h) for h in entry["host"])))
                else:
                    self.add("needs-relation", "relations", "%s needs the relation %s"
                             % (_a(kind), " or ".join('"%s"' % n for n in needs)))

    def text(self, f, kind, entry):
        if "text" not in f:
            return
        if entry and not entry.get("takes_text"):
            self.add("no-text", "text", "%s takes no text" % _a(kind))
            return
        t = f["text"]
        if (not isinstance(t, str) or not t.strip() or len(t) > TEXT_MAX
                or any(ord(c) < 32 for c in t)):
            self.add("bad-text", "text",
                     "text must be one line of at most %d characters" % TEXT_MAX)


def validate(form, user_text=None, known=None, catalogue=None):
    """Validate one filled form. Never raises; every problem is in the verdict.

    user_text  the user's words for this decision; when given, every "said"
               must quote them exactly.
    known      {name: kind} of the objects already in the drawing; when given,
               names, targets and hosts are checked against it.
    """
    check = _Check(catalogue or default_catalogue(), user_text, known)
    try:
        check.form(form)
    except Exception as exc:  # a validator that crashes lets nothing through
        check.add("internal", "", "the validator could not read this form (%s: %s); "
                  "it is refused" % (type(exc).__name__, exc))
    return Verdict(check.p)


# ------------------------------------------------------- the published schema

def _value_schema(cat, quantity):
    measure = cat["quantities"][quantity]["measure"]
    if measure == "count":
        return {"type": "object", "additionalProperties": False,
                "required": ["value", "said"],
                "properties": {"value": {"type": "integer",
                                         "minimum": cat["quantities"][quantity].get("min", 1)},
                               "said": {"type": "string", "minLength": 1}}}
    units = sorted(u for u, e in cat["units"].items() if e["measure"] == measure)
    value = {"type": "number"}
    if measure == "angle":
        value.update({"exclusiveMinimum": -360, "exclusiveMaximum": 360})
    else:
        value["exclusiveMinimum"] = 0
    return {"type": "object", "additionalProperties": False,
            "required": ["value", "unit", "said"],
            "properties": {"value": value, "unit": {"enum": units},
                           "said": {"type": "string", "minLength": 1}}}


def build_schema(cat=None):
    """The JSON Schema (draft 2020-12) of the form, generated from the catalogue.

    It holds the shape and every closed list. The rules that depend on the
    object kind, on what the user said and on what the drawing already holds
    are enforced by lang.form.validate, which is the authority; a form that
    passes this schema may still be refused there, never the other way round.
    """
    cat = cat or default_catalogue()
    relations = []
    for word in sorted(cat["relations"]):
        rel = cat["relations"][word]
        props = {"relation": {"const": word},
                 "to": {"type": "array", "minItems": rel["targets"], "maxItems": rel["targets"],
                        "items": {"type": "string",
                                  "pattern": (target_pattern(cat) if rel.get("edge_targets")
                                              else NAME_PATTERN)}}}
        required = ["relation", "to"]
        for param, need in sorted(rel.get("params", {}).items()):
            spec = cat["parameters"][param]
            props[param] = ({"enum": sorted(spec["values"])} if spec["type"] == "word"
                            else _value_schema(cat, spec["quantity"]))
            if need == "required":
                required.append(param)
        relations.append({"type": "object", "additionalProperties": False,
                          "required": required, "properties": props,
                          "description": rel["meaning"]})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/nasdomak/linework/shared/form_schema_v%d.json" % FORM_VERSION,
        "title": "linework commitment form, version %d" % FORM_VERSION,
        "description": ("GENERATED by 'python3 -m lang.form write' from "
                        "shared/catalogue_v%d.json -- do not edit by hand. One decision, "
                        "committed through the narrow gate of ADR 0001 and ADR 0005. "
                        "Per-kind rules, the two-doors check on numbers and the checks "
                        "against the drawing are enforced by lang/form.py."
                        % _catalogue.CATALOGUE_VERSION),
        "type": "object",
        "additionalProperties": False,
        "required": list(REQUIRED_FIELDS),
        "properties": {
            "form": {"const": FORM_TAG},
            "version": {"const": FORM_VERSION},
            "domain": {"enum": sorted(cat["domains"])},
            "act": {"enum": sorted(cat["acts"])},
            "object": {"type": "object", "additionalProperties": False,
                       "required": list(OBJECT_FIELDS),
                       "properties": {"kind": {"enum": sorted(cat["objects"])},
                                      "name": {"type": "string", "pattern": NAME_PATTERN,
                                               "not": {"enum": sorted(cat["reserved_names"])}}}},
            "relations": {"type": "array", "items": {"oneOf": relations}},
            "dimensions": {"type": "object", "additionalProperties": False,
                           "properties": dict((q, _value_schema(cat, q))
                                              for q in sorted(cat["quantities"]))},
            "properties": {"type": "object", "additionalProperties": False,
                           "properties": dict((p, {"enum": sorted(e["values"])})
                                              for p, e in sorted(cat["properties"].items()))},
            "text": {"type": "string", "minLength": 1, "maxLength": TEXT_MAX},
            "reason": {"type": "string", "maxLength": REASON_MAX},
        },
    }


def schema_text(cat=None):
    return json.dumps(build_schema(cat), indent=2, sort_keys=True, ensure_ascii=True) + "\n"


# ------------------------------------------------------ the readable catalogue

def catalogue_text(cat=None):
    """docs/CATALOGUE.md: every word of the vocabulary, one entry each."""
    cat = cat or default_catalogue()
    L = ["# The catalogue -- every word the model may commit",
         "",
         "> GENERATED by `python3 -m lang.form write` from `shared/catalogue_v%d.json`."
         % cat["version"],
         "> Do not edit this file: edit the catalogue and regenerate. CI fails if they disagree.",
         "",
         "The model thinks freely, then commits one decision by filling the form of",
         "[ADR 0005](adr/0005-the-commitment-form.md). Every value in the form is one",
         "of the words below; anything else is refused with a reason. **No field takes",
         "a coordinate.** Every number carries the user's own words, and must appear in",
         "them, in the user's unit.",
         ""]

    def table(title, block, extra=None):
        L.extend(["## %s" % title, ""])
        head = "| Word | %sMeaning |" % ("%s | " % extra[0] if extra else "")
        L.extend([head, "|---|%s---|" % ("---|" if extra else "")])
        for w in sorted(block):
            e = block[w]
            mid = "%s | " % extra[1](e) if extra else ""
            L.append("| `%s` | %s%s |" % (w, mid, e["meaning"]))
        L.append("")

    table("Domains", cat["domains"])
    table("Acts", cat["acts"])
    table("Units", cat["units"], ("Measures", lambda e: e["measure"]))
    table("Quantities (dimensions)", cat["quantities"], ("Measure", lambda e: e["measure"]))

    L.extend(["## The sheet and reference points", "",
              cat["sheet"]["meaning"], ""])
    for w in sorted(cat["reference_points"]):
        L.append("- **%s** -- %s" % (w, cat["reference_points"][w]["meaning"]))
    L.append("")
    L.extend(["## Relations", "",
              "Every relation names its reference frame: what of the target it measures "
              "from, and which part of the object's position it fixes -- *firmly*, or *by "
              "default* when nothing else fixes that part. The rules are in "
              "[SCRIPT.md](SCRIPT.md), \"Where the first object goes\".", "",
              "| Relation | Targets | Parameters | Meaning | Reference frame | Fixes |",
              "|---|---|---|---|---|---|"])
    for w in sorted(cat["relations"]):
        e = cat["relations"][w]
        params = ", ".join("`%s` (%s)" % (p, n) for p, n in sorted(e["params"].items())) or "--"
        fixes = ", ".join("%s %s" % (k, v) for k, v in sorted(e["fixes"].items())) or "nothing"
        L.append("| `%s` | %d | %s | %s | %s | %s |" % (w, e["targets"], params, e["meaning"],
                                                       e["frame"], fixes))
    L.append("")
    L.extend(["### Relation parameters", ""])
    for p in sorted(cat["parameters"]):
        e = cat["parameters"][p]
        if e["type"] == "word":
            vals = "; ".join("`%s` -- %s" % (v, ve["meaning"]) for v, ve in sorted(e["values"].items()))
            L.append("- **`%s`** -- %s Values: %s" % (p, e["meaning"], vals))
        else:
            L.append("- **`%s`** -- %s A number (quantity `%s`)." % (p, e["meaning"], e["quantity"]))
    L.append("")
    if cat.get("edges"):
        takers = ", ".join("`%s`" % w for w in sorted(cat["relations"])
                           if cat["relations"][w].get("edge_targets"))
        L.extend(["### Edges and corners of a target", "",
                  "A target may be followed by one of these words, and the relation then "
                  "measures from that edge or corner instead of from the whole object: "
                  "`offset from plate1 top by 15 mm on side below`. Only %s take them; a "
                  "reserved name such as `origin` is a point and has none." % takers, ""])
        for w in sorted(cat["edges"]):
            L.append("- **`%s`** -- %s" % (w, cat["edges"][w]["meaning"]))
        L.append("")
    table("Reserved names", cat["reserved_names"])

    L.extend(["## Properties", ""])
    for p in sorted(cat["properties"]):
        e = cat["properties"][p]
        L.append("- **`%s`** -- %s" % (p, e["meaning"]))
        for v in sorted(e["values"], key=lambda x: (len(x), x)):
            L.append("  - `%s` -- %s" % (v, e["values"][v]["meaning"]))
    L.append("")

    L.extend(["## Object kinds", "",
              "Dimensions marked *memory* may be left out: the solver takes them from",
              "the drawing standard in memory (ADR 0002). *Required* ones must come from",
              "the user; if they did not give one, the model asks.", ""])
    for d in sorted(cat["domains"]):
        kinds = sorted(k for k, e in cat["objects"].items() if e["domain"] == d)
        if not kinds:
            continue
        L.extend(["### %s" % d, "", "| Kind | Dimensions | Properties | Placement | Meaning |",
                  "|---|---|---|---|---|"])
        for k in kinds:
            e = cat["objects"][k]
            dims = ", ".join("`%s` %s" % (q, n) for q, n in sorted(e.get("dimensions", {}).items()))
            for g in e.get("exactly_one_of", []):
                dims += "; exactly one of %s" % " / ".join("`%s`" % q for q in g)
            props = ", ".join("`%s` %s" % (p, n) for p, n in sorted(e.get("properties", {}).items()))
            place = []
            if e.get("needs_relation"):
                place.append("needs %s" % " or ".join("`%s`" % r for r in e["needs_relation"]))
            if e.get("host"):
                place.append("on %s" % " or ".join("`%s`" % h for h in e["host"]))
            if e.get("takes_text"):
                place.append("takes text")
            if e.get("placed_by"):
                place.append("placed by its %s" % e["placed_by"])
            L.append("| `%s` | %s | %s | %s | %s |" % (k, dims or "--", props or "--",
                                                     "; ".join(place) or "--", e["meaning"]))
        L.append("")
    return "\n".join(L)


GENERATED = ((SCHEMA_PATH, schema_text), (CATALOGUE_DOC_PATH, catalogue_text))


def stale_files(cat=None):
    """The generated files whose content differs from what the catalogue gives."""
    out = []
    for path, make in GENERATED:
        want = make(cat)
        try:
            with open(path, "r", encoding="utf-8", newline="") as fh:
                have = fh.read()
        except OSError:
            have = None
        if have != want:
            out.append(path)
    return out


# ------------------------------------------------------------ worked examples

def check_example(example, catalogue=None):
    """A worked example: {"title", "user_text", "known", "form", "expect": {...}}.

    Returns a list of strings: empty when the example behaves as it says.
    expect = {"ok": true} or {"ok": false, "codes": [...], "messages": [...]}
    where every listed message must appear, word for word, in the refusal.
    """
    v = validate(example["form"], user_text=example.get("user_text"),
                 known=example.get("known"), catalogue=catalogue)
    exp = example["expect"]
    errs = []
    if v.ok != exp["ok"]:
        errs.append("expected %s, got %s" % ("acceptance" if exp["ok"] else "refusal",
                                              v.explain()))
        return errs
    if not exp["ok"]:
        if "codes" in exp and sorted(v.codes()) != sorted(exp["codes"]):
            errs.append("expected codes %s, got %s" % (sorted(exp["codes"]), sorted(v.codes())))
        for m in exp.get("messages", []):
            if m not in v.messages():
                errs.append("missing refusal %r; got %s" % (m, v.messages()))
    return errs


def load_examples(directory=EXAMPLES_DIR):
    out = []
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            with open(os.path.join(directory, name), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for i, ex in enumerate(data["examples"]):
                out.append(("%s#%d" % (name, i + 1), data["domain"], ex))
    return out


# ------------------------------------------------------------- command line

def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "write":
        for path, make in GENERATED:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(make())
            print("wrote %s" % os.path.relpath(path, ROOT))
        return 0
    if cmd == "verify":
        stale = stale_files()
        for path in stale:
            print("STALE %s -- run: python3 -m lang.form write" % os.path.relpath(path, ROOT))
        if not stale:
            print("generated files agree with the catalogue")
        return 1 if stale else 0
    if cmd == "check":
        bad = 0
        for path in rest:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "examples" in data:
                for i, ex in enumerate(data["examples"]):
                    errs = check_example(ex)
                    bad += bool(errs)
                    print("%s %s#%d %s" % ("FAIL" if errs else "ok  ", path, i + 1, ex["title"]))
                    for e in errs:
                        print("       %s" % e)
            else:
                v = validate(data)
                bad += not v.ok
                print("%s: %s" % (path, v.explain()))
        return 1 if bad else 0
    print("unknown command %r; try --help" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
