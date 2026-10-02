"""Factoring over Q, and fields that keep their true size -- part of the exact
numbers of ADR 0010, added with P2-T03 (ADR 0012, "Change to ADR 0010").

Without minimal polynomials every square root taken inside a field doubled it,
even when the root was already there; a rounded triangle with 45-degree corners
reached degree 16 and took minutes. These tests pin both halves of the fix.

Standard library only: runs with pytest in CI and with tools/run_tests.py
anywhere.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from geometry.factor import factor_int        # noqa: E402
from geometry.exact import sqrt, Num          # noqa: E402
from geometry.primitives import Segment       # noqa: E402
from geometry.ops import fillet               # noqa: E402


def mul(*ps):
    out = [1]
    for p in ps:
        o = [0] * (len(out) + len(p) - 1)
        for i, a in enumerate(out):
            for j, b in enumerate(p):
                o[i + j] += a * b
        out = o
    return out


def as_set(factors):
    return sorted(tuple(f) for f in factors)


def test_irreducible_polynomials_stay_whole():
    assert factor_int([1, 0, -10, 0, 1]) == [[1, 0, -10, 0, 1]]   # sqrt 2 + sqrt 3
    assert factor_int([-2, 0, 1]) == [[-2, 0, 1]]
    assert factor_int([1, 1, 1, 1, 1]) == [[1, 1, 1, 1, 1]]


def test_products_come_apart_into_their_factors():
    cases = [
        [[-2, 0, 1], [-3, 0, 1]],
        [[1, 1], [-1, 1], [5, 0, 0, 1]],
        [[-1, 2], [-3, 1], [1, 1, 1, 1, 1]],                       # 2x - 1 keeps its 2
        [[7, 3], [2, -5], [11, 0, 4], [1, 2, 3, 4, 5, 6, 7]],
        [[1, 0, -10, 0, 1], [-5, 0, 1]],
    ]
    for factors in cases:
        f = mul(*factors)
        got = factor_int(f)
        assert mul(*got) in (f, [-c for c in f])
        norm = [x if x[-1] > 0 else [-c for c in x] for x in factors]
        assert as_set(got) == as_set(norm), (factors, got)


def test_a_square_root_already_in_the_field_does_not_grow_it():
    r2 = sqrt(2)
    x = (3 + 2 * r2).sqrt()              # = 1 + sqrt 2, already in Q(sqrt 2)
    assert x == 1 + r2
    assert x.F.degree == 2
    y = sqrt(2) + sqrt(3) + sqrt(5)      # a real degree-8 number stays degree 8
    assert y.F.degree == 8
    assert (y - sqrt(5)) * (y - sqrt(5)) == 5 + 2 * sqrt(6)


def test_a_45_degree_rounded_triangle_is_fast_and_small():
    t = time.time()
    a, b, c = Segment((0, 0), (10, 0)), Segment((10, 0), (10, 10)), Segment((10, 10), (0, 0))
    r1 = fillet(a, b, 1)
    r2 = fillet(r1.second, c, 1)
    r3 = fillet(r2.second, r1.first, 1)
    degrees = set()
    for piece in (r1.piece, r2.piece, r3.piece):
        for v in (piece.c.x, piece.c.y, piece.r):
            if isinstance(v, Num) and not v.is_rational():
                degrees.add(v.F.degree)
    assert degrees <= {2}, degrees
    assert time.time() - t < 5
