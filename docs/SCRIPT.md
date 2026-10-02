# The linework script

> The readable recipe of a drawing. Decided in
> [ADR 0006](adr/0006-the-script-language.md); the words it may use are in
> [CATALOGUE.md](CATALOGUE.md). Every example on this page is run by
> `tests/test_script.py`: the ones marked `linework` must be accepted and must
> print back exactly as written; the ones marked `linework-refused` must be
> refused with exactly the error shown on their last line.

## What a script is, in one minute

Think of a recipe card. It does not say "move your hand 23 cm to the left"; it
says "add the eggs to the flour". A script is the same for a drawing: it says
*what* goes *where relative to what*, and the solver works out the exact
coordinates.

```linework
linework script 1
domain architecture

add room living: at origin, width 5 m, length 4 m, text "Living room"
add room kitchen: next to living on side right, width 3 m, length 4 m, text "Kitchen"
```

Read it aloud: *add a room called living, at the origin, 5 metres wide and 4
long, labelled "Living room". Add a room called kitchen, next to living on its
right side, 3 by 4 metres.* There is no coordinate anywhere, yet the drawing is
fully decided.

The script is three things at once:

1. **what the agent is about to do** -- you can read it before anything is drawn;
2. **the record of what it did** -- the same file, kept with the drawing;
3. **a document you can correct and run again** -- change `3 m` to `3.5 m`, run
   it, and the kitchen is wider and everything placed relative to it follows.

The model never writes this text. It fills a form (ADR 0005); the engine checks
the form and writes the line. You may edit the line yourself: a number you type
here is a number you dictated.

## The shape of a script

- The first line is always `linework script 1`.
- `domain <name>` says which trade the lines below belong to: `mechanical`,
  `architecture`, `civil`, `schematic`, or `general`. It stays in force until the
  next `domain` line.
- Every other line is one of:
  - **a statement** -- one decision, on one line;
  - **a comment** -- a line starting with `#`, kept as written;
  - **a blank line** -- kept as written, to group things.

## A statement

```
<act> <kind> <name>: <clause>, <clause>, ...  # why, optional
```

- **act** -- `add` (a new object), `change` (an existing one), `remove`.
- **kind** -- what it is: `plate`, `hole`, `room`, `window`, `pipe`, `resistor`...
  The full list, per trade, is in CATALOGUE.md.
- **name** -- your handle for it, so other lines can refer to it: lower-case
  letters, digits and `_`, starting with a letter (`wall_north`, `h1`).
- **clauses** -- after the colon, separated by commas, in any order.
- **why** -- anything after `#` is the reason for the decision. It is kept.

A clause is one of four things.

| Clause | Looks like | Example |
|---|---|---|
| a relation | where it goes, relative to something that exists | `centred on plate1` |
| a dimension | a size, with its unit | `width 120 cm` |
| a property | a choice from a fixed list | `thread M8` |
| a text | the words written on it, in quotes | `text "Kitchen"` |

### Numbers

Write numbers with a decimal **point**: `6.5`, not `6,5` -- in a script the comma
separates clauses. Lengths always carry their unit (`mm`, `cm`, `m`), angles
carry `deg`, and a count carries none (`sides 6`).

### Texts

In double quotes. To put a quote inside, write `\"`; a backslash is `\\`. A `#`
inside quotes is part of the text, not a comment.

## Where things go: the vocabulary of position

Every position is a relation to something that already exists. The very first
object has nothing to relate to, so it goes `at origin` -- the one name that
always exists.

| Relation | Means | Written |
|---|---|---|
| on | hosted by it: a window on a wall, a hole on a plate | `on wall_north` |
| inside | entirely within its outline | `inside plot1` |
| at | its reference point is the other's | `at origin` |
| centred on | its centre is the other's centre | `centred on plate1` |
| along | runs the whole length of it, optionally on one side | `along plot1 on side below` |
| offset from | at a distance from it, on a side | `offset from plate1 by 15 mm on side right` |
| next to | touching it, on a side | `next to living on side right` |
| between | spans from one to the other | `between mh1 and mh2` |
| aligned with | lined up with it, on an axis | `aligned with r1 on axis horizontal` |
| distributed over | that many copies, equally spaced over it | `distributed over plate1 in 4 copies` |

