# `shared/`

Versioned schemas shared by every other package.

Data definitions only: the contracts between the form, the solver, the memory and the DXF layer.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library; dxf; tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `shared/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".
