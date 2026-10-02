"""geometry.placement -- exact positions from anchoring decisions (P1-T04, ADR 0008).

The second door of the two-doors rule: numbers computed, never guessed. This
module receives, for every object, its size and -- for each sheet axis -- the
one relation the grammar chose to fix it (lang.anchoring decides which; this
module only does the arithmetic). It returns every object's extent on the sheet
as exact fractions of a millimetre, and a canonical text of the result: the same
input gives the same bytes, every time, on every machine.

Covered here: at, centred on, next to, offset from, aligned with, and the inside
check, for rectangular ("box") and round objects. The relations that need real
geometry -- along, between, distributed over -- are placed by the solver of
phase 2; asked for one, this module raises NotPlacedYet rather than guess.

Standard library only (CORE package). Imports nothing from lang/: it works on
plain records.
"""

from fractions import Fraction

UNIT_MM = {"mm": Fraction(1), "cm": Fraction(10), "m": Fraction(1000)}

SUPPORTED = ("at", "centred_on", "next_to", "offset_from", "aligned_with")


class PlacementError(Exception):
    def __init__(self, name, message):
        self.name, self.message = name, message
        Exception.__init__(self, '"%s": %s' % (name, message))


class NotPlacedYet(PlacementError):
    """A relation this module does not compute; the phase-2 solver will."""


def to_mm(value, unit):
    """An exact length in millimetres. 6.5 cm is exactly 65 mm, never 64.99999."""
    return Fraction(str(value)) * UNIT_MM[unit]


class Extent(object):
    """Where an object lies on the sheet: [xmin, xmax] x [ymin, ymax], in mm."""

    __slots__ = ("lo", "hi", "shape")

    def __init__(self, xmin, ymin, xmax, ymax, shape):
        self.lo = {"x": xmin, "y": ymin}
        self.hi = {"x": xmax, "y": ymax}
        self.shape = shape

    def centre(self, axis):
        return (self.lo[axis] + self.hi[axis]) / 2

    def ref(self, axis):
        """The reference point: lower-left for a box, the centre otherwise."""
        return self.lo[axis] if self.shape == "box" else self.centre(axis)


ORIGIN = Extent(Fraction(0), Fraction(0), Fraction(0), Fraction(0), "point")


def _interval(obj, axis, rel, placed):
    """The object's [lo, hi] on `axis`, from the one relation that fixes it."""
    word = rel["relation"]
    if word not in SUPPORTED:
        raise NotPlacedYet(obj["name"], '"%s" is placed by the solver of phase 2, not yet '
                           "here" % word.replace("_", " "))
    target = placed[rel["to"][0]]
    size = obj["size"][axis]
    half = size / 2
    if word == "at":
        r = target.ref(axis)
        return (r, r + size) if obj["shape"] == "box" else (r - half, r + half)
    if word in ("centred_on", "aligned_with"):
        c = target.centre(axis)
        return c - half, c + half
    # next_to, offset_from
    gap = rel.get("distance", Fraction(0))
    side = rel["side"]
    across = "x" if side in ("left", "right") else "y"
    if axis == across:
        if side in ("right", "above"):
            return target.hi[axis] + gap, target.hi[axis] + gap + size
        return target.lo[axis] - gap - size, target.lo[axis] - gap
    # along the edge, by default: flush at the left or at the bottom
    return target.lo[axis], target.lo[axis] + size


def place(objects):
    """objects: in order, each {"name", "kind", "shape": "box"|"round",
    "size": {"x": Fraction, "y": Fraction}, "axes": {"x": rel, "y": rel},
    "inside": [names]}, where a rel is {"relation", "to": [...], and its
    parameters with distances already in mm}. Returns {name: Extent}."""
    placed = {"origin": ORIGIN}
    for obj in objects:
        if obj.get("shape") not in ("box", "round"):
            raise NotPlacedYet(obj["name"], "its size is not known here, so it is placed by "
                               "the solver of phase 2")
        lo, hi = {}, {}
        for axis in ("x", "y"):
            lo[axis], hi[axis] = _interval(obj, axis, obj["axes"][axis], placed)
        e = Extent(lo["x"], lo["y"], hi["x"], hi["y"], obj["shape"])
        for host in obj.get("inside", []):
            h = placed[host]
            if not all(h.lo[a] <= e.lo[a] and e.hi[a] <= h.hi[a] for a in ("x", "y")):
                raise PlacementError(obj["name"], 'it is not inside "%s": the relations that '
                                     "place it put it partly outside" % host)
        placed[obj["name"]] = e
    del placed["origin"]
    return placed


def fmt(q):
    """A fraction as an exact decimal, or as n/d when it has no finite decimal."""
    q = Fraction(q)
    if q.denominator == 1:
        return str(q.numerator)
    d = q.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    if d != 1:
        return "%d/%d" % (q.numerator, q.denominator)
    sign = "-" if q < 0 else ""
    q = abs(q)
    whole = q.numerator // q.denominator
    rest = q - whole
    digits = ""
    while rest:
        rest *= 10
        digits += str(rest.numerator // rest.denominator)
        rest -= rest.numerator // rest.denominator
    return "%s%d.%s" % (sign, whole, digits)


def text(objects, placed):
    """The canonical text of a placement: one line per object, in order, mm."""
    lines = ["# linework placement 1 -- millimetres, x right, y up, from origin",
             "# name kind xmin ymin xmax ymax"]
    for obj in objects:
        e = placed[obj["name"]]
        lines.append("%s %s %s %s %s %s" % (obj["name"], obj["kind"], fmt(e.lo["x"]),
                                            fmt(e.lo["y"]), fmt(e.hi["x"]), fmt(e.hi["y"])))
    return "\n".join(lines) + "\n"