Sides are `left`, `right`, `above`, `below` -- directions on the sheet; axes are
`horizontal` and `vertical`.

### Measuring from an edge or a corner

A target may be followed by one of its edges (`top`, `bottom`, `left`,
`right`) or corners (`top_left`, `top_right`, `bottom_left`, `bottom_right`).
The relation then measures from that edge or corner, which is how a mechanical
drawing is dimensioned (decision D-003, ADR 0013). Only `at`, `centred on`,
`next to`, `offset from` and `aligned with` take them; `origin` is a point and
has none.

```linework
linework script 1
domain mechanical

add plate plate1: at origin, width 200 mm, height 120 mm
add hole h1: on plate1, offset from plate1 top by 15 mm on side below, offset from plate1 left by 20 mm on side right, diameter 10 mm
add hole h2: on plate1, offset from plate1 bottom by 12.5 mm on side above, offset from plate1 right by 8 mm on side left, diameter 6 mm
```

`h1` sits 15 mm under the top edge and 20 mm in from the left edge: its
extent is x 20 to 30, y 95 to 105, exactly.

## Where the first object goes, and what "next to" means

On a blank sheet "a 5 x 4 room" has no obvious *where*, and "next to it" has no
obvious *side*. The script answers both by rule, so nothing is ever guessed.

1. **The first object goes `at origin`**, the point (0, 0) of the sheet. When
   the model commits the first object of a drawing, it commits `at origin`.
2. **The sheet is the one frame**: x to the right, y up. `left`, `right`,
   `above`, `below` are directions on the sheet, never relative to an object's
   own rotation.
3. **Every object has a reference point**: the lower-left corner of rectangular
   things (rooms, plates, plots), the centre of round things and of schematic
   symbols, the start of the baseline of a text, the start of the axis of
   straight things (walls, roads, pipes, wires). `at` puts reference point on
   reference point.
4. **Every relation names its frame** -- what of the target it measures from,
   and which part of the object's position it fixes. The full table is in
   CATALOGUE.md; in short:
   - `at`, `centred on`, `between` fix the object both ways;
   - `next to X on side S` puts the object against X's edge on side S, touching
     it. That fixes it *across* the edge. *Along* the edge it is, by default,
     flush with X: at the left for `above`/`below`, at the bottom for
     `left`/`right`. `offset from X by D on side S` is the same with a gap D;
   - `aligned with X on axis horizontal` puts the centres at one height;
     `on axis vertical`, on one vertical line;
   - `along X` lies against an edge of X, or on its long axis;
     `distributed over X` spreads the copies along X's long axis;
   - `on` and `inside` place nothing: they say what the object belongs to, and
     check where it may be.
5. **"Beside", "by", "adjacent to"** are not script words. They all mean
   `next to`, and `next to` always names its side. If the user did not say
   which side, the model asks; it never picks one.
6. **Each object's left-right place and up-down place are decided exactly
   once.** A relation that fixes a direction firmly decides it; a default
   decides it only when nothing firm does. If nothing decides a direction, or two
   relations decide the same one, the script is refused -- with the line, and
   the relations involved.

So this script, which holds no coordinate at all, is one drawing and only one:

```linework
linework script 1
domain mechanical

add plate plate1: at origin, width 200 mm, height 120 mm
add hole h_c: on plate1, centred on plate1, diameter 10 mm
add hole h_r: on plate1, aligned with h_c on axis horizontal, offset from h_c by 30 mm on side right, diameter 6.5 mm
add hole h_t: on plate1, aligned with h_c on axis vertical, offset from h_c by 20 mm on side above, diameter 8 mm
```

The solver computes it exactly, in millimetres, the same to the last byte every
time:

