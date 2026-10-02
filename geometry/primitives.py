"""geometry.primitives -- points, segments, arcs, circles, ellipses, and the exact
intersection of every pair (P2-T01, ADR 0010).

Every coordinate is an exact number (geometry.exact.Num). Nothing here rounds
and nothing here has a tolerance: two curves touch or they do not.

The shapes:

- Point(x, y)
- Segment(p, q)                    p != q
- Circle(centre, r)                r > 0
- Arc(centre, r, start, end)       counter-clockwise from the direction `start`
                                   to the direction `end` (vectors from the
                                   centre, any length, never parallel and equal)
- Ellipse(centre, major, ratio, start=None, end=None)
                                   `major` is the semi-major axis as a vector
                                   (DXF style), 0 < ratio <= 1 the minor/major
                                   ratio; with start and end directions it is an
                                   elliptical arc, counter-clockwise.

A degenerate shape (zero length, zero radius, start equal to end ...) is refused
when it is made, with the reason, never carried along to fail later.

intersect(a, b) returns an Intersection: the points where they meet (each
marked tangent or not), the pieces they share when they overlap, and notes that
name the degenerate situation met: parallel, collinear, tangent, concentric,
coincident, outside (the carriers meet, but not on the pieces).

Standard library only (CORE package).
"""

from fractions import Fraction

from geometry.exact import (Num, ZERO, ONE, real_roots, resultant, ngcd, nstrip,
                            neval_xpoly)


class Degenerate(ValueError):
    """A shape that is not one: zero length, zero radius, an empty arc."""


class NotSupported(NotImplementedError):
    """An exact computation this version does not perform, named, never guessed."""


def n(value):
    return Num.of(value)


def _vec(v, what):
    if isinstance(v, Point):
        return v.x, v.y
    try:
        x, y = v
    except (TypeError, ValueError):
        raise Degenerate("%s must be a pair (dx, dy)" % what)
    return n(x), n(y)


def cross(ax, ay, bx, by):
    return ax * by - ay * bx


def dot(ax, ay, bx, by):
    return ax * bx + ay * by


class Point(object):
    __slots__ = ("x", "y")
    __hash__ = None
    kind = "point"

    def __init__(self, x, y):
        self.x, self.y = n(x), n(y)

    def __eq__(self, other):
        return isinstance(other, Point) and self.x == other.x and self.y == other.y

    def __ne__(self, other):
        return not self == other

    def key_lt(self, other):
        if self.x != other.x:
            return self.x < other.x
        return self.y < other.y

    def exact(self):
        """(Fraction, Fraction) when both coordinates are rational."""
        return self.x.as_fraction(), self.y.as_fraction()

    def text(self, digits=6):
        return "(%s, %s)" % (self.x.decimal(digits), self.y.decimal(digits))

    def __repr__(self):
        return "Point(%r, %r)" % (self.x, self.y)

    def on(self, p):
        return self == p


def P(x, y):
    return Point(x, y)


def _pt(p):
    if isinstance(p, Point):
        return p
    x, y = p
    return Point(x, y)


class Segment(object):
    kind = "segment"

    def __init__(self, p, q):
        self.p, self.q = _pt(p), _pt(q)
        if self.p == self.q:
            raise Degenerate("a segment from %s to itself has zero length; use a point"
                             % self.p.text())
        self.dx, self.dy = self.q.x - self.p.x, self.q.y - self.p.y

    def __repr__(self):
        return "Segment(%s, %s)" % (self.p.text(), self.q.text())

    def param(self, pt):
        """t with pt = p + t (q - p), for a point on the carrier line."""
        return dot(pt.x - self.p.x, pt.y - self.p.y, self.dx, self.dy) / dot(
            self.dx, self.dy, self.dx, self.dy)

    def on_carrier(self, pt):
        return cross(pt.x - self.p.x, pt.y - self.p.y, self.dx, self.dy).is_zero()

    def in_piece(self, pt):
        t = self.param(pt)
        return t >= 0 and t <= 1

    def on(self, pt):
        return self.on_carrier(pt) and self.in_piece(pt)

    def __eq__(self, other):
        return isinstance(other, Segment) and (
            (self.p == other.p and self.q == other.q) or (self.p == other.q and self.q == other.p))

    __hash__ = None


