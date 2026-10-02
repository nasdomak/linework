"""geometry.ops -- offsets, trim, extend, fillet, chamfer, tangents (P2-T02,
ADR 0011).

The operations a draughtsman does by hand a hundred times a day, and the ones a
model must never approximate. Each takes exact shapes and returns exact shapes
(geometry.primitives on geometry.exact numbers).

Tolerance policy, stated once for every operation here: **there is none.**
Each result is computed exactly; a case that would need a tolerance to decide
(is this pick on the cut point? does the fillet fit?) is decided exactly, and
when the honest answer is "this is ambiguous" or "this does not fit", the
operation refuses with the reason (OperationRefused) instead of guessing.

- offset(shape, distance, side)          segment (left/right of p -> q),
                                          circle and arc (outside/inside)
- split(shape, points) / trim(shape, cutters, pick)
- extend(shape, boundary, end)            segment (end 'p' or 'q'), arc
                                          (end 'start' or 'end')
- fillet(a, b, r)                         two segments, any angle
- chamfer(a, b, d1, d2=None)              two segments, any angle
- tangents_from_point(point, circle)
- tangents_between(c1, c2)                external and internal

Standard library only (CORE package).
"""

from geometry.exact import Num
from geometry.primitives import (Point, Segment, Circle, Arc, Ellipse, Degenerate,
                                 NotSupported, intersect, between, turn_le, cross, dot,
                                 _line_conic, _same_dir)


class OperationRefused(ValueError):
    """The operation cannot be done exactly as asked; the message says why."""


def n(v):
    return Num.of(v)


def _positive(value, what):
    v = n(value)
    if v.sign() <= 0:
        raise OperationRefused("the %s must be greater than zero, not %s" % (what, v.decimal(6)))
    return v


def _norm(dx, dy):
    return (dx * dx + dy * dy).sqrt()


# ----------------------------------------------------------------------------
# Offsets


def offset(shape, distance, side):
    """A parallel copy at `distance`. Segments: side 'left' or 'right' of the
    direction p -> q. Circles and arcs: 'outside' or 'inside'."""
    d = _positive(distance, "offset distance")
    if isinstance(shape, Segment):
        if side not in ("left", "right"):
            raise OperationRefused("a segment is offset to the 'left' or the 'right' of its "
                                   "direction, not '%s'" % side)
        L = _norm(shape.dx, shape.dy)
        k = d / L if side == "left" else -d / L
        ox, oy = -shape.dy * k, shape.dx * k
        return Segment(Point(shape.p.x + ox, shape.p.y + oy), Point(shape.q.x + ox, shape.q.y + oy))
    if isinstance(shape, (Arc, Circle)):
        if side not in ("outside", "inside"):
            raise OperationRefused("a circle or an arc is offset 'outside' or 'inside', not '%s'"
                                   % side)
        r = shape.r + d if side == "outside" else shape.r - d
        if r.sign() <= 0:
            raise OperationRefused("an inside offset of %s is not smaller than the radius %s: "
                                   "nothing would be left" % (d.decimal(6), shape.r.decimal(6)))
        if isinstance(shape, Arc):
            return Arc(shape.c, r, shape.start, shape.end)
        return Circle(shape.c, r)
    if isinstance(shape, Ellipse):
        raise NotSupported("the offset of an ellipse is not an ellipse; it is not computed "
                           "in this version rather than approximated")
    raise OperationRefused("a %s has no offset" % shape.kind)


# ----------------------------------------------------------------------------
# Split and trim


def _dir(shape, p):
    return (p.x - shape.c.x, p.y - shape.c.y)


def _with_piece(shape, s, e):
    if isinstance(shape, Ellipse):
        return Ellipse(shape.c, shape.major, shape.ratio, s, e)
    return Arc(shape.c, shape.r, s, e)


def _sort_turns(ref, dirs):
    out = []
    for d in dirs:
        i = 0
        while i < len(out) and turn_le(ref, out[i], d):
            i += 1
        out.insert(i, d)
    return out