```
# linework placement 1 -- millimetres, x right, y up, from origin
# name kind xmin ymin xmax ymax
plate1 plate 0 0 200 120
h_c hole 95 55 105 65
h_r hole 135 56.75 141.5 63.25
h_t hole 96 85 104 93
```

When a place is not decided, the script is refused instead of guessed:

```linework-unplaced
linework script 1
domain architecture
add room living: at origin, width 5 m, length 4 m
add room kitchen: width 3 m, length 4 m
# unplaced: line 4: "kitchen" has no place: say where it goes relative to something that exists (the first object goes at origin)
```

```linework-unplaced
linework script 1
domain architecture
add room living: at origin, width 5 m, length 4 m
add column c1: inside living, aligned with living on axis vertical, diameter 30 cm
# unplaced: line 4: the up-down place of "c1" is not determined; add a relation that fixes it, such as centred on, aligned with ... on axis horizontal, or offset from ... on side below
```

```linework-unplaced
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm, height 120 mm
add hole h1: on p1, centred on p1, offset from p1 by 10 mm on side right, diameter 8 mm
# unplaced: line 4: the left-right place of "h1" is fixed twice, by "centred on p1" and by "offset from p1 by 10 mm on side right"; keep one
```

```linework-unplaced
linework script 1
domain mechanical
add plate p1: at origin, width 100 mm, height 100 mm
add hole holes: on p1, distributed over p1 in 4 copies, offset from p1 by 10 mm on side above, diameter 8 mm
# unplaced: line 4: "distributed over p1 in 4 copies" needs the direction of "p1", which is not known: it is square, or its size is not given in the script
```

```linework-unplaced
linework script 1
domain architecture
add room living: at origin, width 5 m, length 4 m
add wall w_n: along living on side above
add window w1: on w_n, centred on w_n, width 120 cm
remove wall w_n
# unplaced: line 6: removing "w_n" leaves "w1" (line 5) without the object it is placed by; place it relative to something else first
```

## Worked examples

### Mechanical: a bracket

```linework
linework script 1
domain mechanical

# The plate the user sized; everything else is placed on it.
add plate plate1: at origin, width 200 mm, height 120 mm, thickness 10 mm
add threaded_hole hole_centre: on plate1, centred on plate1, thread M8, hole_type through
add hole holes_top: on plate1, distributed over plate1 in 4 copies, offset from hole_centre by 40 mm on side above, diameter 6.5 mm  # four fixing holes along the top
add slot adjust: on plate1, aligned with hole_centre on axis vertical, offset from hole_centre by 10 mm on side below, length 40 mm, width 8.5 mm
add fillet corners: on plate1, radius 5 mm, corner all
add chamfer cut: on plate1, length 3 mm, corner top_left
```

### Architecture: two rooms and their openings

```linework
linework script 1
domain architecture

add room living: at origin, width 5 m, length 4 m, text "Living room"
add room kitchen: next to living on side right, width 3 m, length 4 m, text "Kitchen"
add wall wall_north: along living on side above, thickness 30 cm
add wall wall_east: between living and kitchen
add window w1: on wall_north, centred on wall_north, width 120 cm  # sill and height from the standard
add door d1: on wall_east, centred on wall_east, width 90 cm, hinge_side left, swing inward
add column c1: inside living, aligned with w1 on axis vertical, offset from wall_north by 50 cm on side below, diameter 30 cm

# The user asked for a wider window, then for no door between the rooms.
change window w1: width 150 cm
remove door d1
add opening op1: on wall_east, centred on wall_east, width 120 cm
```

### Civil: a plot with a road, parking and a sewer

```linework
linework script 1
domain civil

add plot plot1: at origin, width 30 m, length 45 m, text "Plot 1"
add road road1: along plot1 on side below, width 6 m
add parking_bay bays: along road1 on side above, distributed over road1 in 12 copies  # bay size from the standard
add manhole mh1: inside plot1, offset from road1 by 2 m on side above, diameter 1 m, text "MH1"
add manhole mh2: next to mh1 on side right, diameter 1 m, text "MH2"
add pipe sewer1: between mh1 and mh2, diameter 300 mm, pipe_use sewer
```

