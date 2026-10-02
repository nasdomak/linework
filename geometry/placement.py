"""geometry.placement -- exact positions from anchoring decisions (P1-T04, ADR 0008).

The second door of the two-doors rule: numbers computed, never guessed. This
module receives, for every object, its size and -- for each sheet axis -- the
one relation the grammar chose to fix it (lang.anchoring decides which; this
module only does the arithmetic). It returns every object's extent on the sheet
as exact fractions of a millimetre, and a canonical text of the result: the same
input gives the same bytes, every time, on every machine.

Covered here: at, centred on, next to, offset from, aligned with, along,
between, distributed over, the corner features (fillet, chamfer) and the inside
check, for rectangular ("box"), round, point and straight ("strip": walls,
roads, pipes, wires) objects (P1-T04, P2-T05, ADR 0014). A size the script does
not give is never invented: SizeNotKnown names where it will come from.

Standard library only (CORE package). Imports nothing from lang/: it works on
plain records.
"""

from fractions import Fraction

UNIT_MM = {"mm": Fraction(1), "cm": Fraction(10), "m": Fraction(1000)}

SUPPORTED = ("at", "centred_on", "next_to", "offset_from", "aligned_with", "along",
             "distributed_over")


class PlacementError(Exception):
    def __init__(self, name, message):
        self.name, self.message = name, message
        Exception.__init__(self, '"%s": %s' % (name, message))


class NotPlacedYet(PlacementError):
    """Something this module does not compute yet; the message says what."""


class SizeNotKnown(NotPlacedYet):
    """The object's size is not in the script; the message says where it will
    come from (the drawing standard in memory, phase 4)."""


def to_mm(value, unit):
    """An exact length in millimetres. 6.5 cm is exactly 65 mm, never 64.99999."""
    return Fraction(str(value)) * UNIT_MM[unit]


class Extent(object):
    """Where an object lies on the sheet: [xmin, xmax] x [ymin, ymax], in mm."""

    __slots__ = ("lo", "hi", "shape", "start", "end", "width", "parts")

    def __init__(self, xmin, ymin, xmax, ymax, shape, start=None, end=None, width=None):
        self.lo = {"x": xmin, "y": ymin}
        self.hi = {"x": xmax, "y": ymax}
        self.shape = shape
        self.start, self.end, self.width = start, end, width   # strips: the axis
        self.parts = None                   # copies and corner features: [(label, Extent)]

    def centre(self, axis):
        return (self.lo[axis] + self.hi[axis]) / 2

    def ref(self, axis):
        """The reference point: lower-left for a box, the start of the axis for a
        strip, the centre otherwise."""
        if self.shape == "box":
            return self.lo[axis]
        if self.shape == "strip":
            return self.start[0 if axis == "x" else 1]
        return self.centre(axis)


ORIGIN = Extent(Fraction(0), Fraction(0), Fraction(0), Fraction(0), "point")

EDGES = ("top", "bottom", "left", "right",
         "top_left", "top_right", "bottom_left", "bottom_right")


def sub_extent(e, edge):
    """An edge of an extent as a zero-thickness box (its reference point is its
    left or lower end), a corner as a point (D-003)."""
    x0, y0, x1, y1 = e.lo["x"], e.lo["y"], e.hi["x"], e.hi["y"]
    if edge == "top":
        return Extent(x0, y1, x1, y1, "box")
    if edge == "bottom":
        return Extent(x0, y0, x1, y0, "box")
    if edge == "left":
        return Extent(x0, y0, x0, y1, "box")
    if edge == "right":
        return Extent(x1, y0, x1, y1, "box")
    corners = {"top_left": (x0, y1), "top_right": (x1, y1),
               "bottom_left": (x0, y0), "bottom_right": (x1, y0)}
    if edge in corners:
        x, y = corners[edge]
        return Extent(x, y, x, y, "point")
    raise ValueError('"%s" is not an edge or a corner' % edge)


