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
| offset from | at a distance from it, on a side | `offset from plate1 by 15 mm on side inside` |
| next to | touching it, on a side | `next to living on side right` |
| between | spans from one to the other | `between mh1 and mh2` |
| aligned with | lined up with it, on an axis | `aligned with r1 on axis horizontal` |
| distributed over | that many copies, equally spaced over it | `distributed over plate1 in 4 copies` |

Sides are `left`, `right`, `above`, `below`, `inside`, `outside`; axes are
`horizontal` and `vertical`.

## Worked examples

### Mechanical: a bracket

```linework
linework script 1
domain mechanical

# The plate the user sized; everything else is placed on it.
add plate plate1: at origin, width 200 mm, height 120 mm, thickness 10 mm
add threaded_hole hole_centre: on plate1, centred on plate1, thread M8, hole_type through
add hole holes_top: on plate1, distributed over plate1 in 4 copies, offset from plate1 by 15 mm on side inside, diameter 6.5 mm  # four fixing holes along the top
add slot adjust: on plate1, aligned with hole_centre on axis vertical, length 40 mm, width 8.5 mm
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
add column c1: inside living, aligned with w1 on axis vertical, diameter 30 cm

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
add junction j1: on n2
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
