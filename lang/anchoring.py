"""lang.anchoring -- the blank page, answered by the grammar (P1-T04, ADR 0008).

In 3D you grow from the origin; in 2D "a 5 x 4 room" has no obvious where, and
"next to it" has no obvious side. This module answers both from the script
alone, never at run time and never by guessing:

- The first object goes `at origin`. Every other object is placed by relations
  to objects that exist.
- Every relation names its reference frame (shared/catalogue_v1.json, "frame"
  and "fixes"): what of the target it measures from, and which part of the
  object's position it fixes -- firmly, or by default when nothing else does.
- For each object and each sheet axis (left-right, up-down) exactly one
  relation must govern: one firm one, or else exactly one default. None is
  "not determined"; two firm ones is "fixed twice"; two defaults and no firm
  one is "suggested twice". All three are refused with the line and the words,
  never resolved by a guess.

`analyse(script)` returns the anchoring plan or raises the first problem;
`problems(script)` returns them all; `place(script)` hands the plan to
geometry.placement and returns its canonical text -- one determinate drawing,
byte for byte, from a script that holds no coordinate.

Standard library only (CORE package).
"""

import re
from fractions import Fraction

from geometry import placement as _placement
from lang import form as _form
from lang import script as _script

AXIS_WORDS = {"x": "left-right", "y": "up-down"}
SIDE_AXES = {"left": ("x", "y"), "right": ("x", "y"), "above": ("y", "x"),
             "below": ("y", "x")}           # side -> (across, along)
OTHER = {"x": "y", "y": "x"}


class AnchoringError(_script.ScriptError):
    """A script whose drawing is not one determinate drawing."""


def _bases(rel):
    """The objects a relation clause names, without any edge or corner (D-003)."""
    return [_form.split_target(t)[0] for t in rel.targets]


class _Object(object):
    def __init__(self, st):
        self.name, self.kind, self.line = st.name, st.kind, st.line
        self.dims, self.props, self.relations = {}, {}, []
        self.text = None
        self.update(st)

    def update(self, st):
        rels = [c for c in st.clauses if c.kind == "relation"]
        if rels or st.act == "add":
            self.relations = rels
            self.line = st.line
        for c in st.clauses:
            if c.kind == "dimension":
                self.dims[c.word] = (c.value, c.unit)
            elif c.kind == "property":
                self.props[c.word] = c.value
            elif c.kind == "text":
                self.text = c.value

    def mm(self, quantity):
        v = self.dims.get(quantity)
        return _placement.to_mm(*v) if v and v[1] in _placement.UNIT_MM else None

    def shape_and_size(self):
        """("box"|"round", {"x": mm, "y": mm}) when the script gives the size. A
        free shape is placed by its local origin, as a point (ADR 0009)."""
        if self.kind == "free":
            return "point", {"x": Fraction(0), "y": Fraction(0)}
        d = self.mm("diameter")
        if d is None and self.mm("radius") is not None:
            d = 2 * self.mm("radius")
        if d is None and "thread" in self.props:
            d = Fraction(re.sub(r"\D", "", self.props["thread"]))
        if d is not None:
            return "round", {"x": d, "y": d}
        w = self.mm("width")
        h = self.mm("height") if self.mm("height") is not None else self.mm("length")
        if w is not None and h is None and self.kind == "column":
            h = w
        if w is not None and h is not None:
            return "box", {"x": w, "y": h}
        return None, None

    def orientation(self, objects):
        """horizontal, vertical or None: the direction of the object's long axis."""
        shape, size = self.shape_and_size()
        if shape == "box" and size["x"] != size["y"]:
            return "horizontal" if size["x"] > size["y"] else "vertical"
        for r in self.relations:
            if r.word == "along":
                side = r.params.get("side")
                if side:
                    return "horizontal" if side in ("above", "below") else "vertical"
                t = objects.get(r.targets[0])
                return t.orientation(objects) if t else None
        return None


def _state(script):
    """Replay the drawable statements: the objects that exist at the end, in the
    order they were added, and the problems found on the way."""
    objects, order, problems = {}, [], []
    for st in script.drawable():
        if st.act == "add":
            objects[st.name] = _Object(st)
            order.append(st.name)
        elif st.act == "change":
            objects[st.name].update(st)
        elif st.act == "remove":
            del objects[st.name]
            order.remove(st.name)
            for name in order:
                o = objects[name]
                if any(st.name in _bases(r) for r in o.relations):
                    problems.append(AnchoringError(
                        st.line, 'removing "%s" leaves "%s" (line %d) without the object it is '
                        "placed by; place it relative to something else first"
                        % (st.name, name, o.line)))
    return objects, order, problems


