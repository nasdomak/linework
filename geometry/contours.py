"""geometry.contours -- closed contours from loose pieces, exactly (P2-T03,
ADR 0012).

A contour closes exactly, not almost. Hatches on open contours are a defect the
whole drawing inherits, so this module never closes anything quietly:

- two piece ends meet only when their exact coordinates are equal (ADR 0010:
  no tolerance in geometry);
- loose segments, arcs and elliptical arcs are chained into closed contours
  where every junction joins exactly two ends;
- an open chain is reported as open, with its two loose ends, and every loose
  end is paired with the nearest other loose end and the exact gap between
  them -- so "nearly closed by a thousandth of a millimetre" is visible and
  named, not hidden;
- a junction of three or more ends (a branch) and a piece given twice are
  reported, never resolved by guessing which way the contour goes.

Closure is guaranteed by construction upstream: the solver's operations
(geometry.ops) hand neighbouring pieces the very same exact point, so a contour
built by them closes with zero gap, irrational corners included.

Standard library only (CORE package).
"""

from geometry.primitives import Segment


def ends(piece):
    """The two end points of an open piece, in its own direction; None for a
    full circle or ellipse (closed on its own)."""
    if isinstance(piece, Segment):
        return piece.p, piece.q
    if getattr(piece, "start", None) is None:
        return None
    return piece.endpoints()


class Contour(object):
    """A chain of pieces, each with `reversed` True when it is walked from its
    second end to its first. `closed` says whether the last end is the first."""

    def __init__(self, steps, closed):
        self.steps = steps                  # [(piece, reversed)]
        self.closed = closed

    @property
    def pieces(self):
        return [p for p, _ in self.steps]

    def vertices(self):
        """The junction points in walking order (the start once, for a closed one)."""
        out = []
        for piece, rev in self.steps:
            e = ends(piece)
            if e is None:
                return []
            a, b = (e[1], e[0]) if rev else e
            if not out:
                out.append(a)
            out.append(b)
        if self.closed and len(out) > 1:
            out.pop()
        return out

    @property
    def first(self):
        v = self.vertices()
        return v[0] if v else None

    @property
    def last(self):
        e = ends(self.steps[-1][0])
        if e is None:
            return None
        return e[0] if self.steps[-1][1] else e[1]

    def __repr__(self):
        return "Contour(%s, %d pieces)" % ("closed" if self.closed else "OPEN", len(self.steps))


class Gap(object):
    """Two loose ends and the exact distance between them."""

    def __init__(self, a, b):
        self.a, self.b = a, b
        dx, dy = b.x - a.x, b.y - a.y
        self.distance = (dx * dx + dy * dy).sqrt()

    def __repr__(self):
        return "Gap(%s to %s: %s)" % (self.a.text(), self.b.text(), self.distance.decimal(6))


class Report(object):
    """closed: closed contours; open: open chains; branches: points where three
    or more ends meet (with the pieces there left out of any contour); gaps:
    each loose end with its nearest other loose end; duplicates: pieces given
    twice (the second copy is ignored)."""

    def __init__(self):
        self.closed, self.open, self.branches, self.gaps, self.duplicates = [], [], [], [], []

    @property
    def all_closed(self):
        return bool(self.closed) and not (self.open or self.branches or self.duplicates)

    def describe(self):
        lines = ["%d closed contour(s), %d open chain(s)" % (len(self.closed), len(self.open))]
        for c in self.open:
            lines.append("open: from %s to %s" % (c.first.text(), c.last.text()))
        for g in self.gaps:
            lines.append("gap of %s mm between %s and %s"
                         % (g.distance.decimal(6), g.a.text(), g.b.text()))
        for p in self.branches:
            lines.append("branch: three or more ends meet at %s" % p.text())
        for d in self.duplicates:
            lines.append("given twice: %r" % (d,))
        return "\n".join(lines)


class _Vertices(object):
    """Exact point registry: rational points by key, the rest by exact search."""

    def __init__(self):
        self.points, self._by_key = [], {}

    def index(self, p):
        if p.x.is_rational() and p.y.is_rational():
            key = (p.x.as_fraction(), p.y.as_fraction())
            i = self._by_key.get(key)
            if i is None:
                i = self._by_key[key] = len(self.points)
                self.points.append(p)
            return i
        for i, q in enumerate(self.points):
            if not (q.x.is_rational() and q.y.is_rational()) and q == p:
                return i
        self.points.append(p)
        return len(self.points) - 1


def _same_piece(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, Segment):
        return a == b
    ea, eb = ends(a), ends(b)
    if ea is None or eb is None:
        return ea is None and eb is None and a.c == b.c and a.same_carrier(b)
    return a.c == b.c and a.same_carrier(b) and ea[0] == eb[0] and ea[1] == eb[1]


def find_contours(pieces):
    """Chain loose pieces into contours. Returns a Report; nothing is closed that
    does not close exactly, and nothing is dropped without being named."""
    rep = Report()
    kept = []
    for p in pieces:
        if any(_same_piece(p, k) for k in kept):
            rep.duplicates.append(p)
        else:
            kept.append(p)
    reg = _Vertices()
    edges = []                                   # (piece, i, j)
    for p in kept:
        e = ends(p)
        if e is None:
            rep.closed.append(Contour([(p, False)], True))
            continue
        edges.append((p, reg.index(e[0]), reg.index(e[1])))
    adj = {}
    for k, (_, i, j) in enumerate(edges):
        adj.setdefault(i, []).append(k)
        adj.setdefault(j, []).append(k)
    # connected components of the edge graph
    seen, comps = set(), []
    for k in range(len(edges)):
        if k in seen:
            continue
        stack, comp = [k], []
        seen.add(k)
        while stack:
            e = stack.pop()
            comp.append(e)
            for v in edges[e][1:]:
                for f in adj[v]:
                    if f not in seen:
                        seen.add(f)
                        stack.append(f)
        comps.append(sorted(comp))
    loose = []
    for comp in comps:
        verts = set()
        for e in comp:
            verts.update(edges[e][1:])
        degree = {v: len(adj[v]) for v in verts}
        branch = [v for v in verts if degree[v] > 2]
        if branch:
            rep.branches.extend(reg.points[v] for v in sorted(branch))
            continue
        starts = [v for v in sorted(verts) if degree[v] == 1]
        start = starts[0] if starts else edges[comp[0]][1]
        steps, used, v = [], set(), start
        while True:
            nxt = [e for e in adj[v] if e not in used]
            if not nxt:
                break
            e = nxt[0]
            used.add(e)
            piece, i, j = edges[e]
            if i == v:
                steps.append((piece, False))
                v = j
            else:
                steps.append((piece, True))
                v = i
        contour = Contour(steps, closed=not starts)
        if contour.closed:
            rep.closed.append(contour)
        else:
            rep.open.append(contour)
            loose.extend([contour.first, contour.last])
    # every loose end, with the nearest other loose end
    for i, a in enumerate(loose):
        best = None
        for j, b in enumerate(loose):
            if i == j:
                continue
            g = Gap(a, b)
            if best is None or g.distance < best.distance:
                best = g
        if best is not None and not any(
                (g.a == best.b and g.b == best.a) for g in rep.gaps):
            rep.gaps.append(best)
    return rep
