"""The engine core imports only the standard library (README, "Repository
layout"). tools/check_core_imports.py enforces it in CI; these tests prove the
check itself can fail, because a check that cannot fail is decoration.

Standard library only.
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import check_core_imports as cci  # noqa: E402


def _tree(files):
    root = tempfile.mkdtemp(prefix="lw-core-")
    for rel, body in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    return root


def test_the_real_repository_passes():
    problems, _ = cci.check()
    assert not problems, problems


def test_a_third_party_import_in_the_core_is_caught():
    root = _tree({"geometry/solver.py": "import math\nimport numpy as np\n"})
    problems, seen = cci.check(root)
    assert seen == 1
    assert len(problems) == 1 and "numpy" in problems[0] and ":2 " in problems[0]


def test_from_imports_are_caught_too():
    root = _tree({"engine/client.py": "from requests.adapters import HTTPAdapter\n"})
    problems, _ = cci.check(root)
    assert problems and "requests" in problems[0]


def test_stdlib_relative_and_first_party_imports_are_allowed():
    root = _tree({
        "lang/form.py": "import json, re\nfrom collections import OrderedDict\n"
                        "from . import catalogue\nfrom geometry import points\n",
        "lang/catalogue.py": "from __future__ import annotations\n",
    })
    problems, seen = cci.check(root)
    assert seen == 2 and not problems, problems


def test_ezdxf_is_allowed_outside_the_core_only():
    root = _tree({"dxf/write.py": "import ezdxf\n", "memory/store.py": "import ezdxf\n"})
    problems, seen = cci.check(root)
    assert seen == 1, "dxf/ must not be scanned"
    assert len(problems) == 1 and "memory" in problems[0]
