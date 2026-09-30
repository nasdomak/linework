#!/usr/bin/env python3
"""
render_dxf.py -- a drawing becomes a picture.

This is the backbone of self-verification. A DXF rendered to PNG can be looked
at by the agent itself: layers, colours, hatches, text and geometry are all
visible, so "it ran without error" becomes "it is right" without a human in
between.

    py tools/render_dxf.py drawing.dxf                -> drawing.png
    py tools/render_dxf.py drawing.dxf out.png --dpi 150
    py tools/render_dxf.py drawing.dxf out.png --stats

ezdxf lives here, in the tooling and the dxf/ package, and nowhere else: the
engine core stays standard-library only.
"""

import argparse
import json
import os
import sys


def render(src, dst, dpi=100, width=12.0, height=9.0, layout="Model"):
    import matplotlib
    matplotlib.use("Agg")              # no display anywhere, ever
    import matplotlib.pyplot as plt
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    doc = ezdxf.readfile(src)
    msp = doc.modelspace() if layout == "Model" else doc.layout(layout)

    ctx = RenderContext(doc)
    # DXF colour 7 means "whatever contrasts with the background". ezdxf
    # defaults to a dark sheet, so 7 resolves to white -- and on our white
    # background the geometry renders invisible while the render reports
    # success. Setting the layout colours is not enough on its own: the layer
    # table was already resolved when RenderContext was constructed, so the
    # resolved white has to be corrected too.
    # Found on 17/09/2026 by looking at a picture that was numerically
    # perfect and visually empty. This is the reason this harness exists.
    ctx.current_layout_properties.set_colors(bg="#FFFFFF", fg="#000000")
    for layer_properties in ctx.layers.values():
        if layer_properties.color.lower() in ("#ffffff", "#ffffffff"):
            layer_properties.color = "#000000"

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    Frontend(ctx, MatplotlibBackend(ax)).draw_layout(msp, finalize=True)
    fig.savefig(dst, dpi=dpi, facecolor="white")
    plt.close(fig)
    return dst


def stats(src):
    """A numeric description of the drawing, to check alongside the picture.

    A picture catches what numbers miss and numbers catch what a picture
    misses -- a shape can look right at the wrong size. Both, always.
    """
    import ezdxf
    doc = ezdxf.readfile(src)
    msp = doc.modelspace()
    by_type, by_layer = {}, {}
    for e in msp:
        by_type[e.dxftype()] = by_type.get(e.dxftype(), 0) + 1
        layer = getattr(e.dxf, "layer", "?")
        by_layer[layer] = by_layer.get(layer, 0) + 1
    # The header's $EXTMIN/$EXTMAX are written by whichever program saved the
    # file and are often the "not computed" sentinel 1e20. Measure the real
    # geometry instead, because extents are part of perception (phase 6) and a
    # sentinel would quietly poison it.
    from ezdxf import bbox
    ext_min = ext_max = size = None
    box = bbox.extents(msp, fast=True)
    if box.has_data:
        # extmin/extmax are Vec3, which does not slice: name the axes.
        ext_min = (round(box.extmin.x, 6), round(box.extmin.y, 6))
        ext_max = (round(box.extmax.x, 6), round(box.extmax.y, 6))
        size = (round(ext_max[0] - ext_min[0], 6),
                round(ext_max[1] - ext_min[1], 6))
    return {
        "file": os.path.basename(src),
        "entities": sum(by_type.values()),
        "by_type": dict(sorted(by_type.items())),
        "by_layer": dict(sorted(by_layer.items())),
        "layers_defined": sorted(l.dxf.name for l in doc.layers),
        "units": doc.header.get("$INSUNITS", None),
        "extmin": ext_min,
        "extmax": ext_max,
        "size": size,
        "dxfversion": doc.dxfversion,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dxf")
    p.add_argument("png", nargs="?")
    p.add_argument("--dpi", type=int, default=100)
    p.add_argument("--layout", default="Model")
    p.add_argument("--stats", action="store_true",
                   help="also print a numeric description as JSON")
    args = p.parse_args(argv)

    out = args.png or os.path.splitext(args.dxf)[0] + ".png"
    render(args.dxf, out, dpi=args.dpi, layout=args.layout)
    print(out)
    if args.stats:
        print(json.dumps(stats(args.dxf), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
