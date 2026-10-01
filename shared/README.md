# `shared/`

Versioned schemas shared by every other package.

Data definitions only: the contracts between the form, the solver, the memory and the DXF layer.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library; dxf; tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `shared/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".

## What is here

- `catalogue_v1.json` -- the closed vocabulary of the commitment form, one entry
  per word with its meaning (ADR 0005). Edited by hand.
- `catalogue.py` -- loads it and checks it is internally consistent.
- `form_schema_v1.json` -- the JSON Schema of the form. **Generated** by
  `python3 -m lang.form write`; never edit it by hand. The readable list of words
  is `docs/CATALOGUE.md`, generated the same way.