def _check_dir(v, what):
    x, y = _vec(v, what)
    if x.is_zero() and y.is_zero():
        raise Degenerate("the %s direction is the zero vector" % what)
    return x, y


def _same_dir(a, b):
    return cross(a[0], a[1], b[0], b[1]).is_zero() and dot(a[0], a[1], b[0], b[1]) > 0


def _half(ref, u):
    c = cross(ref[0], ref[1], u[0], u[1]).sign()
    if c > 0:
        return 0
    if c == 0 and dot(ref[0], ref[1], u[0], u[1]) > 0:
        return 0
    return 1


def turn_le(ref, a, b):
    """Is the counter-clockwise turn from ref to a at most the turn from ref to b?
    Turns are in [0, 2 pi)."""
    ref, a, b = _vec(ref, "reference"), _vec(a, "first"), _vec(b, "second")
    ha, hb = _half(ref, a), _half(ref, b)
    if ha != hb:
        return ha < hb
    if _same_dir(ref, a):
        return True
    if _same_dir(ref, b):
        return False
    return cross(a[0], a[1], b[0], b[1]).sign() >= 0


def between(start, end, v):
    """Is direction v on the counter-clockwise sweep from start to end, inclusive?"""
    return turn_le(start, v, end)


class _Conic(object):
    """Shared by circles, arcs and ellipses: a centre, an implicit equation
    A x^2 + B xy + C y^2 + D x + E y + F = 0, and an optional angular piece."""

    start = end = None

    def coeffs(self):
        raise NotImplementedError

    def value(self, pt):
        A, B, C, D, E, F = self.coeffs()
        x, y = pt.x, pt.y
        return A * x * x + B * x * y + C * y * y + D * x + E * y + F

    def gradient(self, pt):
        A, B, C, D, E, F = self.coeffs()
        return 2 * A * pt.x + B * pt.y + D, B * pt.x + 2 * C * pt.y + E

    def on_carrier(self, pt):
        return self.value(pt).is_zero()

    def in_piece(self, pt):
        if self.start is None:
            return True
        v = (pt.x - self.c.x, pt.y - self.c.y)
        return between(self.start, self.end, v)

    def on(self, pt):
        return self.on_carrier(pt) and self.in_piece(pt)

    def _set_piece(self, start, end):
        if (start is None) != (end is None):
            raise Degenerate("an arc needs both a start and an end direction")
        if start is None:
            return
        self.start = _check_dir(start, "start")
        self.end = _check_dir(end, "end")
        if _same_dir(self.start, self.end):
            raise Degenerate("the start and end directions are the same: the arc is either "
                             "empty or the whole curve; say which by using the full curve")

    def ray_point(self, v):
        """Where the ray from the centre in direction v meets the curve."""
        A, B, C, D, E, F = self.coeffs()
        # with p = c + t v the equation becomes a t^2 + k = 0 (the centre is the
        # centre of symmetry, so there is no linear term)
        a = A * v[0] * v[0] + B * v[0] * v[1] + C * v[1] * v[1]
        k = self.value(self.c)
        t = (-k / a).sqrt()
        return Point(self.c.x + t * v[0], self.c.y + t * v[1])

    def endpoints(self):
        if self.start is None:
            return None
        return self.ray_point(self.start), self.ray_point(self.end)

    def same_carrier(self, other):
        a, b = self.coeffs(), other.coeffs()
        # proportional coefficient vectors; C is never zero for these curves
        return all((x * b[2] - y * a[2]).is_zero() for x, y in zip(a, b))


class Circle(_Conic):
    kind = "circle"

    def __init__(self, centre, r):
        self.c = _pt(centre)
        self.r = n(r)
        if self.r.sign() <= 0:
            raise Degenerate("a circle needs a radius greater than zero, not %s"
                             % self.r.decimal(6))

    def coeffs(self):
        cx, cy, r = self.c.x, self.c.y, self.r
        return n(1), n(0), n(1), -2 * cx, -2 * cy, cx * cx + cy * cy - r * r

    def __repr__(self):
        return "Circle(%s, r=%s)" % (self.c.text(), self.r.decimal(6))

    def __eq__(self, other):
        return isinstance(other, Circle) and self.c == other.c and self.r == other.r

    __hash__ = None