def _axes_of(obj, rel, key, objects):
    """The sheet axes a relation's fix key stands for, or a problem text."""
    if key in ("x", "y"):
        return [key], None
    if key == "axis":
        return ["y" if rel.params.get("axis") == "horizontal" else "x"], None
    side = rel.params.get("side")
    if side:
        across, along = SIDE_AXES[side]
    else:
        target = objects.get(rel.targets[0])
        orient = target.orientation(objects) if target else None
        if orient is None:
            return None, ('"%s" needs the direction of "%s", which is not known: it is square, '
                          "or its size is not given in the script" % (rel, rel.targets[0]))
        along, across = ("x", "y") if orient == "horizontal" else ("y", "x")
    return [across if key == "across" else along], None


def _plan_one(obj, objects, cat):
    """{"x": clause, "y": clause} or "corner"; raises AnchoringError."""
    entry = cat["objects"].get(obj.kind, {})        # "free" is not a catalogue kind
    if entry.get("placed_by") == "corner":
        return "corner"
    firm, default = {"x": [], "y": []}, {"x": [], "y": []}
    for rel in obj.relations:
        for key, strength in sorted(cat["relations"][rel.word]["fixes"].items()):
            axes, problem = _axes_of(obj, rel, key, objects)
            if problem:
                raise AnchoringError(obj.line, problem)
            for a in axes:
                (firm if strength == "firm" else default)[a].append(rel)
    chosen = {}
    missing = []
    for a in ("x", "y"):
        if len(firm[a]) > 1:
            raise AnchoringError(obj.line, 'the %s place of "%s" is fixed twice, by "%s" and by '
                                 '"%s"; keep one' % (AXIS_WORDS[a], obj.name, firm[a][0],
                                                     firm[a][1]))
        if firm[a]:
            chosen[a] = firm[a][0]
        elif len(default[a]) > 1:
            raise AnchoringError(obj.line, 'the %s place of "%s" is suggested twice, by "%s" '
                                 'and by "%s"; fix it with one relation'
                                 % (AXIS_WORDS[a], obj.name, default[a][0], default[a][1]))
        elif default[a]:
            chosen[a] = default[a][0]
        else:
            missing.append(a)
    if len(missing) == 2:
        raise AnchoringError(obj.line, '"%s" has no place: say where it goes relative to '
                             "something that exists (the first object goes at origin)"
                             % obj.name)
    if missing:
        a = missing[0]
        hint = ("aligned with ... on axis vertical" if a == "x"
                else "aligned with ... on axis horizontal")
        raise AnchoringError(obj.line, 'the %s place of "%s" is not determined; add a relation '
                             "that fixes it, such as centred on, %s, or offset from ... on "
                             "side %s" % (AXIS_WORDS[a], obj.name, hint,
                                          "left" if a == "x" else "below"))
    return chosen


def problems(script, catalogue=None):
    """Every reason the script is not one determinate drawing, in line order."""
    cat = catalogue or _form.default_catalogue()
    invalid = _script.check(script)
    if invalid:
        return invalid          # the anchoring of an invalid script means nothing
    objects, order, found = _state(script)
    undetermined = set()
    for name in order:
        obj = objects[name]
        bad = [t for r in obj.relations for t in _bases(r) if t in undetermined]
        try:
            _plan_one(obj, objects, cat)
        except AnchoringError as exc:
            found.append(exc)
            undetermined.add(name)
            continue
        if bad:
            found.append(AnchoringError(obj.line, '"%s" is placed by "%s", whose own place is '
                                        "not determined" % (name, bad[0])))
            undetermined.add(name)
    found.sort(key=lambda e: e.line)
    return found


def analyse(script, catalogue=None):
    """The anchoring plan: [(object name, {"x": clause, "y": clause} | "corner")].
    Raises the first problem (an OpenChoiceError if a choice is open)."""
    found = problems(script, catalogue)
    if found:
        raise found[0]
    cat = catalogue or _form.default_catalogue()
    objects, order, _ = _state(script)
    return [(name, _plan_one(objects[name], objects, cat)) for name in order]


def _rel_record(clause):
    rec = {"relation": clause.word, "to": list(clause.targets)}
    for p, v in clause.params.items():
        rec[p] = _placement.to_mm(*v) if p == "distance" else v
    return rec


def place(script, catalogue=None):
    """One determinate drawing: the canonical placement text of the script.
    Raises AnchoringError, or geometry.placement.NotPlacedYet for a relation the
    phase-2 solver will compute."""
    cat = catalogue or _form.default_catalogue()
    plan = analyse(script, cat)
    objects, _, _ = _state(script)
    records = []
    free = dict((f.name, f.source) for f in script.free())
    for name, axes in plan:
        obj = objects[name]
        if axes == "corner":
            raise _placement.NotPlacedYet(name, "corner features are placed by the solver of "
                                          "phase 2")
        shape, size = obj.shape_and_size()
        records.append({"name": name, "kind": obj.kind, "shape": shape, "size": size,
                        "axes": dict((a, _rel_record(c)) for a, c in axes.items()),
                        "inside": [r.targets[0] for r in obj.relations
                                   if r.word == "inside"],
                        "free": free.get(name)})
    return _placement.text(records, _placement.place(records))