def split(shape, points):
    """The pieces of `shape` between the given points (which must lie on it),
    in order along it."""
    for p in points:
        if not shape.on(p):
            raise OperationRefused("the point %s is not on the %s" % (p.text(), shape.kind))
    if isinstance(shape, Segment):
        ts = [n(0), n(1)]
        for p in points:
            t = shape.param(p)
            if not any(t == u for u in ts):
                ts.append(t)
        ts = _sorted_nums(ts)
        pts = [Point(shape.p.x + t * shape.dx, shape.p.y + t * shape.dy) for t in ts]
        return [Segment(a, b) for a, b in zip(pts, pts[1:])]
    if shape.start is not None:                      # an arc of a circle or an ellipse
        dirs = []
        for p in points:
            d = _dir(shape, p)
            if not any(_same_dir(d, e) for e in dirs + [shape.start, shape.end]):
                dirs.append(d)
        cuts = [shape.start] + _sort_turns(shape.start, dirs) + [shape.end]
        return [_with_piece(shape, a, b) for a, b in zip(cuts, cuts[1:])]
    dirs = []
    for p in points:
        d = _dir(shape, p)
        if not any(_same_dir(d, e) for e in dirs):
            dirs.append(d)
    if len(dirs) < 2:
        raise OperationRefused("a closed %s needs at least two cut points to come apart"
                               % shape.kind)
    cuts = _sort_turns(dirs[0], dirs)
    return [_with_piece(shape, a, b) for a, b in zip(cuts, cuts[1:] + cuts[:1])]


def _sorted_nums(xs):
    out = []
    for x in xs:
        i = 0
        while i < len(out) and out[i] < x:
            i += 1
        out.insert(i, x)
    return out


def _cut_points(shape, cutters):
    pts = []
    for c in cutters:
        r = intersect(shape, c)
        if r.overlap:
            raise OperationRefused("a cutting %s lies along the %s: there is no single cut "
                                   "point" % (c.kind, shape.kind))
        for p in r.points:
            if not any(p == q for q in pts):
                pts.append(p)
    return pts


def _piece_holding(shape, pieces, pick):
    """The piece whose interior holds the pick (projected onto the shape)."""
    if isinstance(shape, Segment):
        t = shape.param(Point(pick[0], pick[1]) if not isinstance(pick, Point) else pick)
        if t.sign() < 0 or t > 1:
            raise OperationRefused("the pick is beyond the ends of the segment")
        for i, piece in enumerate(pieces):
            a, b = shape.param(piece.p), shape.param(piece.q)
            if a < t and t < b:
                return i
        raise OperationRefused("the pick falls exactly on a cut point: say which side to remove")
    pick = pick if isinstance(pick, Point) else Point(pick[0], pick[1])
    v = _dir(shape, pick)
    if v[0].is_zero() and v[1].is_zero():
        raise OperationRefused("the pick is the centre: it names no part of the curve")
    for i, piece in enumerate(pieces):
        if between(piece.start, piece.end, v) and not _same_dir(v, piece.start) \
                and not _same_dir(v, piece.end):
            return i
    raise OperationRefused("the pick falls exactly on a cut point: say which side to remove")


def trim(shape, cutters, pick):
    """Remove the piece of `shape`, between its cuts by `cutters`, that holds the
    pick. Returns the pieces that remain, in order."""
    pts = _cut_points(shape, cutters)
    if not pts:
        raise OperationRefused("nothing cuts the %s, so nothing is trimmed" % shape.kind)
    pieces = split(shape, pts)
    i = _piece_holding(shape, pieces, pick)
    return pieces[:i] + pieces[i + 1:]


# ----------------------------------------------------------------------------
# Extend


class _Ray(object):
    """The infinite carrier line of a segment, for intersection with conics."""

    def __init__(self, seg):
        self.p, self.dx, self.dy = seg.p, seg.dx, seg.dy


def _line_hits(seg, boundary):
    """Points where the carrier line of seg meets the boundary piece."""
    if isinstance(boundary, Segment):
        den = cross(seg.dx, seg.dy, boundary.dx, boundary.dy)
        if den.is_zero():
            return []
        wx, wy = boundary.p.x - seg.p.x, boundary.p.y - seg.p.y
        t = cross(wx, wy, boundary.dx, boundary.dy) / den
        p = Point(seg.p.x + t * seg.dx, seg.p.y + t * seg.dy)
        return [p] if boundary.in_piece(p) else []
    if isinstance(boundary, Point):
        return [boundary] if seg.on_carrier(boundary) else []
    pts, _ = _line_conic(_Ray(seg), boundary)
    return [p for p in pts if boundary.in_piece(p)]


