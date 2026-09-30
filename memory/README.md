# `memory/`

The two-layer memory: layer 1 the standard, layer 2 the judgement (ADR 0002).

Plain files with provenance, never model weights.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library (no database drivers, no vector stores); dxf; tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `memory/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".
