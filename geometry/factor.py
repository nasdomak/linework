"""geometry.factor -- factor a rational polynomial into irreducible factors
(Zassenhaus: factor modulo a prime, Hensel-lift, recombine). Part of ADR 0010.

Why the solver needs it: a field Q(a) must be described by the *minimal*
polynomial of a, or every square root taken in it doubles its size even when the
root was already there (sqrt(2) * sqrt(2) inside Q(sqrt 2) would build
Q(sqrt 2, sqrt 2), of degree 4, and so on). Factoring keeps every field at its
true degree.

Everything here is exact integer arithmetic; the random choices of the
equal-degree splitting use a fixed seed, so a run is reproducible, and every
factor found is checked by exact division before it is accepted.

Standard library only (CORE package).
"""

from fractions import Fraction
import random

_PRIMES = [p for p in range(3, 2000) if all(p % d for d in range(2, int(p ** 0.5) + 1))]


# ---------------------------------------------------------------- integer polys mod m

def _trim(a):
    while a and a[-1] == 0:
        a.pop()
    return a


def _mod(a, m):
    return _trim([c % m for c in a])


def _sub(a, b, m):
    n = max(len(a), len(b))
    return _trim([((a[i] if i < len(a) else 0) - (b[i] if i < len(b) else 0)) % m
                  for i in range(n)])


def _add(a, b, m):
    n = max(len(a), len(b))
    return _trim([((a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)) % m
                  for i in range(n)])


def _mul(a, b, m):
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                out[i + j] += x * y
    return _trim([c % m for c in out])


def _divmod(a, b, p):
    """Division in F_p[x] (p prime)."""
    a = list(a)
    inv = pow(b[-1], p - 2, p)
    out = [0] * max(len(a) - len(b) + 1, 0)
    while len(a) >= len(b) and a:
        c = a[-1] * inv % p
        k = len(a) - len(b)
        out[k] = c
        for i, y in enumerate(b):
            a[i + k] = (a[i + k] - c * y) % p
        _trim(a)
    return _trim(out), a


def _divmod_monic(a, b, m):
    """Division by a monic b over Z/m."""
    a = list(a)
    out = [0] * max(len(a) - len(b) + 1, 0)
    while len(a) >= len(b) and a:
        c = a[-1] % m
        k = len(a) - len(b)
        out[k] = c
        for i, y in enumerate(b):
            a[i + k] = (a[i + k] - c * y) % m
        _trim(a)
    return _trim(out), a


def _monic(a, p):
    inv = pow(a[-1], p - 2, p)
    return [c * inv % p for c in a]


def _gcd(a, b, p):
    a, b = _mod(a, p), _mod(b, p)
    while b:
        a, b = b, _divmod(a, b, p)[1]
    return _monic(a, p) if a else a


def _deriv(a, m):
    return _trim([(i * a[i]) % m for i in range(1, len(a))])


def _powmod(base, e, f, p):
    result, base = [1], _divmod(base, f, p)[1]
    while e:
        if e & 1:
            result = _divmod(_mul(result, base, p), f, p)[1]
        base = _divmod(_mul(base, base, p), f, p)[1]
        e >>= 1
    return result


def _xgcd(a, b, p):
    """s, t with s a + t b = 1 in F_p[x] (a, b coprime)."""
    r0, r1, s0, s1, t0, t1 = a, b, [1], [], [], [1]
    while r1:
        q, r = _divmod(r0, r1, p)
        r0, r1 = r1, r
        s0, s1 = s1, _sub(s0, _mul(q, s1, p), p)
        t0, t1 = t1, _sub(t0, _mul(q, t1, p), p)
    inv = pow(r0[0], p - 2, p)
    return [c * inv % p for c in s0], [c * inv % p for c in t0]


# ---------------------------------------------------------------- factoring mod p

