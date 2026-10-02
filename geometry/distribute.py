"""geometry.distribute -- distributions by count and by pitch, exactly (P2-T04,
ADR 0013).

Distributing by count or pitch is most of the tedium the agent is meant to
remove. Every point is exact (geometry.exact): a pitch that does not divide a
length leaves a remainder that is computed and reported, never absorbed into
the last gap; positions on a circle use the exact cosines of rational angles.

- along(segment, count=..., pitch=..., ends=...)
- on_circle(circle, count=..., pitch_deg=..., start=(1, 0))
- grid(origin, cols, rows, pitch_x, pitch_y)
- grid_in(lower_left, upper_right, cols, rows, ends=...)

`ends` says what happens at the ends of a run (for `along` and `grid_in`):

- "include"  the first and the last point sit on the two ends (count >= 2);
- "exclude"  the points are spaced so that the gaps at the ends equal the
             gaps between them (n points, n + 1 equal gaps);
- "start"    (pitch patterns) the first point is on the start, the leftover is
             at the far end;
- "centred"  (pitch patterns) the pattern is centred, the leftover split
             equally between the two ends.

Each call returns a Distribution: the points, the pitch, the leftover and the
rule used, so a report can say exactly what was done.

Standard library only (CORE package).
"""

from fractions import Fraction

from geometry.exact import Num, pnorm, _isolate, ZERO, ONE
from geometry.primitives import Point, Segment, Circle, Arc


class DistributionRefused(ValueError):
    """The distribution cannot be made as asked; the message says why."""


def n(v):
    return Num.of(v)


class Distribution(object):
    """points: in order; pitch: the distance between neighbours (an angle in
    degrees for a circle); leftover: what the pattern leaves unused at the ends
    (zero when it fills the run exactly); rule: the `ends` rule applied."""

    def __init__(self, points, pitch, leftover, rule):
        self.points, self.pitch, self.leftover, self.rule = points, pitch, leftover, rule

    def __len__(self):
        return len(self.points)

    def __repr__(self):
        return "Distribution(%d points, pitch %s, leftover %s, %s)" % (
            len(self.points), self.pitch.decimal(6), self.leftover.decimal(6), self.rule)


def _count(value, what="count"):
    if isinstance(value, bool) or not isinstance(value, int):
        raise DistributionRefused("the %s must be a whole number, not %r" % (what, value))
    if value < 1:
        raise DistributionRefused("the %s must be at least 1, not %d" % (what, value))
    return value


def _length(seg):
    return (seg.dx * seg.dx + seg.dy * seg.dy).sqrt()


def _at(seg, t):
    return Point(seg.p.x + t * seg.dx, seg.p.y + t * seg.dy)


def along(seg, count=None, pitch=None, ends=None):
    """Points along a segment, from p towards q.

    count only:      ends "include" (default) or "exclude";
    pitch only:      as many as fit from the start: ends "start" (default) or
                     "centred";
    count and pitch: exactly `count` points at `pitch`: ends "start" (default)
                     or "centred"; refused when they do not fit."""
    if not isinstance(seg, Segment):
        raise DistributionRefused("a distribution along needs a segment, not a %s" % seg.kind)
    L = _length(seg)
    if count is not None:
        count = _count(count)
    if pitch is not None:
        pitch = n(pitch)
        if pitch.sign() <= 0:
            raise DistributionRefused("the pitch must be greater than zero")
    if count is None and pitch is None:
        raise DistributionRefused("say how many (count) or how far apart (pitch)")
    if pitch is None:
        ends = ends or "include"
        if ends == "include":
            if count < 2:
                raise DistributionRefused("one point cannot sit on both ends: use at least 2, "
                                          'or ends "exclude" to centre a single point')
            ts = [Fraction(i, count - 1) for i in range(count)]
            return Distribution([_at(seg, t) for t in ts], L / (count - 1), n(0), ends)
        if ends == "exclude":
            ts = [Fraction(i + 1, count + 1) for i in range(count)]
            return Distribution([_at(seg, t) for t in ts], L / (count + 1), n(0), ends)
        raise DistributionRefused('by count, the ends are "include" or "exclude", not "%s"'
                                  % ends)
    ends = ends or "start"
    if ends not in ("start", "centred"):
        raise DistributionRefused('by pitch, the ends are "start" or "centred", not "%s"' % ends)
    if count is None:
        count = (L / pitch).floor() + 1
    span = pitch * (count - 1)
    leftover = L - span
    if leftover.sign() < 0:
        raise DistributionRefused("%d points at a pitch of %s need %s, and the segment is only "
                                  "%s long" % (count, pitch.decimal(6), span.decimal(6),
                                               L.decimal(6)))
    first = n(0) if ends == "start" else leftover / 2
    ts = [(first + pitch * i) / L for i in range(count)]
    return Distribution([_at(seg, t) for t in ts], pitch, leftover, ends)


