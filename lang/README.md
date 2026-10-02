# `lang/`

The form and the script language -- the bridle on the hand (ADR 0001).

The model fills a closed form; this package validates it and turns it into a readable script. It never computes a final coordinate: that is the solver's door.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library; dxf (it pulls in ezdxf); tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `lang/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".

## What is here

- `form.py` -- the commitment form (ADR 0005): `validate(form, user_text, known)`
  refuses anything outside the catalogue with a readable reason. Also
  `python3 -m lang.form write|verify|check`.
- `script.py` -- the script language (ADR 0006): `parse`, `check`, `from_forms`;
  `python3 -m lang.script check FILE...`. Specification: `docs/SCRIPT.md`.
- `anchoring.py` -- the blank page (ADR 0008): which relation fixes each
  direction of every object; refuses what is not determined, fixed twice or
  suggested twice; `place()` hands the plan to `geometry/placement.py`.
- `escape.py` -- the free channel listed for review (ADR 0009):
  `python3 -m lang.escape FILE...`.
- `examples/forms/` -- worked forms in the four domains, accepted and refused,
  each refusal stated word for word. Checked by `tests/test_form.py`.