def target_extent(placed, target):
    """The extent a relation measures from: the object, or one edge or corner of it."""
    name, _, edge = target.partition(" ")
    e = placed[name]
    return sub_extent(e, edge) if edge else e


def _interval(obj, axis, rel, placed):
    """The object's [lo, hi] on `axis`, from the one relation that fixes it."""
    word = rel["relation"]
    if word == "between":
        raise PlacementError(obj["name"], '"between" spans a straight thing (a wall, a road, a '
                             "pipe, a wire, a line) from one object to the other; a %s is not "
                             "one: place it with centred on or offset from"
                             % obj["kind"].replace("_", " "))
    if word not in SUPPORTED:
        raise NotPlacedYet(obj["name"], '"%s" is placed by the solver of phase 2, not yet '
                           "here" % word.replace("_", " "))
    target = target_extent(placed, rel["to"][0])
    size = obj["size"][axis]
    half = size / 2
    if word == "at":
        r = target.ref(axis)
        return (r, r + size) if obj["shape"] == "box" else (r - half, r + half)
    if word in ("centred_on", "aligned_with"):
        c = target.centre(axis)
        return c - half, c + half
    if word == "along":
        across = _strip_axes(obj, rel, placed)[1]
        if axis == across:
            side = rel.get("side")
            if side is None:                       # on the target's long axis
                c = target.centre(axis)
                return c - half, c + half
            if side in ("right", "above"):         # against the edge, outside
                return target.hi[axis], target.hi[axis] + size
            return target.lo[axis] - size, target.lo[axis]
        return target.lo[axis], target.lo[axis] + size   # starts where the target starts
    if word == "distributed_over":
        along_axis = _long_axis(obj, target, rel["to"][0])
        if axis != along_axis:                     # across, by default: centred
            c = target.centre(axis)
            return c - half, c + half
        centres = _copy_centres(obj, target, axis, rel["count"])
        return centres[0] - half, centres[-1] + half
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


def _long_axis(obj, target, name):
    w = target.hi["x"] - target.lo["x"]
    h = target.hi["y"] - target.lo["y"]
    if w == h:
        raise PlacementError(obj["name"], '"%s" is as wide as it is tall, so it has no long '
                             "axis to run along; name a side" % name)
    return "x" if w > h else "y"


def _strip_axes(obj, rel, placed):
    """(along, across) sheet axes of a strip placed along a target."""
    side = rel.get("side")
    if side is not None:
        return ("x", "y") if side in ("above", "below") else ("y", "x")
    a = _long_axis(obj, target_extent(placed, rel["to"][0]), rel["to"][0])
    return a, ("y" if a == "x" else "x")


def _copy_centres(obj, target, axis, count):
    """D-004 (default): N copies, N + 1 equal spaces between the target's ends
    and the copies' centres. Copies that would overlap are refused."""
    L = target.hi[axis] - target.lo[axis]
    pitch = L / (count + 1)
    if obj["size"][axis] > pitch:
        raise PlacementError(obj["name"], "%d copies %s mm wide do not fit side by side over "
                             "%s mm: the pitch would be %s mm" % (count, fmt(obj["size"][axis]),
                                                                   fmt(L), fmt(pitch)))
    return [target.lo[axis] + pitch * (i + 1) for i in range(count)]


def _shared_edge(name, a, b, an, bn):
    """The edge two touching rectangles share, as (start, end) -- D-005."""
    for ax, other in (("x", "y"), ("y", "x")):
        for first, second in ((a, b), (b, a)):
            if first.hi[ax] == second.lo[ax]:
                lo = max(first.lo[other], second.lo[other])
                hi = min(first.hi[other], second.hi[other])
                if lo < hi:
                    at = first.hi[ax]
                    return ((at, lo), (at, hi)) if ax == "x" else ((lo, at), (hi, at))
    raise PlacementError(name, '"%s" and "%s" share no edge, so there is nothing between them '
                         "to lie on; place it with along or offset from instead" % (an, bn))


def _ref_point(e):
    return (e.ref("x"), e.ref("y"))