def extend(shape, boundary, end):
    """Lengthen `shape` from its `end` until it first meets `boundary`."""
    if isinstance(shape, Segment):
        if end not in ("p", "q"):
            raise OperationRefused("a segment is extended at its end 'p' or 'q', not '%s'" % end)
        ts = [shape.param(p) for p in _line_hits(shape, boundary)]
        if end == "q":
            ahead = [t for t in ts if t > 1]
            if not ahead:
                raise OperationRefused("extended past q, the segment never meets the %s"
                                       % boundary.kind)
            t = _sorted_nums(ahead)[0]
            return Segment(shape.p, Point(shape.p.x + t * shape.dx, shape.p.y + t * shape.dy))
        behind = [t for t in ts if t.sign() < 0]
        if not behind:
            raise OperationRefused("extended past p, the segment never meets the %s"
                                   % boundary.kind)
        t = _sorted_nums(behind)[-1]
        return Segment(Point(shape.p.x + t * shape.dx, shape.p.y + t * shape.dy), shape.q)
    if isinstance(shape, Arc):
        if end not in ("start", "end"):
            raise OperationRefused("an arc is extended at its 'start' or its 'end', not '%s'"
                                   % end)
        full = Circle(shape.c, shape.r)
        r = intersect(full, boundary)
        dirs = [_dir(shape, p) for p in r.points]
        if end == "end":
            cands = [d for d in dirs if not _same_dir(d, shape.end)
                     and turn_le(shape.end, d, shape.start)]
            if not cands:
                raise OperationRefused("going on from its end, the arc never meets the %s "
                                       "before closing on itself" % boundary.kind)
            new = _sort_turns(shape.end, cands)[0]
            return Arc(shape.c, shape.r, shape.start, new)
        # going back (clockwise) from the start, outside the arc: the nearest is
        # the one with the largest counter-clockwise turn from the start
        cands = [d for d in dirs if not between(shape.start, shape.end, d)]
        if not cands:
            raise OperationRefused("going back from its start, the arc never meets the %s "
                                   "before closing on itself" % boundary.kind)
        new = _sort_turns(shape.start, cands)[-1]
        return Arc(shape.c, shape.r, new, shape.end)
    raise OperationRefused("only segments and arcs are extended")


# ----------------------------------------------------------------------------
# Corners: fillet and chamfer


class Corner(object):
    """Two segments seen from the point X where their lines meet: for each, the
    unit direction from X towards its far end and the distance to it."""

    def __init__(self, a, b):
        den = cross(a.dx, a.dy, b.dx, b.dy)
        if den.is_zero():
            raise OperationRefused("the two segments are parallel: they make no corner")
        wx, wy = b.p.x - a.p.x, b.p.y - a.p.y
        t = cross(wx, wy, b.dx, b.dy) / den
        self.X = Point(a.p.x + t * a.dx, a.p.y + t * a.dy)
        self.legs = [self._leg(a, "first"), self._leg(b, "second")]

    def _leg(self, s, name):
        tp, tq = s.param(self.X), n(1) - s.param(self.X)
        if tp.sign() > 0 and tq.sign() > 0:
            raise OperationRefused("the %s segment runs through the corner: say which part of "
                                   "it to keep" % name)
        far = s.q if tp.sign() <= 0 else s.p
        vx, vy = far.x - self.X.x, far.y - self.X.y
        L = _norm(vx, vy)
        return {"far": far, "ux": vx / L, "uy": vy / L, "len": L, "name": name}

    def at(self, leg, dist):
        return Point(self.X.x + leg["ux"] * dist, self.X.y + leg["uy"] * dist)


class CornerResult(object):
    """first, second: the two segments, trimmed (or extended) to the corner
    piece; piece: the fillet arc or the chamfer segment."""

    def __init__(self, first, second, piece):
        self.first, self.second, self.piece = first, second, piece

    def __repr__(self):
        return "CornerResult(%r, %r, %r)" % (self.first, self.second, self.piece)


def _leg_segment(corner, leg, dist):
    if not dist < leg["len"]:
        raise OperationRefused("the %s segment is too short: the corner needs %s of it and "
                               "it is %s long" % (leg["name"], dist.decimal(6),
                                                  leg["len"].decimal(6)))
    return Segment(corner.at(leg, dist), leg["far"])


