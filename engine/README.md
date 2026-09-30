# `engine/`

The orchestrator, and the client that talks to a local Ollama.

The Ollama client uses urllib from the standard library; no HTTP library is added.

- **May import:** the standard library, and the other core packages (engine, lang, geometry, memory, shared).
- **May not import:** anything outside the standard library (no requests, no ollama package); dxf; tools.

CORE package: tools/check_core_imports.py and tests/test_dependency_rules.py enforce the standard-library-only rule in CI.

The same contract is stated in `engine/__init__.py`; the repository table is in
the root `README.md`, "Repository layout".