def _strip(obj, placed):
    """A strip (wall, road, pipe, wire) from its along or between relation."""
    rels = obj["axes"]
    width = obj["across"]
    if rels["x"]["relation"] == "between":
        rel = rels["x"]
        an, bn = rel["to"]
        a, b = target_extent(placed, an), target_extent(placed, bn)
        if a.shape == "box" and b.shape == "box":
            start, end = _shared_edge(obj["name"], a, b, an, bn)
        else:
            start, end = _ref_point(a), _ref_point(b)
        if start == end:
            raise PlacementError(obj["name"], '"%s" and "%s" are at the same point: there is '
                                 "nothing between them" % (an, bn))
        half = width / 2
        x0, x1 = min(start[0], end[0]), max(start[0], end[0])
        y0, y1 = min(start[1], end[1]), max(start[1], end[1])
        if x0 == x1:                               # vertical: thick across x
            return Extent(x0 - half, y0, x1 + half, y1, "strip", start, end, width)
        if y0 == y1:
            return Extent(x0, y0 - half, x1, y1 + half, "strip", start, end, width)
        return Extent(x0, y0, x1, y1, "strip", start, end, width)    # diagonal: the axis
    along_rel = rels["x"] if rels["x"]["relation"] == "along" else rels["y"]
    along, across = _strip_axes(obj, along_rel, placed)
    target = target_extent(placed, along_rel["to"][0])
    length = obj["length"]
    if length is None:
        length = target.hi[along] - target.lo[along]     # the whole length of the target
    sized = dict(obj, size={along: length, across: width}, shape="strip")
    lo, hi = {}, {}
    for axis in ("x", "y"):
        lo[axis], hi[axis] = _interval(sized, axis, rels[axis], placed)
    mid = (lo[across] + hi[across]) / 2
    if along == "x":
        start, end = (lo["x"], mid), (hi["x"], mid)
    else:
        start, end = (mid, lo["y"]), (mid, hi["y"])
    return Extent(lo["x"], lo["y"], hi["x"], hi["y"], "strip", start, end, width)


CORNERS = ("bottom_left", "bottom_right", "top_left", "top_right")


def _corner_feature(obj, placed):
    """Fillets and chamfers: the square each one takes out of its host's corner."""
    host = placed[obj["host"]]
    size = obj["corner_size"]
    w = host.hi["x"] - host.lo["x"]
    h = host.hi["y"] - host.lo["y"]
    corners = CORNERS if obj["corner"] == "all" else (obj["corner"],)
    limit = min(w, h) / 2 if len(corners) > 1 else min(w, h)
    if size > limit:
        raise PlacementError(obj["name"], "a %s of %s mm does not fit the %s mm x %s mm corners "
                             'of "%s"' % (obj["kind"], fmt(size), fmt(w), fmt(h), obj["host"]))
    parts = []
    for c in corners:
        x0 = host.lo["x"] if c.endswith("left") else host.hi["x"] - size
        y0 = host.lo["y"] if c.startswith("bottom") else host.hi["y"] - size
        parts.append((c, Extent(x0, y0, x0 + size, y0 + size, "box")))
    e = Extent(min(p.lo["x"] for _, p in parts), min(p.lo["y"] for _, p in parts),
               max(p.hi["x"] for _, p in parts), max(p.hi["y"] for _, p in parts), "box")
    e.parts = parts
    return e


def _copies(obj, e, placed):
    """Split a distributed object's extent into its copies."""
    for axis in ("x", "y"):
        rel = obj["axes"][axis]
        if rel["relation"] != "distributed_over":
            continue
        target = target_extent(placed, rel["to"][0])
        if axis != _long_axis(obj, target, rel["to"][0]):
            continue
        half = obj["size"][axis] / 2
        parts = []
        for i, c in enumerate(_copy_centres(obj, target, axis, rel["count"])):
            lo, hi = dict(e.lo), dict(e.hi)
            lo[axis], hi[axis] = c - half, c + half
            parts.append((str(i + 1), Extent(lo["x"], lo["y"], hi["x"], hi["y"], obj["shape"])))
        e.parts = parts
    return e