def _factor_mod_p(f, p, rng):
    """Monic irreducible factors of a monic square-free f in F_p[x]."""
    out, rest, i = [], f, 0
    xp = [0, 1]
    # distinct-degree factorisation
    by_degree = []
    while len(rest) - 1 >= 2 * (i + 1):
        i += 1
        xp = _powmod(xp, p, rest, p)
        g = _gcd(rest, _sub(xp, [0, 1], p), p)
        if len(g) > 1:
            by_degree.append((g, i))
            rest = _divmod(rest, g, p)[0]
            xp = _divmod(xp, rest, p)[1]
    if len(rest) > 1:
        by_degree.append((_monic(rest, p), len(rest) - 1))
    # equal-degree splitting (Cantor-Zassenhaus)
    for g, d in by_degree:
        stack = [g]
        while stack:
            h = stack.pop()
            if len(h) - 1 == d:
                out.append(h)
                continue
            while True:
                a = [rng.randrange(p) for _ in range(len(h) - 1)]
                a = _trim(a)
                if len(a) < 2:
                    continue
                b = _sub(_powmod(a, (p ** d - 1) // 2, h, p), [1], p)
                k = _gcd(h, b, p)
                if 1 < len(k) < len(h):
                    stack.append(k)
                    stack.append(_monic(_divmod(h, k, p)[0], p))
                    break
    return out


# ---------------------------------------------------------------- Hensel lifting

def _lift2(f, g, h, p, k):
    """f monic over Z, f = g h mod p with g, h monic coprime: lift to mod p^k."""
    s, t = _xgcd(g, h, p)
    m = p
    while m < p ** k:
        e = _sub(f, _mul(g, h, m * p), m * p)
        e = [c // m for c in e]
        e = _mod(e, p)
        q, dg = _divmod(_mul(t, e, p), g, p)
        dh = _divmod(_sub(e, _mul(dg, h, p), p), g, p)[0]
        g = _add(g, [c * m for c in dg], m * p)
        h = _add(h, [c * m for c in dh], m * p)
        m *= p
    return g, h


def _lift_all(f, factors, p, k):
    M = p ** k
    if len(factors) == 1:
        return [_mod(f, M)]
    g = factors[0]
    h = [1]
    for x in factors[1:]:
        h = _mul(h, x, p)
    G, H = _lift2(f, g, h, p, k)
    return [G] + _lift_all(H, factors[1:], p, k)


# ---------------------------------------------------------------- over Z

def _primitive(a):
    from math import gcd
    g = 0
    for c in a:
        g = gcd(g, c)
    a = [c // g for c in a] if g else a
    if a and a[-1] < 0:
        a = [-c for c in a]
    return a


def _int_divides(a, b):
    """Does the integer poly a divide b over Z (exactly)?"""
    b = list(b)
    out = []
    while len(b) >= len(a) and b:
        if b[-1] % a[-1]:
            return False
        c = b[-1] // a[-1]
        k = len(b) - len(a)
        for i, y in enumerate(a):
            b[i + k] -= c * y
        _trim(b)
        out.append(c)
    return not b


def _int_div(a, b):
    """b / a over Z, known exact."""
    b = list(b)
    out = [0] * (len(b) - len(a) + 1)
    while len(b) >= len(a) and b:
        c = b[-1] // a[-1]
        k = len(b) - len(a)
        out[k] = c
        for i, y in enumerate(a):
            b[i + k] -= c * y
        _trim(b)
    return _trim(out)


def _symmetric(a, m):
    return [c - m if c > m // 2 else c for c in a]


def factor_int(f):
    """Irreducible factors over Z of a square-free primitive integer poly f
    (lowest degree first), each primitive with a positive leading coefficient."""
    f = _primitive(_trim(list(f)))
    if len(f) <= 2:
        return [f]
    if f[0] == 0:
        return [[0, 1]] + factor_int(f[1:])
    lc = f[-1]
    n = len(f) - 1
    rng = random.Random(len(f) * 1000003 + sum(abs(c) for c in f) % 1000003)
    best = None
    tried = 0
    for p in _PRIMES:
        if lc % p == 0:
            continue
        fp = _mod(f, p)
        if len(_gcd(fp, _deriv(fp, p), p)) > 1:
            continue
        facs = _factor_mod_p(_monic(fp, p), p, rng)
        if best is None or len(facs) < len(best[1]):
            best = (p, facs)
        tried += 1
        if len(facs) == 1 or tried >= 6:
            break
    p, facs = best
    if len(facs) == 1:
        return [f]
    # Mignotte: every factor's coefficients are at most 2^n |f|_2 |lc| in size
    norm = int(sum(c * c for c in f) ** 0.5) + 1
    bound = 2 * (2 ** n) * norm * abs(lc)
    k = 1
    while p ** k <= bound:
        k += 1
    M = p ** k
    monic_f = _mod([c * pow(lc, -1, M) for c in f], M)
    lifted = _lift_all(monic_f, facs, p, k)
    found, rest, s = [], f, 1
    remaining = list(range(len(lifted)))
    while 2 * s <= len(remaining):
        hit = False
        for combo in _combinations(remaining, s):
            cand = [rest[-1] % M]
            for i in combo:
                cand = _mul(cand, lifted[i], M)
            cand = _primitive(_symmetric(cand, M))
            if _int_divides(cand, rest):
                found.append(cand)
                rest = _int_div(cand, rest)
                rest = _primitive(rest)
                remaining = [i for i in remaining if i not in combo]
                hit = True
                break
        if not hit:
            s += 1
    found.append(_primitive(rest))
    return found


def _combinations(items, k):
    if k == 0:
        yield ()
        return
    for i in range(len(items) - k + 1):
        for rest in _combinations(items[i + 1:], k - 1):
            yield (items[i],) + rest


def factor_q(poly):
    """Monic irreducible factors over Q of a square-free rational polynomial
    (list of Fractions, lowest degree first)."""
    den = 1
    for c in poly:
        den = den * c.denominator // _g(den, c.denominator)
    ints = [int(c * den) for c in poly]
    out = []
    for fac in factor_int(ints):
        lead = Fraction(fac[-1])
        out.append([Fraction(c) / lead for c in fac])
    return out


def _g(a, b):
    while b:
        a, b = b, a % b
    return a