class Arc(Circle):
    kind = "arc"

    def __init__(self, centre, r, start, end):
        Circle.__init__(self, centre, r)
        self._set_piece(start, end)

    def __repr__(self):
        return "Arc(%s, r=%s, from %r to %r)" % (self.c.text(), self.r.decimal(6),
                                                 self.start, self.end)

    def __eq__(self, other):
        return (isinstance(other, Arc) and Circle.__eq__(self, other)
                and _same_dir(self.start, other.start) and _same_dir(self.end, other.end))

    __hash__ = None


class Ellipse(_Conic):
    kind = "ellipse"

    def __init__(self, centre, major, ratio, start=None, end=None):
        self.c = _pt(centre)
        self.major = _check_dir(major, "major axis")
        self.ratio = n(ratio)
        if self.ratio.sign() <= 0 or self.ratio > 1:
            raise Degenerate("the minor/major ratio of an ellipse must be greater than 0 and "
                             "at most 1, not %s" % self.ratio.decimal(6))
        self._set_piece(start, end)

    def coeffs(self):
        u, v = self.major
        rho2 = self.ratio * self.ratio
        L = u * u + v * v
        a = rho2 * u * u + v * v
        b = 2 * u * v * (rho2 - 1)
        c = rho2 * v * v + u * u
        k = rho2 * L * L
        cx, cy = self.c.x, self.c.y
        return (a, b, c, -2 * a * cx - b * cy, -2 * c * cy - b * cx,
                a * cx * cx + b * cx * cy + c * cy * cy - k)

    def __repr__(self):
        return "Ellipse(%s, major=%r, ratio=%s%s)" % (
            self.c.text(), self.major, self.ratio.decimal(6),
            "" if self.start is None else ", from %r to %r" % (self.start, self.end))


# ----------------------------------------------------------------------------
# The result


class Intersection(object):
    """points: the meeting points, sorted by x then y; tangent: the same length,
    True where the curves touch without crossing their carriers; overlap: the
    pieces both share; notes: words naming what was met."""

    def __init__(self, points=(), tangent=(), overlap=(), notes=()):
        pairs = []
        for p, t in zip(points, tangent):
            for i, (q, tq) in enumerate(pairs):
                if q == p:
                    pairs[i] = (q, tq or t)
                    break
            else:
                pairs.append((p, t))
        pairs = _sort_points(pairs)
        self.points = [p for p, _ in pairs]
        self.tangent = [t for _, t in pairs]
        self.overlap = list(overlap)
        self.notes = tuple(sorted(set(notes)))

    @property
    def kind(self):
        if self.overlap:
            return "overlap"
        return "points" if self.points else "none"

    def __repr__(self):
        return "Intersection(%s, points=%s, overlap=%s, notes=%s)" % (
            self.kind, [p.text() for p in self.points], self.overlap, self.notes)


def _sort_points(pairs):
    out = []
    for item in pairs:
        i = 0
        while i < len(out) and not item[0].key_lt(out[i][0]):
            i += 1
        out.insert(i, item)
    return out


# ----------------------------------------------------------------------------
# Carrier intersections


def _line_line(s1, s2):
    """Segment carriers: ('point', P) or ('parallel',) or ('collinear',)."""
    den = cross(s1.dx, s1.dy, s2.dx, s2.dy)
    if den.is_zero():
        return ("collinear",) if s2.on_carrier(s1.p) else ("parallel",)
    wx, wy = s2.p.x - s1.p.x, s2.p.y - s1.p.y
    t = cross(wx, wy, s2.dx, s2.dy) / den
    return ("point", Point(s1.p.x + t * s1.dx, s1.p.y + t * s1.dy))


