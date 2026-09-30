#!/usr/bin/env python3
"""
make_fixtures.py -- deterministic test drawings, generated rather than stored.

A DXF checked into git is a binary-ish blob nobody can review. A generator is
readable, diffable, and states exactly what the drawing is supposed to contain,
which is what a golden-image test needs in order to mean anything.

    py tests/fixtures/make_fixtures.py            writes them all
    py tests/fixtures/make_fixtures.py plate      writes one
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Every fixture states what it is for, so a failure can be read.
CATALOGUE = {
    "plate": "A plate with four holes, a chamfer, a hatched pocket, two "
             "dimensions and a title. Exercises layers, colours, arcs, "
             "hatching, dimensions and text in one drawing.",
    "room": "A 5x4 room with 300 mm walls, a door east and two windows south. "
            "The architectural case the whole project is aimed at.",
    "empty": "A drawing with layers defined and nothing drawn. The degenerate "
             "case that has broken renderers before.",
}


def _new():
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4          # millimetres
    return doc


def plate(path):
    """Mechanical: plate 120 x 80, four M8 holes, one chamfer, a hatched
    pocket, two dimensions."""
    import ezdxf
    doc = _new()
    msp = doc.modelspace()
    for name, colour, weight in (("OUTLINE", 7, 50), ("HOLES", 1, 25),
                                 ("POCKET", 3, 25), ("DIM", 4, 18),
                                 ("TEXT", 2, 18)):
        doc.layers.add(name, color=colour, lineweight=weight)

    w, h, ch = 120.0, 80.0, 10.0
    outline = [(0, 0), (w - ch, 0), (w, ch), (w, h), (0, h)]
    msp.add_lwpolyline(outline, close=True, dxfattribs={"layer": "OUTLINE"})

    for x, y in ((15, 15), (105, 15), (15, 65), (105, 65)):
        msp.add_circle((x, y), 4.0, dxfattribs={"layer": "HOLES"})

    pocket = [(40, 30), (80, 30), (80, 50), (40, 50)]
    msp.add_lwpolyline(pocket, close=True, dxfattribs={"layer": "POCKET"})
    hatch = msp.add_hatch(color=3, dxfattribs={"layer": "POCKET"})
    hatch.set_pattern_fill("ANSI31", scale=1.5)
    hatch.paths.add_polyline_path(pocket, is_closed=True)

    # Dimension sizes have to be stated relative to the drawing, or the text
    # renders as an unreadable speck. This is the whole of phase 16 in
    # miniature: a scale is only correct together with its text height.
    dim = {"dimtxt": 4.0, "dimasz": 3.0, "dimexe": 2.0, "dimexo": 2.0,
           "dimgap": 1.0, "dimtad": 1, "dimdec": 0,
           "dimlfac": 1.0}
    msp.add_linear_dim(base=(0, -18), p1=(0, 0), p2=(w, 0),
                       dxfattribs={"layer": "DIM"}, override=dim).render()
    msp.add_linear_dim(base=(-20, 0), p1=(0, 0), p2=(0, h), angle=90,
                       dxfattribs={"layer": "DIM"}, override=dim).render()

    msp.add_text("PLATE 120x80 - 4 x D8", height=5.0,
                 dxfattribs={"layer": "TEXT"}).set_placement((0, h + 8))

    doc.set_modelspace_vport(height=140, center=(60, 40))
    doc.saveas(path)
    return path


def room(path):
    """Architecture: a 5.0 x 4.0 m room, 300 mm walls, a 900 door east, two
    1200 windows south. Coordinates in millimetres."""
    doc = _new()
    msp = doc.modelspace()
    for name, colour, weight in (("WALLS", 7, 50), ("OPENINGS", 5, 25),
                                 ("DIM", 4, 18), ("TEXT", 2, 18)):
        doc.layers.add(name, color=colour, lineweight=weight)

    iw, ih, t = 5000.0, 4000.0, 300.0
    msp.add_lwpolyline([(0, 0), (iw, 0), (iw, ih), (0, ih)], close=True,
                       dxfattribs={"layer": "WALLS"})
    msp.add_lwpolyline([(-t, -t), (iw + t, -t), (iw + t, ih + t), (-t, ih + t)],
                       close=True, dxfattribs={"layer": "WALLS"})

    # Door east, centred on the wall: the "centred" relation, by hand, once.
    door = 900.0
    y0 = (ih - door) / 2.0
    msp.add_lwpolyline([(iw, y0), (iw + t, y0), (iw + t, y0 + door), (iw, y0 + door)],
                       close=True, dxfattribs={"layer": "OPENINGS"})

    # Two windows south, distributed over the wall.
    win = 1200.0
    for cx in (iw * 0.3, iw * 0.7):
        msp.add_lwpolyline([(cx - win / 2, -t), (cx + win / 2, -t),
                            (cx + win / 2, 0), (cx - win / 2, 0)],
                           close=True, dxfattribs={"layer": "OPENINGS"})

    dim = {"dimtxt": 160.0, "dimasz": 120.0, "dimexe": 80.0, "dimexo": 80.0,
           "dimgap": 40.0, "dimtad": 1, "dimdec": 0,
           "dimlfac": 1.0}
    msp.add_linear_dim(base=(0, -900), p1=(0, 0), p2=(iw, 0),
                       dxfattribs={"layer": "DIM"}, override=dim).render()
    msp.add_linear_dim(base=(-900, 0), p1=(0, 0), p2=(0, ih), angle=90,
                       dxfattribs={"layer": "DIM"}, override=dim).render()
    msp.add_text("ROOM 5.00 x 4.00", height=200.0,
                 dxfattribs={"layer": "TEXT"}).set_placement((0, ih + 500))

    doc.set_modelspace_vport(height=7000, center=(2500, 2000))
    doc.saveas(path)
    return path


def empty(path):
    doc = _new()
    for name in ("OUTLINE", "DIM", "TEXT"):
        doc.layers.add(name)
    doc.saveas(path)
    return path


BUILDERS = {"plate": plate, "room": room, "empty": empty}


def build(name=None, out_dir=HERE):
    os.makedirs(out_dir, exist_ok=True)
    names = [name] if name else sorted(BUILDERS)
    made = []
    for n in names:
        if n not in BUILDERS:
            raise SystemExit("unknown fixture %r; known: %s"
                             % (n, ", ".join(sorted(BUILDERS))))
        made.append(BUILDERS[n](os.path.join(out_dir, n + ".dxf")))
    return made


if __name__ == "__main__":
    for p in build(sys.argv[1] if len(sys.argv) > 1 else None):
        print(p)
