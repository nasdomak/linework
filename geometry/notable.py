"""geometry.notable -- the notable points of a shape, for dimensions to attach
to automatically (P2-T04, ADR 0013).

A dimension in a technical drawing runs between notable points: the ends and
middle of a line, the centre and quadrant points of a circle, the vertices of
an ellipse, the corners and edge midpoints of a rectangle. Every point here is
exact (geometry.exact) and named, so a dimension says what it measures
("plate1 top_left to h_c centre"), never a coordinate.

notable(shape) returns an ordered list of (name, Point). Names:

- segment:   start, end, mid
- circle:    centre, quadrant_0, quadrant_90, quadrant_180, quadrant_270
- arc:       centre, start, end, mid, and the quadrant points that lie on it
- ellipse:   centre, major_1, major_2, minor_1, minor_2 (and start, end for an
             elliptical arc, with the vertices that lie on it)
- extent:    centre, the four corners and the four edge midpoints of a
             placed rectangle (geometry.placement.Extent): top_left, top,
             top_right, left, right, bottom_left, bottom, bottom_right

Standard library only (CORE package).
"""

from geometry.exact import Num
from geometry.primitives import Point, Segment, Circle, Arc, Ellipse, cross, dot


def _mid(a, b):
    return Point((a.x + b.x) / 2, (a.y + b.y) / 2)


def _arc_mid(arc):
    """The point halfway along an arc (of a circle or an ellipse), by angle."""
    s, e = arc.start, arc.end
    ls = (s[0] * s[0] + s[1] * s[1]).sqrt()
    le = (e[0] * e[0] + e[1] * e[1]).sqrt()
    ux, uy = s[0] / ls, s[1] / ls
    vx, vy = e[0] / le, e[1] / le
    c = cross(ux, uy, vx, vy).sign()
    if c == 0 and dot(ux, uy, vx, vy).sign() < 0:
        d = (-uy, ux)                                # exactly half a turn: a quarter on
    else:
        d = (ux + vx, uy + vy)
        if c < 0:                                    # more than half a turn
            d = (-d[0], -d[1])
    return arc.ray_point(d)


def notable(shape):
    """[(name, Point)] -- see the module documentation for the names."""
    if isinstance(shape, Point):
        return [("point", shape)]
    if isinstance(shape, Segment):
        return [("start", shape.p), ("end", shape.q), ("mid", _mid(shape.p, shape.q))]
    if isinstance(shape, Circle):
        c, r = shape.c, shape.r
        quads = [("quadrant_0", Point(c.x + r, c.y)), ("quadrant_90", Point(c.x, c.y + r)),
                 ("quadrant_180", Point(c.x - r, c.y)), ("quadrant_270", Point(c.x, c.y - r))]
        if not isinstance(shape, Arc):
            return [("centre", c)] + quads
        a, b = shape.endpoints()
        return ([("centre", c), ("start", a), ("end", b), ("mid", _arc_mid(shape))]
                + [(nm, p) for nm, p in quads if shape.in_piece(p)])
    if isinstance(shape, Ellipse):
        c = shape.c
        u, v = shape.major
        rho = shape.ratio
        verts = [("major_1", Point(c.x + u, c.y + v)), ("major_2", Point(c.x - u, c.y - v)),
                 ("minor_1", Point(c.x - v * rho, c.y + u * rho)),
                 ("minor_2", Point(c.x + v * rho, c.y - u * rho))]
        if shape.start is None:
            return [("centre", c)] + verts
        a, b = shape.endpoints()
        return ([("centre", c), ("start", a), ("end", b), ("mid", _arc_mid(shape))]
                + [(nm, p) for nm, p in verts if shape.in_piece(p)])
    if hasattr(shape, "lo") and hasattr(shape, "hi"):          # a placement Extent
        x0, y0 = Num.of(shape.lo["x"]), Num.of(shape.lo["y"])
        x1, y1 = Num.of(shape.hi["x"]), Num.of(shape.hi["y"])
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        return [("centre", Point(xm, ym)),
                ("top_left", Point(x0, y1)), ("top", Point(xm, y1)), ("top_right", Point(x1, y1)),
                ("left", Point(x0, ym)), ("right", Point(x1, ym)),
                ("bottom_left", Point(x0, y0)), ("bottom", Point(xm, y0)),
                ("bottom_right", Point(x1, y0))]
    raise TypeError("no notable points for %r" % (shape,))


def point(shape, name):
    """One notable point by name."""
    for nm, p in notable(shape):
        if nm == name:
            return p
    raise KeyError('a %s has no notable point "%s"; it has: %s' % (
        getattr(shape, "kind", "shape"), name, ", ".join(nm for nm, _ in notable(shape))))