def _quadratic(A, B, C):
    """Real roots of A t^2 + B t + C (A != 0), ascending, with a 'double' flag."""
    disc = B * B - 4 * A * C
    s = disc.sign()
    if s < 0:
        return [], False
    if s == 0:
        return [-B / (2 * A)], True
    r = disc.sqrt()
    t1, t2 = (-B - r) / (2 * A), (-B + r) / (2 * A)
    return ([t1, t2] if t1 < t2 else [t2, t1]), False


def _line_conic(seg, con):
    A, B, C, D, E, F = con.coeffs()
    px, py, dx, dy = seg.p.x, seg.p.y, seg.dx, seg.dy
    a = A * dx * dx + B * dx * dy + C * dy * dy
    b = 2 * A * px * dx + B * (px * dy + py * dx) + 2 * C * py * dy + D * dx + E * dy
    c = con.value(seg.p)
    ts, double = _quadratic(a, b, c)
    return [Point(px + t * dx, py + t * dy) for t in ts], double


def _circle_circle(c1, c2):
    """('points', [P...], tangent) or ('concentric',) or ('same',)."""
    if c1.c == c2.c:
        return ("same",) if c1.r == c2.r else ("concentric",)
    # radical line: subtracting the two equations leaves a line
    A1, _, _, D1, E1, F1 = c1.coeffs()
    _, _, _, D2, E2, F2 = c2.coeffs()
    a, b, c = D1 - D2, E1 - E2, F1 - F2      # a x + b y + c = 0
    # a point on it and its direction
    if not b.is_zero():
        p = Point(0, -c / b)
    else:
        p = Point(-c / a, 0)
    line = _Line(p, (-b, a))
    pts, double = _line_conic(line, c1)
    return ("points", pts, double)


class _Line(object):
    """A carrier line through p with direction d (no piece)."""

    def __init__(self, p, d):
        self.p = p
        self.dx, self.dy = d


def _is_rational_conic(con):
    return all(c.is_rational() for c in con.coeffs())


def _conic_conic(c1, c2):
    """General conic pair through the resultant in y: ('points', [P...]) or ('same',)."""
    if c1.same_carrier(c2):
        return ("same",)
    if not (_is_rational_conic(c1) and _is_rational_conic(c2)):
        raise NotSupported("two conics meet at the roots of a quartic; this version solves it "
                           "exactly only when both have rational equations (centres, axes and "
                           "ratios given as exact rationals)")

    def ypoly(con):
        A, B, C, D, E, F = [x.as_fraction() for x in con.coeffs()]
        return [[F, D, A], [E, B], [C]]

    def clean(p):
        out = list(p)
        while out and out[-1] == 0:
            out.pop()
        return out

    Y1 = [clean(c) for c in ypoly(c1)]
    Y2 = [clean(c) for c in ypoly(c2)]
    R = resultant(Y1, Y2)
    if not R:
        return ("same",)
    pts = []
    for root in real_roots(R):
        X = Num(None, root) if isinstance(root, Fraction) else Num(root, [ZERO, ONE])
        g = ngcd([neval_xpoly(c, X) for c in Y1], [neval_xpoly(c, X) for c in Y2])
        g = nstrip(g)
        if len(g) == 2:
            pts.append(Point(X, -g[0] / g[1]))
        elif len(g) == 3:
            ys, _ = _quadratic(g[2], g[1], g[0])
            pts.extend(Point(X, y) for y in ys)
    return ("points", pts)


def _tangent_at(a, b, pt):
    """Do the carriers of a and b touch at pt (same tangent line)?"""
    def normal(s):
        if isinstance(s, Segment):
            return -s.dy, s.dx
        return s.gradient(pt)
    na, nb = normal(a), normal(b)
    return cross(na[0], na[1], nb[0], nb[1]).is_zero()


# ----------------------------------------------------------------------------
# Overlaps of pieces on one carrier


def _segment_overlap(s1, s2):
    t0, t1 = s1.param(s2.p), s1.param(s2.q)
    lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)
    a = lo if lo > 0 else n(0)
    b = hi if hi < 1 else n(1)
    if a > b:
        return [], []
    pa = Point(s1.p.x + a * s1.dx, s1.p.y + a * s1.dy)
    if a == b:
        return [pa], []
    pb = Point(s1.p.x + b * s1.dx, s1.p.y + b * s1.dy)
    return [], [Segment(pa, pb)]


