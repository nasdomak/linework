"""geometry.exact -- exact real numbers for the solver (P2-T01, ADR 0010).

A drawing needs square roots: a line meets a circle at 1 + sqrt(3), two ellipses
meet at roots of a quartic. A float would store those as 2.7320508075688772 and
the error would travel into every later construction. This module never rounds.
Every number is either a Fraction or an exact real algebraic number: an element
g(a) of the field Q(a), where a is the one real root of a square-free polynomial
f with rational coefficients inside a rational isolating interval.

What the module guarantees:

- `+ - * /` and `sqrt` are exact. Mixing numbers of two different fields builds
  their common field (a primitive element) exactly.
- `==`, `<`, `sign()` are decided exactly, never with a tolerance: zero is
  recognised by a gcd, a non-zero sign by refining the interval until it is
  certain. Two numbers that are equal compare equal, however they were built.
- Decimals are produced only at the very end, on request, correctly rounded
  (`decimal(digits)`), and floats only by `float()`.

Floats are refused as input: 0.1 is not one tenth. Numbers enter as int,
Fraction or a decimal string ("0.1").

Standard library only (CORE package).
"""

from fractions import Fraction
from math import isqrt

ZERO = Fraction(0)
ONE = Fraction(1)


class NotExact(TypeError):
    """A float, or anything else that is not an exact number."""


def q(value):
    """An exact rational: int, Fraction or decimal string. Floats are refused."""
    if isinstance(value, bool):
        raise NotExact("a boolean is not a number")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value.strip())
    if isinstance(value, float):
        raise NotExact("%r is a float and floats are not exact; give it as the string '%r' "
                       "or as a Fraction" % (value, value))
    raise NotExact("%r is not an exact number" % (value,))


# ----------------------------------------------------------------------------
# Polynomials over Q: lists of Fractions, lowest degree first, no trailing zeros.
# The zero polynomial is [].


def pnorm(p):
    p = [c if isinstance(c, Fraction) else q(c) for c in p]
    while p and p[-1] == 0:
        p.pop()
    return p


def padd(a, b):
    n = max(len(a), len(b))
    return pnorm([(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)])


def psub(a, b):
    n = max(len(a), len(b))
    return pnorm([(a[i] if i < len(a) else 0) - (b[i] if i < len(b) else 0) for i in range(n)])


def pmul(a, b):
    if not a or not b:
        return []
    out = [ZERO] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                out[i + j] += x * y
    return pnorm(out)


def pscale(a, c):
    return pnorm([x * c for x in a])


def pdivmod(a, b):
    if not b:
        raise ZeroDivisionError("division by the zero polynomial")
    a = list(a)
    out = [ZERO] * max(len(a) - len(b) + 1, 0)
    lead = b[-1]
    while len(a) >= len(b) and a:
        c = a[-1] / lead
        k = len(a) - len(b)
        out[k] = c
        for i, y in enumerate(b):
            a[i + k] -= c * y
        a = pnorm(a)
    return pnorm(out), a


def pmod(a, b):
    return pdivmod(a, b)[1]


def pmonic(a):
    return [x / a[-1] for x in a] if a else []


def pgcd(a, b):
    a, b = pnorm(a), pnorm(b)
    while b:
        a, b = b, pmod(a, b)
    return pmonic(a)


def pderiv(a):
    return pnorm([a[i] * i for i in range(1, len(a))])


def peval(a, x):
    acc = ZERO
    for c in reversed(a):
        acc = acc * x + c
    return acc


def psqfree(a):
    """The square-free part: the same roots, each once."""
    a = pnorm(a)
    if len(a) <= 2:
        return pmonic(a)
    g = pgcd(a, pderiv(a))
    return pmonic(pdivmod(a, g)[0])


def pdeg(a):
    return len(a) - 1


def _imul(a, b):
    ps = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return min(ps), max(ps)


def pinterval(a, lo, hi):
    """Exact bounds of a(x) for every x in [lo, hi] (interval Horner)."""
    acc = (ZERO, ZERO)
    for c in reversed(a):
        m = _imul(acc, (lo, hi))
        acc = (m[0] + c, m[1] + c)
    return acc