def place(objects):
    """objects: in order, each {"name", "kind", "shape", "size": {"x", "y"},
    "axes": {"x": rel, "y": rel}, "inside": [names]}, where a rel is
    {"relation", "to": [...], and its parameters with distances already in mm}.
    shape is "box", "round" or "point"; "strip" (with "across" and "length",
    either None) for walls, roads, pipes and wires placed along or between;
    "corner" (with "host", "corner", "corner_size") for fillets and chamfers;
    None when the size is not in the script ("size_from" says where it will come
    from). Returns {name: Extent}."""
    placed = {"origin": ORIGIN}
    for obj in objects:
        shape = obj.get("shape")
        if shape is None:
            raise SizeNotKnown(obj["name"], obj.get("size_from") or "its size is not in the "
                               "script")
        if shape == "corner":
            placed[obj["name"]] = _corner_feature(obj, placed)
            continue
        if shape == "strip":
            if obj.get("across") is None:
                raise SizeNotKnown(obj["name"], obj["size_from"])
            e = _strip(obj, placed)
        else:
            lo, hi = {}, {}
            for axis in ("x", "y"):
                lo[axis], hi[axis] = _interval(obj, axis, obj["axes"][axis], placed)
            e = _copies(obj, Extent(lo["x"], lo["y"], hi["x"], hi["y"], shape), placed)
        for host in obj.get("inside", []):
            h = placed[host]
            if not all(h.lo[a] <= e.lo[a] and e.hi[a] <= h.hi[a] for a in ("x", "y")):
                raise PlacementError(obj["name"], 'it is not inside "%s": the relations that '
                                     "place it put it partly outside" % host)
        for host in obj.get("on", []):             # "on" places nothing, but it checks
            h = placed.get(host)
            if h is not None and not all(h.lo[a] <= e.lo[a] and e.hi[a] <= h.hi[a]
                                         for a in ("x", "y")):
                raise PlacementError(obj["name"], 'it is not on "%s": the relations that '
                                     "place it put it partly off it" % host)
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
    """The canonical text of a placement: one line per object, in order, mm.

    Objects that came through the free channel (ADR 0009) are never mixed with
    checked ones: they follow in their own section, each marked FREE with its
    source, and for them only the local origin is placed."""
    lines = ["# linework placement 1 -- millimetres, x right, y up, from origin",
             "# name kind xmin ymin xmax ymax"]
    free = [o for o in objects if o.get("free")]
    strips = []
    for obj in objects:
        if obj.get("free"):
            continue
        e = placed[obj["name"]]
        if e.parts:
            for label, part in e.parts:
                lines.append("%s.%s %s %s %s %s %s" % (obj["name"], label, obj["kind"],
                                                       fmt(part.lo["x"]), fmt(part.lo["y"]),
                                                       fmt(part.hi["x"]), fmt(part.hi["y"])))
            continue
        lines.append("%s %s %s %s %s %s" % (obj["name"], obj["kind"], fmt(e.lo["x"]),
                                            fmt(e.lo["y"]), fmt(e.hi["x"]), fmt(e.hi["y"])))
        if e.shape == "strip":
            strips.append((obj, e))
    if strips:
        lines.append("# AXES -- straight things: the axis from start to end, and the width")
        lines.append("# name kind start_x start_y end_x end_y width")
        for obj, e in strips:
            lines.append("%s %s %s %s %s %s %s" % (obj["name"], obj["kind"], fmt(e.start[0]),
                                                   fmt(e.start[1]), fmt(e.end[0]),
                                                   fmt(e.end[1]), fmt(e.width)))
    if free:
        lines.append("# FREE CHANNEL -- not checked by the language; review separately")
        lines.append("# name FREE source origin_x origin_y")
        for obj in free:
            e = placed[obj["name"]]
            lines.append("%s FREE %s %s %s" % (obj["name"], obj["free"], fmt(e.lo["x"]),
                                               fmt(e.lo["y"])))
    return "\n".join(lines) + "\n"
