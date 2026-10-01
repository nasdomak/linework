# ADR 0005 — The commitment form

- **Status:** accepted
- **Date:** 2026-10-01
- **Builds on:** ADR 0001 (thinking is free, the hand is guided), ADR 0002 (the memory model)
- **Backlog:** P1-T01

## Context

ADR 0001 says the model commits through a narrow gate: a form with fixed fields
and values from closed lists, refused with a readable reason when it does not fit.
This ADR fixes what that form is. It is the first half of the bridle: the script
language (P1-T02) is written by the engine *from* validated forms, so whatever the
form cannot say, the script will never be asked to say.

Too rich, and the bridle is gone. Too narrow, and nothing useful can be said. The
choices below aim at the narrowest form that still carries a whole drawing in the
four domains of the plan.

## Decision

### One form, one decision

A form commits **one act on one object**:

```json
{
  "form": "linework/commitment", "version": 1,
  "domain": "architecture", "act": "add",
  "object": {"kind": "window", "name": "w1"},
  "relations": [{"relation": "on", "to": ["wall_north"]},
                {"relation": "centred_on", "to": ["wall_north"]}],
  "dimensions": {"width": {"value": 120, "unit": "cm", "said": "width 120"}},
  "reason": "Sill and height come from the standard in memory."
}
```

Fixed fields: `form`, `version`, `domain`, `act`, `object` (`kind`, `name`), and
optionally `relations`, `dimensions`, `properties`, `text`, `reason`. Nothing else
is accepted at any level.

### Every word comes from the catalogue

`shared/catalogue_v1.json` is the closed vocabulary: domains, acts, units,
quantities, relations and their parameters, properties and their values, object
kinds, reserved names. **One entry per word, each with its meaning.** The
catalogue also says, per object kind, which dimensions are required, optional, or
taken from memory, which properties it has, what must host it, and whether it
carries text. The readable version is `docs/CATALOGUE.md`; the JSON Schema is
`shared/form_schema_v1.json`. Both are generated from the catalogue, and CI fails
if they disagree with it.

Version 1 holds 5 domains (the four of the plan plus `general`), 3 acts, 4 units,
12 quantities, 10 relations, 7 properties and 30 object kinds. It is a start, not
a ceiling: phase 13 grows the domain vocabularies, each loaded only when needed.

### No field is a coordinate

There is no field for a point, and fields named like one (`x`, `y`, `position`,
`start`, `centre`, ...) are refused with their own message: *state a relation
instead*. Where an object goes is said only by relations to objects that exist.
The first object of a drawing is placed `at` the reserved name `origin`.

### The first door, enforced

Every number carries `said`: the user's own words. The validator refuses a number
that does not appear in them, and a unit other than the one written next to the
number. The model copies; it never converts, never rounds, never guesses.
A required dimension the user did not give is refused with "ask: never guess a
number". Dimensions marked *memory* may be left out: the solver fills them from
the drawing standard (ADR 0002), which is the second door.

Numbers are recognised as the user writes them: `120`, `1,20` and `1.20`,
`1,500`, and small whole numbers written as words in English or Italian
(`twelve`, `dodici`, up to twenty, and "a dozen"). A word for a number is as exact
as its digits, and refusing "four holes" would push the model to rephrase the
user, which is the opposite of the rule.

Known limit, accepted: the check proves the number was *said*, not that it was
said *for this dimension*. "120 x 80", committed as width 80 and height 120,
passes. That error is visible in the readable script and in the picture, which is
where phase 2 and phase 12 check it; the form cannot know which number the user
meant for which side without parsing the user, which is the model's job.

### The validator refuses, explains, and never repairs

`lang.form.validate(form, user_text, known)` returns every problem at once, each
with a stable code, the path to the field, and a sentence written for the model to
act on — including "Did you mean ...?" and the list of words it may use instead.
When the drawing is given (`known`: name → kind), names, targets and hosts are
checked against it: adding an existing name, changing a missing object, a window
on a plate, a wire whose two ends are the same. The validator never raises: a form
it cannot read is refused.

## Consequences

- P1-T02 writes script lines **only** from forms this validator accepts. The
  vocabulary of position the script must cover is already here as relations:
  `centred_on`, `along`, `offset_from`, `between`, `aligned_with`,
  `distributed_over` (plus `on`, `inside`, `next_to`, `at`).
- The schema can be handed to a model runtime that forces JSON output (phase 5).
  It is never looser than the validator: whatever the schema refuses, the
  validator refuses (tested).
- Adding a word means editing the catalogue, regenerating, and adding an example.
  Changing what a field *is* means a new form version and a new ADR.
- Open: whether intent and alternatives (P1-T03) travel in this form or in the
  script. Expected: in the script, since a form is one committed decision.

## Verification

`tests/test_form.py` (P1-T01): the catalogue is consistent and every word has a
meaning; the generated files are current; the schema is closed and never looser
than the validator; 37 worked examples in `lang/examples/forms/` — accepted and
refused, in all four domains — behave as they say, with every refusal checked word
for word; more than 30 single-fault forms produce their exact message;
coordinate fields are refused wherever they are hidden; 1,500 randomly damaged
forms are refused without a crash. Breaking the validator on purpose (dropping the
number check, the coordinate trap, the duplicate-target or the host check) makes
the suite fail.
