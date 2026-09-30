#!/usr/bin/env python3
"""
check_core_imports.py -- the engine core imports nothing outside the standard
library. CI runs this on every push, so the rule cannot erode in a hurry.

    python tools/check_core_imports.py           check, exit 1 on a violation
    python tools/check_core_imports.py --list    also print every import seen

The core packages are engine/, lang/, geometry/, memory/ and shared/. They may
import the Python standard library and each other, and nothing else. ezdxf is
allowed only in dxf/ and tools/ -- see README.md, "Repository layout".

The check reads the source with `ast`; it never imports the code, so a broken
module is reported rather than crashing the check. A package that does not exist
yet is simply absent: before product phase 0 lays out the directories this check
passes with "no core package present yet", which is true and says so.
"""

import argparse
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = ("engine", "lang", "geometry", "memory", "shared")

# sys.stdlib_module_names exists from Python 3.10. CI runs 3.11 and 3.13.
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}


def imports_of(path):
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level:            # relative import: first-party by definition
                continue
            if node.module:
                yield node.lineno, node.module.split(".")[0]


def check(root=ROOT, listing=False):
    if not STDLIB:
        return ["this Python has no sys.stdlib_module_names; run with 3.10 or later"], 0
    problems, seen = [], 0
    for pkg in CORE:
        base = os.path.join(root, pkg)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, root)
                seen += 1
                try:
                    found = list(imports_of(path))
                except SyntaxError as exc:
                    problems.append("%s: cannot be parsed (%s)" % (rel, exc))
                    continue
                for line, top in found:
                    if listing:
                        print("%s:%s imports %s" % (rel, line, top))
                    if top in STDLIB or top in CORE:
                        continue
                    problems.append("%s:%s imports '%s', which is not in the standard "
                                    "library" % (rel, line, top))
    return problems, seen


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    problems, seen = check(listing=args.list)
    if problems:
        print("CORE IMPORT CHECK FAILED (%d)" % len(problems))
        for p in problems:
            print("  - %s" % p)
        return 1
    if seen == 0:
        print("core import check passed: no core package present yet "
              "(%s)." % ", ".join(CORE))
    else:
        print("core import check passed: %d files, standard library only." % seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