# ----------------------------------------------------------------------------
# Real roots: Sturm sequences and isolation by bisection.


def sturm(p):
    seq = [pnorm(p), pderiv(p)]
    while seq[-1] and len(seq[-1]) > 1:
        r = pscale(pmod(seq[-2], seq[-1]), -1)
        if not r:
            break
        seq.append(r)
    return [s for s in seq if s]


def _changes(seq, x):
    signs = [s for s in (peval(p, x) for p in seq) if s != 0]
    return sum(1 for i in range(1, len(signs)) if (signs[i] > 0) != (signs[i - 1] > 0))


def count_roots(seq, lo, hi):
    """Distinct real roots of the square-free polynomial seq[0] in (lo, hi]."""
    return _changes(seq, lo) - _changes(seq, hi)


def _sgn(x):
    return (x > 0) - (x < 0)


def simplest_between(lo, hi):
    """The fraction with the smallest denominator in [lo, hi]."""
    fl = lo.numerator // lo.denominator
    if fl == lo:
        return Fraction(fl)
    if fl + 1 <= hi:
        return Fraction(fl + 1)
    return fl + 1 / simplest_between(1 / (hi - fl), 1 / (lo - fl))


def _bound(p):
    lead = abs(p[-1])
    return 1 + max(abs(c) / lead for c in p[:-1]) if len(p) > 1 else ONE