def fillet(a, b, radius):
    """Round the corner between two segments with an arc of `radius`, tangent
    to both. Works at any angle; the segments are trimmed (or extended) to the
    tangent points."""
    r = _positive(radius, "fillet radius")
    k = Corner(a, b)
    l1, l2 = k.legs
    cos = l1["ux"] * l2["ux"] + l1["uy"] * l2["uy"]
    # distance from the corner to each tangent point: r / tan(theta / 2)
    # with tan(theta / 2) = sin / (1 + cos) and sin = sqrt(1 - cos^2) >= 0
    sin = (1 - cos * cos).sqrt()
    t = r * (1 + cos) / sin
    s1, s2 = _leg_segment(k, l1, t), _leg_segment(k, l2, t)
    T1, T2 = s1.p, s2.p
    # the centre: from T1, r along the normal of the first leg towards the second
    nx, ny = -l1["uy"], l1["ux"]
    if dot(nx, ny, l2["ux"], l2["uy"]).sign() < 0:
        nx, ny = -nx, -ny
    C = Point(T1.x + nx * r, T1.y + ny * r)
    d1 = (T1.x - C.x, T1.y - C.y)
    d2 = (T2.x - C.x, T2.y - C.y)
    if cross(d1[0], d1[1], d2[0], d2[1]).sign() > 0:
        arc = Arc(C, r, d1, d2)
    else:
        arc = Arc(C, r, d2, d1)
    return CornerResult(s1, s2, arc)


def chamfer(a, b, d1, d2=None):
    """Cut the corner between two segments with a straight piece, `d1` along
    the first and `d2` (default d1) along the second, measured from the corner."""
    d1 = _positive(d1, "chamfer distance")
    d2 = d1 if d2 is None else _positive(d2, "chamfer distance")
    k = Corner(a, b)
    s1, s2 = _leg_segment(k, k.legs[0], d1), _leg_segment(k, k.legs[1], d2)
    return CornerResult(s1, s2, Segment(s1.p, s2.p))


# ----------------------------------------------------------------------------
# Tangents


def tangents_from_point(p, circle):
    """The tangent points on `circle` of the lines through `p`: two when p is
    outside, one (p itself) when on the circle, none inside."""
    p = p if isinstance(p, Point) else Point(*p)
    c, r = circle.c, circle.r
    vx, vy = p.x - c.x, p.y - c.y
    d2 = vx * vx + vy * vy
    s = (d2 - r * r).sign()
    if s < 0:
        return []
    if s == 0:
        return [p]
    k = r * r / d2
    h = r * (d2 - r * r).sqrt() / d2
    out = [Point(c.x + k * vx - h * vy, c.y + k * vy + h * vx),
           Point(c.x + k * vx + h * vy, c.y + k * vy - h * vx)]
    return [q for q in out if isinstance(circle, Circle) and circle.on(q)]


class TangentLine(object):
    """A common tangent: kind 'external' or 'internal', and its touching points
    on the first and on the second circle (the same point when they touch)."""

    def __init__(self, kind, t1, t2):
        self.kind, self.t1, self.t2 = kind, t1, t2

    def __repr__(self):
        return "TangentLine(%s, %s, %s)" % (self.kind, self.t1.text(), self.t2.text())


def tangents_between(c1, c2):
    """Every line tangent to both circles: up to two external and two internal."""
    vx, vy = c2.c.x - c1.c.x, c2.c.y - c1.c.y
    d2 = vx * vx + vy * vy
    if d2.is_zero():
        if c1.r == c2.r:
            raise OperationRefused("the circles are the same circle: every tangent of one is "
                                   "a tangent of the other")
        return []
    out = []
    for kind in ("external", "internal"):
        # the unit normal m of the tangent line satisfies m . (c2 - c1) = k, with
        # k = r1 - r2 (both circles on one side) or r1 + r2 (on opposite sides);
        # m = (k / d^2) v + b perp(v), |m| = 1 gives b = +- sqrt(d^2 - k^2) / d^2
        k = c1.r - c2.r if kind == "external" else c1.r + c2.r
        rest = d2 - k * k
        sg = rest.sign()
        if sg < 0:
            continue
        a = k / d2
        roots = [n(0)] if sg == 0 else [rest.sqrt() / d2, -(rest.sqrt() / d2)]
        for b in roots:
            mx, my = a * vx - b * vy, a * vy + b * vx
            t1 = Point(c1.c.x + c1.r * mx, c1.c.y + c1.r * my)
            sign2 = 1 if kind == "external" else -1
            t2 = Point(c2.c.x + sign2 * c2.r * mx, c2.c.y + sign2 * c2.r * my)
            out.append(TangentLine(kind, t1, t2))
    return out
