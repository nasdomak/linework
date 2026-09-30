# `geometry/`

The solver: relations and dictated numbers become exact coordinates.

The second of the two doors through which numbers enter (ADR 0001). Pure computation, no I/O beyond what the standard library offers.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library (no numpy, no sympy); dxf; tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `geometry/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".
