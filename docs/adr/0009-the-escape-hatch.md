# ADR 0009 — The escape hatch and its boundary

- **Status:** accepted
- **Date:** 2026-10-02
- **Builds on:** ADR 0001 (thinking is free, the hand is guided), ADR 0006, ADR 0008
- **Backlog:** P1-T05 (open issue B)
- **Specification:** `docs/SCRIPT.md`, "The free channel"

## Context

No closed vocabulary covers everything: a cam profile, a logo, a hand sketch.
Without a way out, the user is stuck, or the model bends a catalogue word to mean
something it does not. But a free channel is the hole in the fence ADR 0001
builds: whatever comes through it has not been checked. So its boundary has to be
designed, and everything that crosses it has to stay visible.

## Decision

A `free` line carries a shape the language cannot say:

```
free cam: source user, centred on plate1, unit mm, shape "line 0 0 to 40 0; arc 0 0 radius 40 from 0 to 90; line 0 40 to 0 0"  # the user's cam profile
```

The boundary:

1. **Free is the shape, never the place.** A free object is placed by its local
   origin with `at`, `centred on`, `next to`, `offset from`, `aligned with` or
   `inside`, checked and anchored (ADR 0008) like any object. `on`, `along`,
   `between` and `distributed over` are refused: they would make it part of
   checked geometry.
2. **Provenance is mandatory**: `source user`, `source model` or
   `source import`.
3. **The reason is mandatory**: the `#` comment says what the language could not
   say. Without it the line is refused.
4. **The shape is plain and bounded**: `line`, `circle`, `arc` parts in a stated
   unit, at most 100 per object.
5. **Taint flows one way.** A free object may be placed by checked or free
   objects; a checked object may never be placed by a free one -- its numbers
   would come through the hole. Refused with the line and the clause.
6. **Never mixed on the way out.** Free objects are a separate item type in the
   script (`Script.free()`, never in `statements()`); the placement text puts
   them in their own section marked FREE with their source; the DXF writer
   (phase 3) puts them on their own layer; `lang/escape.py` lists them on their
   own for review -- source, line, reason, placement, every part.

Free objects cannot be changed or removed by statements: to change one, edit its
line. They cannot appear inside a choice's options.

## Consequences

- The model will be able to use the channel (phase 5), but only through a
  separate commitment with `source model`, always listed for the user.
- The share of a drawing that came through the hatch is visible at a glance
  ("2 of 4 objects did not pass the gate"); a vocabulary gap that keeps sending
  things through it is a signal to add catalogue words (phase 13).
- An `import` source names a file the user gave; reading DXF in is phase 3.

## Verification

`tests/test_escape_hatch.py` (P1-T05): free lines are flagged by keyword, source
and reason and round-trip; a free line missing its source, unit, shape or reason,
or with an unknown source, a duplicate, a catalogue word, a zero radius or a
decimal comma is refused at its line and column; the 100-part ceiling holds; no
relation lets a checked object be placed by a free one; free geometry is anchored
like everything else; the output keeps free objects in their own FREE section;
the review list equals the one `docs/SCRIPT.md` quotes; 200 random scripts mixing
checked and free lines always list and mark every free object and never a
checked one. Disabling the taint rule, the reason rule, the separate output
section, the source marking, the drawing of free objects or the part ceiling on
purpose makes the suite fail.