def _angular_overlap(r1, r2):
    """r1, r2: (start, end) or None for the whole curve. Returns (point_dirs,
    pieces) where pieces are (start, end) pairs or None for the whole curve."""
    if r1 is None and r2 is None:
        return [], [None]
    if r1 is None:
        return [], [r2]
    if r2 is None:
        return [], [r1]
    (s1, e1), (s2, e2) = r1, r2
    starts = []
    if between(s1, e1, s2):
        starts.append(s2)
    if between(s2, e2, s1) and not (starts and _same_dir(starts[0], s1)):
        starts.append(s1)
    dirs, pieces = [], []
    for s in starts:
        end = e1 if turn_le(s, e1, e2) else e2
        if _same_dir(s, end):
            dirs.append(s)
        else:
            pieces.append((s, end))
    return dirs, pieces


def _conic_overlap(a, b):
    ra = None if a.start is None else (a.start, a.end)
    rb = None if b.start is None else (b.start, b.end)
    dirs, pieces = _angular_overlap(ra, rb)
    host = a if isinstance(a, Ellipse) or not isinstance(b, Ellipse) else b
    pts = [host.ray_point(d) for d in dirs]
    out = []
    for piece in pieces:
        if piece is None:
            out.append(a if a.start is None else b)
        elif isinstance(host, Ellipse):
            out.append(Ellipse(host.c, host.major, host.ratio, piece[0], piece[1]))
        elif isinstance(a, Ellipse) or isinstance(b, Ellipse):
            e = a if isinstance(a, Ellipse) else b
            out.append(Ellipse(e.c, e.major, e.ratio, piece[0], piece[1]))
        else:
            out.append(Arc(host.c, host.r, piece[0], piece[1]))
    return pts, out


# ----------------------------------------------------------------------------
# The dispatcher

_RANK = {"point": 0, "segment": 1, "arc": 2, "circle": 3, "ellipse": 4}


def intersect(a, b):
    """The exact intersection of two shapes. Symmetric: intersect(a, b) and
    intersect(b, a) give the same points."""
    if _RANK[a.kind] > _RANK[b.kind]:
        a, b = b, a
    if isinstance(a, Point):
        if isinstance(b, Point):
            return Intersection([a], [False]) if a == b else Intersection()
        return Intersection([a], [False]) if b.on(a) else Intersection(
            notes=["outside"] if b.on_carrier(a) else [])
    if isinstance(a, Segment) and isinstance(b, Segment):
        r = _line_line(a, b)
        if r[0] == "parallel":
            return Intersection(notes=["parallel"])
        if r[0] == "collinear":
            pts, pieces = _segment_overlap(a, b)
            return Intersection(pts, [False] * len(pts), pieces, ["collinear"])
        p = r[1]
        if a.in_piece(p) and b.in_piece(p):
            return Intersection([p], [False])
        return Intersection(notes=["outside"])
    if isinstance(a, Segment):
        pts, double = _line_conic(a, b)
        return _filter(a, b, pts, ["tangent"] if double else [])
    # two conics
    if isinstance(a, Circle) and isinstance(b, Circle):
        r = _circle_circle(a, b)
        if r[0] == "concentric":
            return Intersection(notes=["concentric"])
    elif a.same_carrier(b):
        r = ("same",)
    else:
        r = _conic_conic(a, b)
    if r[0] == "same":
        pts, pieces = _conic_overlap(a, b)
        return Intersection(pts, [False] * len(pts), pieces, ["coincident"])
    return _filter(a, b, r[1], [])


def _filter(a, b, pts, notes):
    kept, tang = [], []
    for p in pts:
        if a.in_piece(p) and b.in_piece(p):
            kept.append(p)
            tang.append(_tangent_at(a, b, p))
    notes = list(notes)
    if pts and not kept:
        notes.append("outside")
    if any(tang):
        notes.append("tangent")
    return Intersection(kept, tang, notes=notes)
