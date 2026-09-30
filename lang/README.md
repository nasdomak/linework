# `lang/`

The form and the script language -- the bridle on the hand (ADR 0001).

The model fills a closed form; this package validates it and turns it into a readable script. It never computes a final coordinate: that is the solver's door.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library; dxf (it pulls in ezdxf); tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `lang/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".
