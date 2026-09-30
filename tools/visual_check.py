#!/usr/bin/env python3
"""
visual_check.py -- golden-image comparison, so a visual change fails a test
instead of needing Marco's eyes.

    py tools/visual_check.py render tests/fixtures/plate.dxf out/plate.png
    py tools/visual_check.py compare out/plate.png tests/golden/plate.png
    py tools/visual_check.py bless  out/plate.png tests/golden/plate.png

Why a tolerance and not an exact match: matplotlib and its font stack render a
pixel or two differently across operating systems and versions, so an exact
comparison would fail for reasons that have nothing to do with the drawing.
The tolerance is deliberately tight enough that a moved line, a lost hatch or a
changed colour still fails.

When a comparison fails it writes a side-by-side diff image, because the point
of this harness is that the agent can look at the failure and say what broke.
"""

import argparse
import json
import os
import sys

PIXEL_THRESHOLD = 24          # per-channel difference counted as "different"
DEFAULT_TOLERANCE = 0.005     # global share of differing pixels still allowed
TILE = 16                     # side of the tile the cluster test works on
TILE_TOLERANCE = 0.06         # share of one tile's pixels that may differ

# Why a cluster test and not a global percentage.
#
# A global percentage cannot do this job. Measured on 17/09/2026: deleting an
# entire hole from the plate fixture changed 170 pixels out of 299,520 -- 0.06%
# of the image. Any tolerance loose enough to survive the one-pixel
# antialiasing differences between operating systems is also loose enough to
# let a missing hole through, and a harness that misses a missing hole is
# decoration.
#
# So the image is cut into small tiles. Antialiasing differences are thin and
# spread along every edge, so no single tile fills up. A missing hole, a moved
# line or a lost hatch is concentrated, so it fills a tile and fails. The
# global percentage and the ink check are kept as cheap backstops.


def _load(path):
    import numpy as np
    from PIL import Image
    img = Image.open(path).convert("RGB")
    return np.asarray(img).astype("int16")


def compare(candidate, golden, tolerance=DEFAULT_TOLERANCE,
            threshold=PIXEL_THRESHOLD, diff_out=None):
    """Return a verdict dict. 'ok' is the only thing a test needs to read."""
    import numpy as np

    if not os.path.isfile(golden):
        return {"ok": False, "reason": "no golden image at %s" % golden,
                "action": "run 'bless' once the candidate has been looked at "
                          "and judged correct"}
    a, b = _load(candidate), _load(golden)
    if a.shape != b.shape:
        return {"ok": False, "reason": "size differs: candidate %s, golden %s"
                                       % (a.shape, b.shape)}

    delta = np.abs(a - b)
    per_pixel = delta.max(axis=2)
    hot = per_pixel > threshold
    differing = int(hot.sum())
    total = int(per_pixel.size)
    fraction = differing / total

    # The cluster test: is the difference concentrated anywhere?
    h, w = hot.shape
    ph, pw = (-h) % TILE, (-w) % TILE
    padded = np.pad(hot, ((0, ph), (0, pw)), constant_values=False)
    tiles = padded.reshape(padded.shape[0] // TILE, TILE,
                           padded.shape[1] // TILE, TILE)
    per_tile = tiles.sum(axis=(1, 3)) / float(TILE * TILE)
    worst_tile = float(per_tile.max()) if per_tile.size else 0.0
    bad_tiles = int((per_tile > TILE_TOLERANCE).sum())

    # Ink coverage catches what both of the above can hide: a drawing that
    # simply vanished, or appeared.
    ink = lambda x: float((x.min(axis=2) < 200).mean())
    ink_a, ink_b = ink(a), ink(b)

    reasons = []
    if bad_tiles:
        reasons.append("%s tile(s) of %sx%s px differ by more than %.0f%% "
                       "(worst %.0f%%): the difference is concentrated, so "
                       "something in the drawing changed"
                       % (bad_tiles, TILE, TILE, TILE_TOLERANCE * 100,
                          worst_tile * 100))
    if fraction > tolerance:
        reasons.append("%.4f%% of all pixels differ (limit %.4f%%)"
                       % (fraction * 100, tolerance * 100))
    if abs(ink_a - ink_b) > 0.02:
        reasons.append("ink coverage %.3f vs %.3f: the amount drawn changed"
                       % (ink_a, ink_b))

    verdict = {
        "ok": not reasons,
        "differing_pixels": differing,
        "total_pixels": total,
        "fraction_differing": round(fraction, 6),
        "tolerance": tolerance,
        "bad_tiles": bad_tiles,
        "worst_tile_fraction": round(worst_tile, 4),
        "tile": TILE,
        "tile_tolerance": TILE_TOLERANCE,
        "max_difference": int(per_pixel.max()),
        "ink_candidate": round(ink_a, 5),
        "ink_golden": round(ink_b, 5),
        "candidate": candidate,
        "golden": golden,
    }
    if reasons:
        verdict["reason"] = "; ".join(reasons)
        verdict["diff_image"] = write_diff(a, b, per_pixel,
                                           diff_out or _diff_path(candidate))
    return verdict


def _diff_path(candidate):
    base, ext = os.path.splitext(candidate)
    return base + ".diff" + (ext or ".png")


def write_diff(a, b, per_pixel, out):
    """Candidate, golden and the difference, side by side, so the failure can
    be looked at rather than reasoned about."""
    import numpy as np
    from PIL import Image

    h, w = per_pixel.shape
    heat = np.zeros((h, w, 3), dtype="uint8")
    hot = per_pixel > PIXEL_THRESHOLD
    heat[..., 0] = np.where(hot, 255, 255 - np.clip(per_pixel, 0, 255)).astype("uint8")
    heat[..., 1] = np.where(hot, 0, 255 - np.clip(per_pixel, 0, 255)).astype("uint8")
    heat[..., 2] = np.where(hot, 0, 255 - np.clip(per_pixel, 0, 255)).astype("uint8")

    gap = 8
    canvas = np.full((h, w * 3 + gap * 2, 3), 220, dtype="uint8")
    canvas[:, 0:w] = a.astype("uint8")
    canvas[:, w + gap:2 * w + gap] = b.astype("uint8")
    canvas[:, 2 * w + 2 * gap:] = heat
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    Image.fromarray(canvas).save(out)
    return out


def bless(candidate, golden):
    """Accept the candidate as the new golden image. Deliberately a separate,
    explicit act: a golden image nobody looked at proves nothing."""
    import shutil
    os.makedirs(os.path.dirname(os.path.abspath(golden)), exist_ok=True)
    shutil.copyfile(candidate, golden)
    return golden


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render")
    r.add_argument("dxf")
    r.add_argument("png")
    r.add_argument("--dpi", type=int, default=100)

    c = sub.add_parser("compare")
    c.add_argument("candidate")
    c.add_argument("golden")
    c.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)

    bl = sub.add_parser("bless")
    bl.add_argument("candidate")
    bl.add_argument("golden")

    args = p.parse_args(argv)

    if args.cmd == "render":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from render_dxf import render
        print(render(args.dxf, args.png, dpi=args.dpi))
        return 0

    if args.cmd == "compare":
        verdict = compare(args.candidate, args.golden, tolerance=args.tolerance)
        print(json.dumps(verdict, indent=2))
        return 0 if verdict["ok"] else 1

    if args.cmd == "bless":
        print(bless(args.candidate, args.golden))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
