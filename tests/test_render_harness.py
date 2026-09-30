"""The render harness is the backbone of self-verification, so it is itself
tested. If this file goes red, the agent has lost its eyes and every later
"I checked the drawing" is worthless.

Needs ezdxf and matplotlib, and nothing else. No CAD, no Ollama, no network.
"""

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
GOLDEN = os.path.join(ROOT, "tests", "golden")

ezdxf = pytest.importorskip("ezdxf")
pytest.importorskip("matplotlib")


@pytest.fixture(scope="module")
def drawings(tmp_path_factory):
    sys.path.insert(0, FIXTURES)
    import make_fixtures
    out = tmp_path_factory.mktemp("fixtures")
    made = make_fixtures.build(out_dir=str(out))
    return {os.path.splitext(os.path.basename(p))[0]: p for p in made}


def test_fixtures_build(drawings):
    assert set(drawings) == {"plate", "room", "empty"}
    for path in drawings.values():
        assert os.path.getsize(path) > 1000


def test_render_produces_a_real_picture(drawings, tmp_path):
    from render_dxf import render
    out = str(tmp_path / "plate.png")
    render(drawings["plate"], out, dpi=100)
    assert os.path.getsize(out) > 5000


def test_render_puts_ink_on_the_page(drawings, tmp_path):
    """A render that succeeds and draws nothing is the failure this harness
    exists to catch: on 17/09/2026 an entire plate outline rendered white on
    white while every number said the drawing was correct."""
    np = pytest.importorskip("numpy")
    from PIL import Image
    from render_dxf import render

    out = str(tmp_path / "room.png")
    render(drawings["room"], out, dpi=100)
    arr = np.asarray(Image.open(out).convert("RGB"))
    ink = float((arr.min(axis=2) < 200).mean())
    assert ink > 0.002, ("the page is effectively blank (ink=%.5f): the render "
                         "reported success but drew nothing visible" % ink)


def test_empty_drawing_degrades_cleanly(drawings, tmp_path):
    """The degenerate case, which has broken renderers before."""
    from render_dxf import render, stats
    out = str(tmp_path / "empty.png")
    render(drawings["empty"], out)
    assert os.path.exists(out)
    s = stats(drawings["empty"])
    assert s["entities"] == 0
    assert s["extmin"] is None, "empty drawing must not claim extents"


def test_stats_measure_real_geometry_not_the_header(drawings):
    """$EXTMIN/$EXTMAX in the header are often the sentinel 1e20. Perception
    (product phase 6) must never be fed that."""
    from render_dxf import stats
    s = stats(drawings["plate"])
    assert s["entities"] == 10
    assert s["by_type"]["CIRCLE"] == 4
    assert s["by_type"]["HATCH"] == 1
    assert s["by_type"]["DIMENSION"] == 2
    assert set(s["by_layer"]) == {"OUTLINE", "HOLES", "POCKET", "DIM", "TEXT"}
    assert s["extmin"] is not None
    assert max(abs(v) for v in s["extmin"]) < 1e6, "sentinel extents leaked in"
    w, h = s["size"]
    # The plate is 120 x 80; the extents also contain the dimensions and title.
    assert 120 <= w <= 200, w
    assert 80 <= h <= 160, h


def test_comparison_accepts_an_identical_picture(drawings, tmp_path):
    from render_dxf import render
    from visual_check import compare
    a, b = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    render(drawings["plate"], a)
    render(drawings["plate"], b)
    verdict = compare(a, b)
    assert verdict["ok"], verdict


def test_comparison_catches_a_changed_drawing(drawings, tmp_path):
    """The test that makes the golden images worth having: a real change must
    fail, or the harness is decoration.

    The change is deliberately small and same-size -- one hole removed from the
    plate. A regression that shifts the page bounds is caught by the cheap size
    check; this covers the harder case where the picture is the same shape and
    the geometry inside it is wrong.
    """
    from render_dxf import render
    from visual_check import compare

    golden = str(tmp_path / "plate.png")
    render(drawings["plate"], golden)

    doc = ezdxf.readfile(drawings["plate"])
    msp = doc.modelspace()
    hole = next(e for e in msp if e.dxftype() == "CIRCLE")
    msp.delete_entity(hole)
    changed_dxf = str(tmp_path / "plate_one_hole_less.dxf")
    doc.saveas(changed_dxf)
    candidate = str(tmp_path / "plate_changed.png")
    render(changed_dxf, candidate)

    verdict = compare(candidate, golden)
    assert not verdict["ok"], \
        "a missing hole compared equal to the original: %s" % verdict
    assert os.path.exists(verdict["diff_image"]), \
        "a failure must leave a picture of itself to look at"


def test_comparison_rejects_a_differently_shaped_page(drawings, tmp_path):
    """The cheap check, before any pixel arithmetic."""
    from render_dxf import render
    from visual_check import compare
    a, b = str(tmp_path / "plate.png"), str(tmp_path / "room.png")
    render(drawings["plate"], a)
    render(drawings["room"], b)
    verdict = compare(a, b)
    assert not verdict["ok"]
    assert "size differs" in verdict["reason"]


def test_missing_golden_is_reported_not_passed(tmp_path):
    from visual_check import compare
    verdict = compare(__file__, str(tmp_path / "nope.png"))
    assert not verdict["ok"]
    assert "no golden image" in verdict["reason"]


def test_cli_renders_and_reports_stats(drawings, tmp_path):
    out = str(tmp_path / "cli.png")
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_dxf.py"),
         drawings["plate"], out, "--stats"],
        stdin=subprocess.DEVNULL, capture_output=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr.decode()
    text = proc.stdout.decode()
    payload = json.loads(text.split("\n", 1)[1])
    assert payload["entities"] == 10
    assert os.path.exists(out)