# ---------------------------------------------------------------- the circle

def _cos_turn(b):
    """cos(2 pi / b) exactly: the largest real root of the minimal polynomial of
    2 cos(2 pi / b), built from the cyclotomic polynomial Phi_b."""
    if b == 1:
        return n(1)
    if b == 2:
        return n(-1)
    if b == 3:
        return n(Fraction(-1, 2))
    if b == 4:
        return n(0)
    if b == 6:
        return n(Fraction(1, 2))
    phi = _cyclotomic(b)                      # integer coefficients, lowest first
    m = (len(phi) - 1) // 2                   # Phi_b(z) = z^m * sum c_j (z^j + z^-j)
    # z^j + z^-j = P_j(y), y = z + 1/z: P_0 = 2, P_1 = y, P_j = y P_{j-1} - P_{j-2}
    P = [[Fraction(2)], [Fraction(0), Fraction(1)]]
    for j in range(2, m + 1):
        nxt = [Fraction(0)] + P[j - 1]
        prev = P[j - 2] + [Fraction(0)] * (len(nxt) - len(P[j - 2]))
        P.append([a - b2 for a, b2 in zip(nxt, prev)])
    psi = [Fraction(0)] * (m + 1)
    for j in range(m + 1):
        c = Fraction(phi[m + j])
        term = P[j] if j else [Fraction(1)]          # the middle coefficient counts once
        for i, a in enumerate(term):
            psi[i] += c * a
    # x = y / 2: substitute y = 2x
    poly = pnorm([c * (2 ** i) for i, c in enumerate(psi)])
    fields = _isolate(poly)
    top = fields[0]
    for f in fields[1:]:
        if f.lo > top.lo:
            top = f
    return Num(top, [ZERO, ONE])


def _cyclotomic(b):
    """Phi_b with integer coefficients, lowest degree first."""
    poly = [-1] + [0] * (b - 1) + [1]               # z^b - 1
    for d in range(1, b):
        if b % d == 0:
            poly = _int_div(poly, _cyclotomic(d))
    return poly


def _int_div(a, b):
    a = list(a)
    out = [0] * (len(a) - len(b) + 1)
    while len(a) >= len(b):
        c = a[-1] // b[-1]
        k = len(a) - len(b)
        out[k] = c
        for i, y in enumerate(b):
            a[i + k] -= c * y
        while a and a[-1] == 0:
            a.pop()
        if not a:
            break
    return out


def _turn(a, b):
    """(cos, sin) of the angle a/b of a full turn, exactly."""
    from math import gcd
    g = gcd(a, b)
    a, b = a // g, b // g
    c1 = _cos_turn(b)
    # cos(a x) by Chebyshev: T_0 = 1, T_1 = c, T_k = 2 c T_{k-1} - T_{k-2}
    t0, t1 = n(1), c1
    if a == 0:
        cos = n(1)
    else:
        for _ in range(a - 1):
            t0, t1 = t1, 2 * c1 * t1 - t0
        cos = t1
    sin = (1 - cos * cos).sqrt()
    if Fraction(a, b) > Fraction(1, 2):               # the lower half: sin is negative
        sin = -sin
    return cos, sin


