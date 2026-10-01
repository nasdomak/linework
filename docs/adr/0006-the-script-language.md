# ADR 0006 — The script language

- **Status:** accepted
- **Date:** 2026-10-01
- **Builds on:** ADR 0001 (thinking is free, the hand is guided), ADR 0005 (the commitment form)
- **Backlog:** P1-T02
- **Specification:** `docs/SCRIPT.md`

## Context

ADR 0001 makes the script three things at once: what the agent will do, the
record of what it did, and the document a human corrects and re-runs. Memory,
undo, reproducibility and audit collapse into one artefact. So the script must be
readable by someone who has never programmed, exact enough to be re-run, and
unable to say anything the form (ADR 0005) cannot say.

## Decision

### One line, one form

A script is plain text. The first line is `linework script 1`; `domain <name>`
sets the trade for the lines below; every other line is a comment (`#`), a blank
line, or a **statement** — exactly one commitment form written as a sentence:

```
add window w1: on wall_north, centred on wall_north, width 120 cm  # sill from the standard
```

`<act> <kind> <name>`, a colon, then clauses separated by commas, in any order,
then optionally `#` and the reason. A clause is a relation (`centred on
wall_north`), a dimension (`width 120 cm`), a property (`thread M8`) or a text
(`text "Kitchen"`). Every word is a catalogue word; relations are written with
their underscore as a space, and their parameters in one fixed phrasing each:
`by <distance>`, `on side <side>`, `on axis <axis>`, `in <n> copies`.

There is no syntax for a coordinate, a variable, an expression, a loop or a
condition. The script is a list of decisions, not a program. Repetition is a
relation (`distributed over plate1 in 4 copies`); arithmetic is the solver's.

### The engine writes it; a person may edit it

`from_forms` writes lines **only** from forms the gate accepts, and raises
otherwise. A person editing the file is dictating, so a number typed into the
script is a number through the first door: when a line becomes a form again, the
clause itself is its `said`. The model never writes script text.

### Exact round-trip in one canonical layout

The engine always writes the same layout: single spaces, `: ` after the name,
`, ` between clauses, two spaces before a trailing `#`, numbers in their shortest
form, parameters in a fixed order. Text in that layout prints back character for
character; looser text is read the same and printed tidy. Comments and blank
lines are kept. The order of clauses is kept as written.

### Checked top to bottom, every error at its line

`check` turns each statement into a form and validates it against the drawing the
script has built so far: names, targets and hosts must exist **at that line**.
A refused line does not create its object, so a later line that names it is
reported too. Errors in the writing carry line and column; errors of meaning
carry the line and quote the clause (`line 4: in "on p1": ...`).

## Consequences

- The vocabulary of position the plan asks for — centred on, along, offset from,
  between, aligned with, distributed over — is the catalogue's relations, written
  as words; the specification uses every relation at least once.
- Intent and open alternatives (P1-T03, ADR 0007), anchoring rules (P1-T04) and the escape
  hatch (P1-T05) extend this grammar; each will need a new statement shape, and
  `linework script 1` stays readable by later versions.
- Decimal commas cannot be used inside a script (the comma separates clauses);
  `6,5` is refused with the exact correction. The form still accepts what the
  user typed with a comma — that is the user's text, not the script.

## Verification

`tests/test_script.py` (P1-T02): every example in `docs/SCRIPT.md` round-trips
exactly and checks clean; every refused example fails with the exact error it
states; the specification covers every relation, every act and all four trades;
every accepted form example becomes a line and reads back as the same form; a
refused form is never written; 20 malformed lines each produce their exact
line-and-column error; 2,000 randomly damaged scripts never crash the parser and
print stably. Breaking the printer, the line numbering, a parameter phrase or the
refused-line rule on purpose makes the suite fail.
