# What the render harness found the day it was built

Session 2, 17/09/2026. Recorded because these are exactly the defects the
harness exists to catch, and because two of them are still open.

The lesson, first: **every one of these drawings passed its numeric check.**
`render_dxf.py --stats` reported 10 entities on 5 layers with correct extents,
and it was right. The drawing was still wrong. Numbers and pictures catch
different things, and the agent needs both — a shape can look right at the wrong
size, and a correct size can be invisible.

## Fixed

### 1. Colour 7 rendered white on a white sheet

DXF colour 7 means "whatever contrasts with the background". ezdxf's drawing
add-on assumes a dark sheet, so 7 resolved to white and the whole plate outline
rendered invisible while the render reported success.

Half-fixed in `tools/render_dxf.py`: the layout colours are now set explicitly
to a white background with a black foreground. **See open issue 3 below — the
outline is still missing, so this is not yet the whole story.**

### 2. Dimensions read 12000 instead of 120

`ezdxf.new(setup=True)` writes `$DIMLFAC = 100.0` into the header, which
multiplies every measured length by 100 in the dimension text. A 120 mm plate
was dimensioned "12000".

Fixed in the fixtures by pinning `dimlfac: 1.0` in the dimension override. When
the engine writes real dimensions (product phase 3), it must set this
explicitly rather than inherit it — and phase 16 owns the wider question of a
scale being correct only together with its text height.

The same fixture originally rendered its dimension text as an unreadable speck,
because `dimtxt` was left at its 2.5 default. Dimension sizes have to be stated
relative to the drawing.

### 3. A global pixel percentage could not catch a missing hole

Measured: deleting an entire hole from the plate changed **170 pixels out of
299,520 — 0.06% of the image**. Any tolerance loose enough to survive the
one-pixel antialiasing differences between operating systems was also loose
enough to let a missing hole through.

Fixed in `tools/visual_check.py`: the comparison is now cluster-based. The image
is cut into 16x16 tiles and any tile whose pixels differ by more than 6% fails.
Antialiasing differences are thin and spread along every edge, so no tile fills
up; a missing hole, a moved line or a lost hatch is concentrated, so it fails.
The global percentage and an ink-coverage check are kept as cheap backstops.

Verified both ways: an identical re-render passes, and one missing hole out of
four fails with 6 bad tiles. A harness that misses a missing hole is decoration.

## Still open — belongs to product phase 3

These are recorded as task **P3-T04** in `state/backlog.json` so they cannot be
forgotten.

### 4. The plate outline is still not drawn

After the colour fix above, dimensions and holes render correctly but the
`OUTLINE` layer (ACI colour 7) still produces nothing visible. Diagnosis so far:
`RenderContext` resolves the layer table at construction time, so patching
`ctx.layers[...].color` afterwards appears not to affect how entities with
`BYLAYER` colour are resolved. The fix is probably to configure the context
before or during construction — `ezdxf.addons.drawing.config.Configuration` has
`color_policy`, `custom_fg_color` and `background_policy` fields that were not
tried.

**Not yet isolated. Do not assume the above diagnosis is right** — reproduce it
first. Until it is fixed, fixtures should use explicit colours rather than 7,
and no golden image should be blessed for a drawing that uses colour 7.

### 5. Hatch patterns do not render

`set_pattern_fill("ANSI31", scale=1.5)` on a closed polyline path produces a
HATCH entity — the stats confirm it is in the file — but no pattern lines appear
in the PNG. Solid fill was not tried as a control. `Configuration` has a
`hatch_policy` and a `min_hatch_line_distance` that are the obvious first place
to look.

This matters more than it looks: hatching is one of the two things LibreCAD's
plugin API cannot do at all, and therefore one of the reasons DXF is the
engine's home ground. If it cannot be rendered, it cannot be verified.

## Golden images

**None have been blessed.** Deliberately. A golden image is a claim that a
drawing is correct, and while issues 4 and 5 are open, the fixtures are not
correct. `tests/golden/` is empty, CI says so plainly and uploads the renders as
artefacts instead of comparing against nothing.

Bless them in phase 3, after looking at the pictures, with
`py tools/visual_check.py bless out/plate.png tests/golden/plate.png`.