def on_circle(circle, count=None, pitch_deg=None, start=(1, 0)):
    """Points on a circle, counter-clockwise from the direction `start`.

    count only:      equally spaced round the whole circle;
    pitch only:      round the whole circle; the pitch must divide 360 degrees;
    count and pitch: `count` points at `pitch_deg`, from start; refused when
                     they would go round more than once.
    The pitch is in degrees, a rational number (7.5 is fine, as "7.5")."""
    if not isinstance(circle, Circle) or isinstance(circle, Arc):
        raise DistributionRefused("a distribution on a circle needs a full circle")
    if count is not None:
        count = _count(count)
    if pitch_deg is not None:
        pitch = Num.of(pitch_deg)
        if not pitch.is_rational() or pitch.sign() <= 0:
            raise DistributionRefused("the angular pitch must be a positive exact number of "
                                      "degrees")
        pitch = pitch.as_fraction()
    if count is None and pitch_deg is None:
        raise DistributionRefused("say how many (count) or how far apart (pitch_deg)")
    if pitch_deg is None:
        pitch = Fraction(360, count)
    if count is None:
        whole = Fraction(360) / pitch
        if whole.denominator != 1:
            raise DistributionRefused("a pitch of %s degrees does not go round the circle a "
                                      "whole number of times; give the count as well"
                                      % _deg(pitch))
        count = int(whole)
    if pitch * (count - 1) >= 360:
        raise DistributionRefused("%d points at %s degrees go round more than once"
                                  % (count, _deg(pitch)))
    ux, uy = n(start[0]), n(start[1])
    L = (ux * ux + uy * uy).sqrt()
    if L.is_zero():
        raise DistributionRefused("the start direction is the zero vector")
    ux, uy = ux / L, uy / L
    pts = []
    for k in range(count):
        turn = pitch * k / 360
        c, s = _turn(turn.numerator, turn.denominator)
        dx, dy = ux * c - uy * s, ux * s + uy * c
        pts.append(Point(circle.c.x + circle.r * dx, circle.c.y + circle.r * dy))
    left = Fraction(360) - pitch * count if pitch_deg is not None else Fraction(0)
    return Distribution(pts, n(pitch), n(left if left > 0 else 0), "circle")


def _deg(q):
    return str(q.numerator) if q.denominator == 1 else "%s" % float(q)


# ---------------------------------------------------------------- grids

def grid(origin, cols, rows, pitch_x, pitch_y):
    """cols x rows points, row by row from the origin, at the given pitches
    (negative pitches run left or down)."""
    cols, rows = _count(cols, "number of columns"), _count(rows, "number of rows")
    ox, oy = (origin.x, origin.y) if isinstance(origin, Point) else (n(origin[0]), n(origin[1]))
    px, py = n(pitch_x), n(pitch_y)
    if (cols > 1 and px.is_zero()) or (rows > 1 and py.is_zero()):
        raise DistributionRefused("a zero pitch puts points on top of each other")
    pts = [Point(ox + px * i, oy + py * j) for j in range(rows) for i in range(cols)]
    return Distribution(pts, px, n(0), "grid")


def grid_in(lower_left, upper_right, cols, rows, ends="include"):
    """cols x rows points filling a rectangle, row by row from the lower left."""
    a = lower_left if isinstance(lower_left, Point) else Point(*lower_left)
    b = upper_right if isinstance(upper_right, Point) else Point(*upper_right)
    if not (a.x < b.x and a.y < b.y):
        raise DistributionRefused("the rectangle must run from its lower-left to its "
                                  "upper-right corner")
    xs = [p.x for p in along(Segment(a, Point(b.x, a.y)), count=cols, ends=ends).points]
    ys = [p.y for p in along(Segment(a, Point(a.x, b.y)), count=rows, ends=ends).points]
    pts = [Point(x, y) for y in ys for x in xs]
    return Distribution(pts, xs[1] - xs[0] if len(xs) > 1 else n(0), n(0), ends)
