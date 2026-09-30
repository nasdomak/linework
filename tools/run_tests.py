#!/usr/bin/env python3
"""
run_tests.py -- run the plain-assert tests without pytest.

Why this exists: the shells a session can reach are not always able to install
pytest (on 30/09/2026 PyPI answered 403 both in the cloud container and in the
device_bash VM on Marco's machine). A task whose verification cannot run is not
verified, so the tests that need nothing but the standard library can always be
run with this, anywhere:

    python tools/run_tests.py            every tests/test_*.py
    python tools/run_tests.py test_plan  one module

It runs every zero-argument `test_*` function. A module that cannot be imported
because a third-party package is missing (pytest, ezdxf, ...) is reported as
SKIPPED with the reason -- never as passed. Tests that take pytest fixtures are
skipped the same way. CI runs the full suite with real pytest; this is the
fallback, not a replacement.

Exit codes: 0 all run tests passed, 1 a failure, 2 nothing was run.
"""

import importlib.util
import inspect
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")


def main(argv):
    wanted = set(argv)
    passed, failed, skipped = [], [], []
    for name in sorted(os.listdir(TESTS)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        mod_name = name[:-3]
        if wanted and mod_name not in wanted:
            continue
        spec = importlib.util.spec_from_file_location(mod_name, os.path.join(TESTS, name))
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except ImportError as exc:
            skipped.append("%s (module needs %s)" % (mod_name, exc.name or exc))
            continue
        for fname, fn in inspect.getmembers(module, inspect.isfunction):
            if not fname.startswith("test_") or fn.__module__ != mod_name:
                continue
            if inspect.signature(fn).parameters:
                skipped.append("%s::%s (needs pytest fixtures)" % (mod_name, fname))
                continue
            try:
                fn()
                passed.append("%s::%s" % (mod_name, fname))
            except Exception:
                failed.append(("%s::%s" % (mod_name, fname), traceback.format_exc()))

    for label, _ in failed:
        print("FAILED  %s" % label)
    for label in skipped:
        print("SKIPPED %s" % label)
    for _, tb in failed:
        print("")
        print(tb)
    print("%d passed, %d failed, %d skipped" % (len(passed), len(failed), len(skipped)))
    if failed:
        return 1
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