def _integer_lead(p):
    den = 1
    for c in p:
        den = den * c.denominator // _gcd(den, c.denominator)
    ints = [int(c * den) for c in p]
    g = 0
    for c in ints:
        g = _gcd(g, abs(c))
    return abs(ints[-1] // g) if g else 1


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def real_roots(p):
    """Every real root of p, ascending: a Fraction when it is rational, otherwise
    a Field whose generator is that root."""
    p = psqfree(pnorm(p))
    if len(p) <= 1:
        return []
    if len(p) == 2:
        return [-p[0] / p[1]]
    seq = sturm(p)
    b = _bound(p)
    lead = _integer_lead(p)
    width = Fraction(1, 2 * lead * lead)
    exact, isolated = set(), []
    work = [(-b, b)]
    while work:
        lo, hi = work.pop()
        n = count_roots(seq, lo, hi)
        if n == 0:
            continue
        if peval(p, hi) == 0:
            exact.add(hi)
            if n == 1:
                continue
        elif n == 1 and peval(p, lo) != 0:
            # refine until a rational root, if it is one, is the simplest fraction here
            while hi - lo > width:
                mid = (lo + hi) / 2
                v = peval(p, mid)
                if v == 0:
                    lo = hi = mid
                    break
                if _sgn(v) == _sgn(peval(p, lo)):
                    lo = mid
                else:
                    hi = mid
            if lo == hi:
                exact.add(lo)
                continue
            s = simplest_between(lo, hi)
            if peval(p, s) == 0:
                exact.add(s)
            else:
                isolated.append((lo, hi))
            continue
        mid = (lo + hi) / 2
        work.append((lo, mid))
        work.append((mid, hi))
    rest = p
    for r in exact:
        rest = pdivmod(rest, [-r, ONE])[0]
    out = sorted(exact) + [Field(rest, lo, hi) for lo, hi in isolated]
    return sorted(out, key=_root_key)


def _root_key(r):
    return r if isinstance(r, Fraction) else r.lo


# ----------------------------------------------------------------------------
# Resultants over Q[x]: polynomials (in a main variable) whose coefficients are
# polynomials in x. Sylvester matrix, fraction-free Bareiss elimination.


def resultant(P, Q):
    """Res(P, Q) in the main variable; P and Q are lists (lowest first) of
    polynomials in x. Returns a polynomial in x."""
    P = list(P)
    Q = list(Q)
    while P and not P[-1]:
        P.pop()
    while Q and not Q[-1]:
        Q.pop()
    if not P or not Q:
        return []
    m, n = len(P) - 1, len(Q) - 1
    size = m + n
    if size == 0:
        return [ONE]
    M = []
    for i in range(n):
        row = [[] for _ in range(size)]
        for j, c in enumerate(reversed(P)):
            row[i + j] = list(c)
        M.append(row)
    for i in range(m):
        row = [[] for _ in range(size)]
        for j, c in enumerate(reversed(Q)):
            row[i + j] = list(c)
        M.append(row)
    sign = 1
    prev = [ONE]
    for k in range(size - 1):
        if not M[k][k]:
            for i in range(k + 1, size):
                if M[i][k]:
                    M[k], M[i] = M[i], M[k]
                    sign = -sign
                    break
            else:
                return []
        for i in range(k + 1, size):
            for j in range(k + 1, size):
                num = psub(pmul(M[i][j], M[k][k]), pmul(M[i][k], M[k][j]))
                quo, rem = pdivmod(num, prev)
                assert not rem, "Bareiss division must be exact"
                M[i][j] = quo
        prev = M[k][k]
    return pscale(M[size - 1][size - 1], sign)


# ----------------------------------------------------------------------------
# Fields Q(a): a is the only root of `poly` in the open interval (lo, hi).


class Field(object):
    """Q(a) for one real algebraic a. `poly` is square-free and may be reducible;
    it is split lazily, keeping the factor that holds a, whenever a gcd shows a
    factor. The interval only ever shrinks."""

    __slots__ = ("poly", "lo", "hi", "_slo", "_seq", "parents")

    def __init__(self, poly, lo, hi):
        self.poly = pmonic(pnorm(poly))
        self.lo, self.hi = Fraction(lo), Fraction(hi)
        self._slo = _sgn(peval(self.poly, self.lo))
        self._seq = None
        self.parents = []      # [(subfield, image of its generator in this field)]
        assert self._slo != 0 and _sgn(peval(self.poly, self.hi)) == -self._slo, \
            "the interval must isolate a simple root"

    @property
    def degree(self):
        return len(self.poly) - 1

    def refine(self):
        mid = (self.lo + self.hi) / 2
        v = _sgn(peval(self.poly, mid))
        assert v != 0, "the generator of a field is irrational"
        if v == self._slo:
            self.lo = mid
        else:
            self.hi = mid

    def holds_root_of(self, h):
        """Is the generator a root of h? (h has no root at the endpoints.)"""
        if len(h) <= 1:
            return False
        if _sgn(peval(h, self.lo)) == 0 or _sgn(peval(h, self.hi)) == 0:
            self.refine()
            return self.holds_root_of(h)
        return count_roots(sturm(psqfree(h)), self.lo, self.hi) == 1

    def split(self, h):
        """h divides poly: keep the factor that holds the generator."""
        if self.holds_root_of(h):
            self.poly = pmonic(h)
        else:
            self.poly = pmonic(pdivmod(self.poly, h)[0])
        self._slo = _sgn(peval(self.poly, self.lo))

    def interval(self):
        return self.lo, self.hi

    def __repr__(self):
        return "Field(deg %d in (%s, %s))" % (self.degree, float(self.lo), float(self.hi))


_JOINS = {}


def _sqrt_bounds(x, bits):
    """Rationals lo <= sqrt(x) <= hi for x >= 0, within about 2**-bits."""
    s = 1 << bits
    n = x * s * s
    a = isqrt(n.numerator // n.denominator)
    lo = Fraction(a, s)
    c = -((-n.numerator) // n.denominator)
    b = isqrt(c)
    if b * b < c:
        b += 1
    return lo, Fraction(b, s)


def _extend(F, coeffs, enclose):
    """Adjoin to F the real root b of P(y) = sum coeffs[j] y^j (coeffs: polys in
    the generator of F, already reduced), where enclose(step) gives shrinking
    rational intervals around b. Returns (G, a_in_G, b_in_G)."""
    f = F.poly
    n = len(coeffs) - 1
    for k in (1, -1, 2, -2, 3, -3, 5, -5, 7, -7, 11, -11, 13, -13):
        K = Fraction(k)
        # Q(x, t) = sum_j p_j(t) (x - K t)^j, as a polynomial in t with x-poly coefficients
        Qt = {}
        for j, pj in enumerate(coeffs):
            # (x - K t)^j = sum_i C(j,i) x^(j-i) (-K)^i t^i
            for i in range(j + 1):
                xi = [ZERO] * (j - i) + [Fraction(_binom(j, i)) * (-K) ** i]
                for d, c in enumerate(pj):
                    if c:
                        Qt[i + d] = padd(Qt.get(i + d, []), pscale(xi, c))
        top = max(Qt) if Qt else 0
        Qlist = [Qt.get(d, []) for d in range(top + 1)]
        flist = [[c] if c else [] for c in f]
        N = resultant(flist, Qlist)
        Nsf = psqfree(N)
        if len(Nsf) - 1 == F.degree * n:
            break
    else:
        raise ArithmeticError("no primitive element found")
    candidates = real_roots(Nsf)
    step = 0
    while True:
        blo, bhi = enclose(step)
        alo, ahi = F.lo, F.hi
        glo = blo + min(K * alo, K * ahi)
        ghi = bhi + max(K * alo, K * ahi)
        alive = []
        for c in candidates:
            if isinstance(c, Fraction):
                if glo <= c <= ghi:
                    alive.append(c)
            elif not (c.hi < glo or c.lo > ghi):
                alive.append(c)
        if len(alive) == 1:
            break
        candidates = alive
        for c in candidates:
            if not isinstance(c, Fraction):
                c.refine()
        F.refine()
        step += 1
    G = alive[0]
    assert not isinstance(G, Fraction), "a primitive element over an irrational field is irrational"
    gamma = Num(G, [ZERO, ONE])
    # a is the one common root in t of f(t) and P(gamma - K t, t)
    Qn = {}
    for j, pj in enumerate(coeffs):
        for i in range(j + 1):
            base = Num(None, Fraction(_binom(j, i)) * (-K) ** i) * _npow(gamma, j - i)
            for d, c in enumerate(pj):
                if c:
                    Qn[i + d] = Qn.get(i + d, Num(None, ZERO)) + base * Num(None, c)
    top = max(Qn)
    Qpoly = [Qn.get(d, Num(None, ZERO)) for d in range(top + 1)]
    fpoly = [Num(None, c) for c in f]
    g = ngcd(fpoly, Qpoly)
    assert len(g) == 2, "the common root must be unique"
    a_in_G = -g[0] / g[1]
    b_in_G = gamma - Num(None, K) * a_in_G
    G.parents.append((F, a_in_G))
    return G, a_in_G, b_in_G


def _binom(n, k):
    out = 1
    for i in range(k):
        out = out * (n - i) // (i + 1)
    return out


def _npow(x, e):
    out = Num(None, ONE)
    for _ in range(e):
        out = out * x
    return out


def _join(F1, F2):
    key = (id(F1), id(F2))
    hit = _JOINS.get(key)
    if hit is not None and hit[0] is F1 and hit[1] is F2:
        return hit[2:]

    def enclose(step):
        if step:
            F2.refine()
        return F2.lo, F2.hi

    G, a1, a2 = _extend(F1, [[c] if c else [] for c in F2.poly], enclose)
    G.parents.append((F2, a2))
    _JOINS[key] = (F1, F2, G, a1, a2)
    return G, a1, a2


def _lift(a, T, depth=0):
    """a (a Num) written in the field T, when T is known to contain a's field;
    None when it is not known to."""
    if a.F is None or a.F is T:
        return a
    if depth > 12:
        return None
    for sub, image in T.parents:
        b = _lift(a, sub, depth + 1)
        if b is not None:
            return b if b.F is None else _embed(b._poly(), image)
    return None


def _embed(coeffs, image):
    acc = Num(None, ZERO)
    for c in reversed(coeffs):
        acc = acc * image + Num(None, c)
    return acc


# ----------------------------------------------------------------------------
# Num: an exact real number.


class Num(object):
    """A rational (F is None, c a Fraction) or g(a) in Q(a) (c a polynomial)."""

    __slots__ = ("F", "c")
    __hash__ = None

    def __init__(self, F, c):
        if F is None:
            if isinstance(c, list):
                c = pnorm(c)
                c = c[0] if c else ZERO
            self.F, self.c = None, q(c)
            return
        g = pmod(pnorm(c), F.poly)
        if len(g) <= 1:
            self.F, self.c = None, (g[0] if g else ZERO)
        else:
            self.F, self.c = F, g

    # -- construction and coercion
    @staticmethod
    def of(value):
        return value if isinstance(value, Num) else Num(None, q(value))

    def _poly(self):
        if self.F is None:
            return [self.c] if self.c else []
        return pmod(self.c, self.F.poly)

    def _settle(self):
        """Re-reduce after the field was split; may become rational."""
        if self.F is not None:
            g = pmod(self.c, self.F.poly)
            if len(g) <= 1:
                self.F, self.c = None, (g[0] if g else ZERO)
            else:
                self.c = g
        return self

    def is_rational(self):
        self._settle()
        return self.F is None

    def as_fraction(self):
        if not self.is_rational():
            raise ValueError("%s is irrational" % self)
        return self.c

    # -- exact tests
    def is_zero(self):
        self._settle()
        if self.F is None:
            return self.c == 0
        g = self.c
        h = pgcd(self.F.poly, g)
        if len(h) <= 1:
            return False
        self.F.split(h)
        self._settle()
        return self.F is None and self.c == 0

    def sign(self):
        if self.is_zero():
            return 0
        if self.F is None:
            return _sgn(self.c)
        while True:
            lo, hi = pinterval(self.c, self.F.lo, self.F.hi)
            if lo > 0:
                return 1
            if hi < 0:
                return -1
            self.F.refine()
            self._settle()
            if self.F is None:
                return _sgn(self.c)

    def interval(self):
        self._settle()
        if self.F is None:
            return self.c, self.c
        return pinterval(self.c, self.F.lo, self.F.hi)

    def refine(self):
        if self.F is not None:
            self.F.refine()

    # -- arithmetic
    @staticmethod
    def _pair(a, b):
        a, b = Num.of(a)._settle(), Num.of(b)._settle()
        if a.F is None or b.F is None or a.F is b.F:
            F = a.F or b.F
            return F, a._poly(), b._poly()
        lb = _lift(b, a.F)
        if lb is not None and (lb.F is None or lb.F is a.F):
            return a.F, a._poly(), lb._poly()
        la = _lift(a, b.F)
        if la is not None and (la.F is None or la.F is b.F):
            return b.F, la._poly(), b._poly()
        G, img_a, img_b = _join(a.F, b.F)
        ea = _embed(a.c, img_a)
        eb = _embed(b.c, img_b)
        if ea.F is None or eb.F is None or ea.F is eb.F:
            return ea.F or eb.F, ea._poly(), eb._poly()
        return Num._pair(ea, eb)

    def __add__(self, other):
        F, a, b = Num._pair(self, other)
        return Num(F, padd(a, b))

    __radd__ = __add__

    def __neg__(self):
        return Num(self.F, pscale(self._poly(), -1)) if self.F else Num(None, -self.c)

    def __sub__(self, other):
        F, a, b = Num._pair(self, other)
        return Num(F, psub(a, b))

    def __rsub__(self, other):
        return Num.of(other) - self

    def __mul__(self, other):
        F, a, b = Num._pair(self, other)
        if F is None:
            return Num(None, (a[0] if a else ZERO) * (b[0] if b else ZERO))
        return Num(F, pmod(pmul(a, b), F.poly))

    __rmul__ = __mul__

    def inverse(self):
        if self.is_zero():
            raise ZeroDivisionError("division by an exact zero")
        if self.F is None:
            return Num(None, 1 / self.c)
        f, g = self.F.poly, self.c
        # extended Euclid: s*g + t*f = 1
        r0, r1, s0, s1 = f, g, [], [ONE]
        while len(r1) > 1:
            quo, rem = pdivmod(r0, r1)
            r0, r1 = r1, rem
            s0, s1 = s1, psub(s0, pmul(quo, s1))
        return Num(self.F, pscale(s1, 1 / r1[0]))

    def __truediv__(self, other):
        return self * Num.of(other).inverse()

    def __rtruediv__(self, other):
        return Num.of(other) * self.inverse()

    def sqrt(self):
        """The non-negative square root, exactly."""
        s = self.sign()
        if s < 0:
            raise ValueError("the square root of a negative number is not real")
        if s == 0:
            return Num(None, ZERO)
        if self.F is None:
            n, d = self.c.numerator, self.c.denominator
            rn, rd = isqrt(n), isqrt(d)
            if rn * rn == n and rd * rd == d:
                return Num(None, Fraction(rn, rd))
            F = Field([-self.c, ZERO, ONE], *_sqrt_bounds(self.c, 4))
            return Num(F, [ZERO, ONE])
        F = self.F
        # a perfect square inside F? Try the conjugate-free test by adjoining.
        h = pgcd(F.poly, self.c)
        if len(h) > 1:
            F.split(h)
        coeffs = [pscale(self.c, -1), [], [ONE]]
        me = self

        def enclose(step):
            for _ in range(step and 2):
                me.refine()
            lo, hi = me.interval()
            k = 4 + 2 * step
            while lo <= 0:
                me.refine()
                lo, hi = me.interval()
            return _sqrt_bounds(lo, k)[0], _sqrt_bounds(hi, k)[1]

        G, a_in_G, root = _extend(F, coeffs, enclose)
        return root

    # -- comparison
    def __eq__(self, other):
        try:
            other = Num.of(other)
        except NotExact:
            return NotImplemented
        return (self - other).is_zero()

    def __ne__(self, other):
        r = self.__eq__(other)
        return r if r is NotImplemented else not r

    def __lt__(self, other):
        return (self - Num.of(other)).sign() < 0

    def __le__(self, other):
        return (self - Num.of(other)).sign() <= 0

    def __gt__(self, other):
        return (self - Num.of(other)).sign() > 0

    def __ge__(self, other):
        return (self - Num.of(other)).sign() >= 0

    # -- output, only at the end
    def decimal(self, digits=6):
        """Correctly rounded decimal text with `digits` places."""
        scale = 10 ** digits
        while True:
            lo, hi = self.interval()
            a = round(lo * scale)
            b = round(hi * scale)
            if a == b:
                break
            self.refine()
        neg = a < 0
        a = abs(a)
        whole, frac = divmod(a, scale)
        text = str(whole) + ("." + str(frac).rjust(digits, "0") if digits else "")
        return ("-" if neg and a else "") + text

    def __float__(self):
        return float(Fraction(self.decimal(20)))

    def __repr__(self):
        if self.is_rational():
            return "Num(%s)" % self.c
        return "Num(~%s)" % self.decimal(9)

    __str__ = __repr__


def num(value):
    return Num.of(value)


def sqrt(value):
    return Num.of(value).sqrt()


# ----------------------------------------------------------------------------
# Polynomials whose coefficients are Nums (gcd over a number field).


def nstrip(p):
    p = list(p)
    while p and p[-1].is_zero():
        p.pop()
    return p


def ndivmod(a, b):
    b = nstrip(b)
    if not b:
        raise ZeroDivisionError("division by the zero polynomial")
    a = nstrip(a)
    inv = b[-1].inverse()
    out = [Num(None, ZERO)] * max(len(a) - len(b) + 1, 0)
    while len(a) >= len(b) and a:
        c = a[-1] * inv
        k = len(a) - len(b)
        out[k] = c
        for i, y in enumerate(b):
            a[i + k] = a[i + k] - c * y
        a.pop()
        a = nstrip(a)
    return out, a


def ngcd(a, b):
    a, b = nstrip(a), nstrip(b)
    while b:
        a, b = b, ndivmod(a, b)[1]
    if not a:
        return a
    inv = a[-1].inverse()
    return [c * inv for c in a]


def neval_xpoly(p, x):
    """Evaluate a polynomial with Fraction coefficients at a Num."""
    acc = Num(None, ZERO)
    for c in reversed(p):
        acc = acc * x + Num(None, c)
    return acc
