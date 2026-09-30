"""The repository has a shape the plan depends on: a licence, the founding ADRs,
the CI workflow. These tests are the verification step of backlog tasks P0-T01,
P0-T02, P0-T03 and part of P0-T05.

Standard library only, so they run anywhere -- with pytest, or with
tools/run_tests.py where pytest is not installed.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADR = os.path.join(ROOT, "docs", "adr")

TWO_DOORS = ("Numbers enter through two doors only: the user dictates them, "
             "or the solver computes them.")


def read(*parts):
    with open(os.path.join(ROOT, *parts), "r", encoding="utf-8") as fh:
        return fh.read()


def spdx_in(text):
    m = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)", text)
    return m.group(1) if m else None


# ------------------------------------------------------------ P0-T01, licence

def test_licence_file_is_the_gpl_version_2():
    text = read("LICENSE")
    assert "GNU GENERAL PUBLIC LICENSE" in text
    assert "Version 2, June 1991" in text
    # The whole text, not a stub: the GPL v2 is about 18 kB.
    assert len(text) > 15000, "LICENSE looks truncated (%d bytes)" % len(text)


def test_licence_adr_names_the_same_licence_as_the_licence_file():
    adr = read("docs", "adr", "0004-licence.md")
    spdx = spdx_in(adr)
    assert spdx == "GPL-2.0-or-later", spdx
    # GPL-2.0-* must go with a version 2 LICENSE text.
    assert spdx.startswith("GPL-2.0") and "Version 2, June 1991" in read("LICENSE")


def test_licence_adr_says_what_the_engine_may_be_and_the_plugin_must_be():
    adr = read("docs", "adr", "0004-licence.md")
    assert "The engine may be" in adr
    assert "The plugin must be" in adr


def test_readme_states_the_same_licence():
    assert spdx_in(read("README.md")) == spdx_in(read("docs", "adr", "0004-licence.md"))


# ------------------------------------------------------------ P0-T02, ADR 0001

def test_adr_0001_exists_and_states_the_two_doors_rule_verbatim():
    text = read("docs", "adr", "0001-thinking-is-free-the-hand-is-guided.md")
    assert len(text) > 2000
    assert TWO_DOORS in text
    assert "never emits executable text and never a final coordinate" in text
    for stage in ("FREE REASONING", "design decision", "validated structured intent",
                  "readable script", "geometry (DXF)"):
        assert stage in text, "pipeline stage missing: %s" % stage


# ------------------------------------------------------------ P0-T03, ADR 0002

def test_adr_0002_names_both_layers_and_all_three_channels():
    text = read("docs", "adr", "0002-the-memory-model.md")
    for needle in ("Layer 1", "the standard", "Layer 2", "the judgement",
                   "first-run interview", "Learning while working",
                   "Deduction from the user's own drawings",
                   "provenance", "never model weights",
                   "The script says *what*; the memory says *how*."):
        assert needle.lower() in text.lower(), "ADR 0002 does not mention: %s" % needle


# ------------------------------------------------------------ the ADR index

def test_every_adr_is_listed_in_the_index():
    index = read("docs", "adr", "README.md")
    for name in sorted(os.listdir(ADR)):
        if re.match(r"^\d{4}-.*\.md$", name):
            assert name in index, "%s is not in docs/adr/README.md" % name


# ------------------------------------------------------------ P0-T05, CI

def test_ci_workflow_covers_three_systems_and_the_enforced_checks():
    ci = read(".github", "workflows", "ci.yml")
    for os_name in ("ubuntu-latest", "windows-latest", "macos-latest"):
        assert os_name in ci, os_name
    for step in ("tools/loop.py check", "tools/sync_plan.py check",
                 "tools/check_core_imports.py", "pytest",
                 "actions/upload-artifact"):
        assert step in ci, "CI does not run: %s" % step