### Schematic: a lamp and its switch

```linework
linework script 1
domain schematic

add terminal t_plus: at origin, text "+12V"
add switch s1: offset from t_plus by 20 mm on side right, orientation horizontal, text "S1"
add resistor r1: offset from s1 by 20 mm on side right, orientation horizontal, text "R1"
add lamp l1: offset from r1 by 20 mm on side right, aligned with r1 on axis horizontal, text "L1"
add wire n1: between t_plus and s1
add wire n2: between s1 and r1
add wire n3: between r1 and l1
add junction j1: on n2, centred on n2
```

### Several trades in one script

A `domain` line changes the trade for the lines that follow; names stay shared.

```linework
linework script 1
domain general

add rectangle frame: at origin, width 420 mm, height 297 mm

domain mechanical
add plate part: inside frame, centred on frame, width 120 mm, height 80 mm
add regular_polygon nut: on part, centred on part, sides 6, diameter 13 mm
```

`regular_polygon` belongs to `general`, which every trade may use.

## Open choices: "either this or that, to be decided"

A designer often has two good answers and needs the client to pick. The script
can hold both, side by side, without pretending one was chosen.

```linework
linework script 1
domain architecture

add room living: at origin, width 5 m, length 4 m
add wall wall_south: along living on side below
add wall wall_east: along living on side right

choice entrance: open  # Where does the front door go? The user has not said yet.
option entrance street: add door d1: on wall_south, centred on wall_south, width 90 cm  # closest to the street
option entrance garden: add door d1: on wall_east, centred on wall_east, width 90 cm  # opens on the garden
option entrance garden: add window w_garden: on wall_south, centred on wall_south, width 120 cm  # light where the door is not

change door d1: width 100 cm  # both options have a door d1, so it can be changed here
```

- `choice <name>: open` announces the choice; what follows `#` is the question,
  the design intent behind it.
- Each `option <choice> <label>: <statement>` line is one line of one
  alternative. An alternative may take several lines (`garden` has two). A choice
  has at least two alternatives, and its option lines come right after it.
- Each alternative is checked on its own, from the drawing as it is at the
  choice. After an **open** choice, only what every alternative agrees on exists:
  `d1` is a door in both, so the last line may change it; `w_garden` exists only
  in one, so nothing after the choice may name it yet.

**An open choice cannot be drawn.** Asked for geometry, the engine refuses and
says which choice is waiting, and between what:

```
line 8: cannot draw: choice "entrance" is still open -- options street, garden; decide it first
```

When the user decides, the engine changes one word -- `open` becomes
`decided <label>` -- and records why:

```linework
linework script 1
domain architecture

add room living: at origin, width 5 m, length 4 m
add wall wall_south: along living on side below
add wall wall_east: along living on side right

choice entrance: decided garden  # The user wants to step out onto the garden.
option entrance street: add door d1: on wall_south, centred on wall_south, width 90 cm  # closest to the street
option entrance garden: add door d1: on wall_east, centred on wall_east, width 90 cm  # opens on the garden
option entrance garden: add window w_garden: on wall_south, centred on wall_south, width 120 cm  # light where the door is not

add column c1: inside living, aligned with w_garden on axis vertical, offset from wall_south by 50 cm on side above, diameter 30 cm
```

Now the drawing follows `garden`, and `w_garden` exists for the lines after it.
The `street` alternative stays in the script: it is the record of what was
considered and turned down, and why -- the raw material of the judgement memory
(ADR 0002, phase 10).

## The free channel: what the language cannot say

Some shapes have no word in the catalogue -- the profile of a cam, a logo, the
outline of a hand sketch. For those there is one door out, and it is built so
that you always know when it was used. A `free` line carries a **shape**; its
**place** is still decided by the same checked relations as everything else.

