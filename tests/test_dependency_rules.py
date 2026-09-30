"""The monorepo layout and its import contracts (backlog task P0-T04).

The engine core -- engine/, lang/, geometry/, memory/ and shared/ -- imports
nothing outside the standard library; ezdxf lives only in dxf/ (and tools/).
tools/check_core_imports.py enforces the same rule in CI; this module is a
second, independent walk of the import statements, so one broken checker
cannot silently wave a violation through.

Standard library only: runs under pytest and under tools/run_tests.py.
"""

import ast
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORE = ("engine", "lang", "geometry", "memory", "shared")
PRODUCT = CORE + ("dxf",)
REQUIRED_DIRS = ("lang", "geometry", "dxf", "memory", "engine", "shared",
                 "tests", "tools", os.path.join("docs", "adr"),
                 os.path.join(".github", "workflows"))
STDLIB = set(sys.stdlib_module_names) | {"__future__"}


def _imports(path):
    """Every (line, top-level module) imported by a file, at any depth --
    including imports hidden inside functions and try blocks."""
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            yield node.lineno, node.module.split(".")[0]


def _py_files(root, pkg):
    for dirpath, _dirs, files in os.walk(os.path.join(root, pkg)):
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def violations(root=ROOT):
    """Return (problems, files_seen) for the dependency rules."""
    problems, seen = [], 0
    for pkg in PRODUCT:
        allowed = STDLIB | set(CORE) | ({"ezdxf"} if pkg == "dxf" else set())
        for path in _py_files(root, pkg):
            seen += 1
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            for line, top in _imports(path):
                if top not in allowed:
                    problems.append("%s:%d imports '%s'" % (rel, line, top))
    return problems, seen


# --------------------------------------------------------------- the layout

def test_every_directory_of_the_layout_exists():
    missing = [d for d in REQUIRED_DIRS if not os.path.isdir(os.path.join(ROOT, d))]
    assert not missing, "missing directories: %s" % missing


def test_every_product_package_states_its_contract_twice():
    for pkg in PRODUCT:
        init = os.path.join(ROOT, pkg, "__init__.py")
        readme = os.path.join(ROOT, pkg, "README.md")
        assert os.path.isfile(init), "%s/__init__.py missing" % pkg
        assert os.path.isfile(readme), "%s/README.md missing" % pkg
        with open(init, "r", encoding="utf-8") as fh:
            doc = ast.get_docstring(ast.parse(fh.read())) or ""
        with open(readme, "r", encoding="utf-8") as fh:
            text = fh.read()
        for source, body in (("__init__.py", doc), ("README.md", text)):
            assert re.search(r"May import:", body), "%s/%s: no 'May import'" % (pkg, source)
            assert re.search(r"May not import:", body), "%s/%s: no 'May not import'" % (pkg, source)
            if pkg in CORE:
                assert "standard library" in body and "CORE package" in body, (pkg, source)
            else:
                assert "ezdxf" in body, (pkg, source)


def test_the_readme_table_matches_the_packages():
    with open(os.path.join(ROOT, "README.md"), "r", encoding="utf-8") as fh:
        readme = fh.read()
    for pkg in CORE:
        row = re.search(r"^\| `%s/` \|.*\| (.+) \|$" % pkg, readme, re.M)
        assert row and row.group(1) == "standard library only", pkg
    row = re.search(r"^\| `dxf/` \|.*\| (.+) \|$", readme, re.M)
    assert row and "ezdxf" in row.group(1)


def test_the_ci_checker_guards_the_same_core():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import check_core_imports as cci
    finally:
        sys.path.pop(0)
    assert tuple(cci.CORE) == CORE


# --------------------------------------------------------------- the rule

def test_the_real_repository_obeys_the_dependency_rules():
    problems, seen = violations()
    assert seen >= len(PRODUCT), "the walk saw only %d files" % seen
    assert not problems, problems


# ------------------------------------ the rule can fail (a check that cannot is decoration)

def _tree(files):
    root = tempfile.mkdtemp(prefix="lw-deps-")
    for rel, body in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    return root


def test_a_third_party_import_in_each_core_package_is_caught():
    for pkg in CORE:
        root = _tree({pkg + "/x.py": "import os\nimport numpy\n"})
        problems, seen = violations(root)
        assert seen == 1 and problems == ["%s/x.py:2 imports 'numpy'" % pkg], problems


def test_the_core_may_not_reach_ezdxf_through_the_dxf_package_or_tools():
    root = _tree({"geometry/a.py": "from dxf import write\n",
                  "engine/b.py": "import tools.loop\n",
                  "memory/c.py": "import ezdxf\n"})
    problems, _ = violations(root)
    assert len(problems) == 3, problems


def test_an_import_hidden_in_a_function_is_caught():
    root = _tree({"lang/lazy.py": "def f():\n    try:\n        import requests\n"
                                  "    except ImportError:\n        pass\n"})
    problems, _ = violations(root)
    assert problems == ["lang/lazy.py:3 imports 'requests'"], problems


def test_dxf_may_use_ezdxf_and_the_core_but_nothing_else():
    root = _tree({"dxf/w.py": "import ezdxf\nfrom geometry import points\nimport json\n",
                  "dxf/bad.py": "import shapely\n"})
    problems, seen = violations(root)
    assert seen == 2 and problems == ["dxf/bad.py:1 imports 'shapely'"], problems


def test_relative_and_first_party_imports_are_allowed_in_the_core():
    root = _tree({"shared/s.py": "from __future__ import annotations\nfrom . import v1\n"
                                 "from lang import form\nimport collections.abc\n"})
    problems, _ = violations(root)
    assert not problems, problems