```linework
linework script 1
domain mechanical

add plate plate1: at origin, width 200 mm, height 120 mm
add hole h1: on plate1, centred on plate1, diameter 8 mm
free cam: source user, centred on plate1, unit mm, shape "line 0 0 to 40 0; arc 0 0 radius 40 from 0 to 90; line 0 40 to 0 0"  # the user's cam profile: the catalogue has no word for it
free mark: source model, next to plate1 on side right, unit mm, shape "circle 0 0 radius 5"  # a datum mark the model proposed; there is no catalogue word for marks yet
```

The boundary of the free channel, all of it:

1. **Free is the shape, never the place.** A free object is placed by its local
   origin `0 0`, with `at`, `centred on`, `next to`, `offset from`,
   `aligned with` or `inside` -- checked and anchored like any object.
2. **It says where it came from**: `source user` (the user drew or dictated it),
   `source model` (the model proposed it), or `source import` (it came from a
   file the user named).
3. **It says why**: the `#` reason is required -- what the language could not
   say. A free line without one is refused.
4. **Its shape is plain**: parts separated by `;`, each `line X Y to X Y`,
   `circle X Y radius R`, or `arc X Y radius R from A to A` (degrees,
   counter-clockwise), in the `unit` given, at most 100 parts. The free channel
   is for what the language cannot say, not a second way to draw.
5. **Checked geometry never leans on free geometry.** A free object may be
   placed by checked objects; a checked object may never be placed by a free
   one, because its numbers would then come through the hole.
6. **It is never mixed with checked geometry on the way out.** In the computed
   drawing it sits in its own section, marked FREE with its source; on the DXF
   it goes on its own layer (phase 3); and `python3 -m lang.escape <script>`
   lists every free object on its own, for review:

```
# linework free channel -- 2 of 4 objects did not pass the gate; review each

cam  line 6  source user  3 parts  unit mm  placed: centred on plate1
  why: the user's cam profile: the catalogue has no word for it
  line 0 0 to 40 0
  arc 0 0 radius 40 from 0 to 90
  line 0 40 to 0 0

mark  line 7  source model  1 part  unit mm  placed: next to plate1 on side right
  why: a datum mark the model proposed; there is no catalogue word for marks yet
  circle 0 0 radius 5
```

A checked object placed by a free one:

```linework-refused
linework script 1
domain mechanical
add plate plate1: at origin, width 200 mm, height 120 mm
free cam: source user, centred on plate1, unit mm, shape "circle 0 0 radius 30"  # the user's cam
add hole h1: on plate1, centred on cam, diameter 8 mm
# refused: line 5: in "centred on cam": "cam" is free geometry, and checked geometry is never placed by it -- free may lean on checked, never the reverse
```

A free shape that does not say why:

```linework-refused
linework script 1
domain mechanical
add plate plate1: at origin, width 200 mm, height 120 mm
free cam: source user, centred on plate1, unit mm, shape "circle 0 0 radius 30"
# refused: line 4, column 80: a free object must say why the language could not say it: end the line with # and the reason
```

A free shape that does not say where it came from:

```linework-refused
linework script 1
domain mechanical
add plate plate1: at origin, width 200 mm, height 120 mm
free cam: centred on plate1, unit mm, shape "circle 0 0 radius 30"  # the user's cam
# refused: line 4, column 9: a free object must give its source
```

A free shape that tries to be a catalogue object:

```linework-refused
linework script 1
domain mechanical
add plate plate1: at origin, width 200 mm, height 120 mm
free cam: source model, on plate1, unit mm, shape "circle 0 0 radius 30"  # a cam
# refused: line 4, column 25: a free object is placed with at, centred on, next to, offset from, aligned with, inside; "on" would make it part of checked geometry
```

A part the free shape does not know:

```linework-refused
linework script 1
domain mechanical
add plate plate1: at origin, width 200 mm, height 120 mm
free cam: source user, centred on plate1, unit mm, shape "spline 0 0 10 10 20 0"  # a curve
# refused: line 4, column 58: in the shape, part 1 "spline 0 0 10 10 20 0": a part is "line X Y to X Y", "circle X Y radius R" or "arc X Y radius R from A to A" (degrees, counter-clockwise)
```

## When a script is refused

A script is checked from top to bottom against the drawing it builds as it
goes, and every error names its line -- and, for a mistake in the writing
itself, the column. Nothing is drawn from a script with an error.

A comma inside a number:

```linework-refused
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm, height 120 mm
add hole h1: on p1, diameter 6,5 mm
# refused: line 4, column 30: "6,5" is not a number here: write 6.5 -- in a script the comma separates clauses
```

A unit that does not measure what it is given for:

```linework-refused
linework script 1
domain architecture
add room r1: at origin, width 5 deg, length 4 m
# refused: line 3, column 33: "deg" is not a unit of width; use one of: cm, m, mm
```

Referring to something that does not exist yet:

```linework-refused
linework script 1
domain architecture
add window w1: on wall_north, width 120 cm
add wall wall_north: at origin, length 5 m
# refused: line 3: in "on wall_north": there is no object called "wall_north"; known objects: origin
```

A size that was never given:

```linework-refused
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm
# refused: line 3: a plate needs a height. If the user did not give one, ask: never guess a number
```

Two ends of a wire on the same symbol:

```linework-refused
linework script 1
domain schematic
add resistor r1: at origin, text "R1"
add wire n1: between r1 and r1
# refused: line 4: in "between r1 and r1": "r1" is named twice; "between" needs 2 different targets
```

A relation word spelled the American way:

```linework-refused
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm, height 120 mm
add hole h1: on p1, centered on p1, diameter 8 mm
# refused: line 4, column 21: a clause cannot start with "centered". Did you mean "centred"? It starts with a relation, a dimension, a property or text: aligned, along, angle, at, between, centred, corner, count, depth, diameter, distance, distributed, height, hinge_side, hole_type, inside, length, next, offset, on, orientation, pipe_use, radius, sides, sill_height, swing, text, thickness, thread, width
```

A choice decided for an option it does not have:

```linework-refused
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm, height 120 mm
choice fixing: decided rivets
option fixing bolts: add hole h1: on p1, centred on p1, diameter 9 mm
option fixing studs: add threaded_hole h1: on p1, centred on p1, thread M8
# refused: line 4: choice "fixing" is decided as "rivets", but its options are bolts, studs
```

A choice with nothing to choose between:

```linework-refused
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm, height 120 mm
choice fixing: open
option fixing bolts: add hole h1: on p1, centred on p1, diameter 9 mm
# refused: line 4: choice "fixing" needs at least two options to choose between; it has 1
```

Naming what exists in only one alternative of an open choice:

```linework-refused
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm, height 120 mm
choice fixing: open
option fixing bolts: add hole h1: on p1, centred on p1, diameter 9 mm
option fixing studs: add threaded_hole h2: on p1, centred on p1, thread M8
add slot s1: on p1, aligned with h1 on axis vertical, length 30 mm, width 6 mm
# refused: line 7: in "aligned with h1 on axis vertical": there is no object called "h1"; known objects: origin, p1
```

An option away from its choice:

```linework-refused
linework script 1
domain mechanical
add plate p1: at origin, width 200 mm, height 120 mm
choice fixing: open
option fixing bolts: add hole h1: on p1, centred on p1, diameter 9 mm
option fixing studs: add threaded_hole h1: on p1, centred on p1, thread M8
add slot s1: on p1, length 30 mm, width 6 mm
option fixing glue: add text t1: inside p1, text "glued"
# refused: line 8: the options of choice "fixing" must follow its choice line (line 4), with nothing but comments and blank lines in between
```

A statement before any domain:

```linework-refused
linework script 1
add plate p1: at origin, width 200 mm, height 120 mm
# refused: line 2: no domain yet: write "domain <name>" before the first statement
```

## The layout the engine writes

The engine always writes the same layout, so a script read and written back is
identical, character for character: single spaces, `: ` after the name, `, `
between clauses, two spaces before a trailing `#`, numbers in their shortest
form (`120`, not `120.0`), relation parameters in the order *by*, *on side*,
*on axis*, *in copies*. You may type looser spacing; it is read the same and
written back tidy.
