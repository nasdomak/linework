"""docs/ACTION_PLAN.md and state/backlog.json must not drift apart.
tools/sync_plan.py check is wired into CI; these tests prove it catches each
kind of drift, because a check that cannot fail is decoration.

Standard library only.
"""

import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import sync_plan  # noqa: E402


def _real():
    with open(sync_plan.DOC, encoding="utf-8") as fh:
        doc = fh.read()
    with open(sync_plan.BACKLOG, encoding="utf-8") as fh:
        backlog = json.load(fh)
    return doc, backlog


def test_the_repository_is_in_sync():
    doc, backlog = _real()
    assert sync_plan.check(doc, backlog) == []


def test_a_renamed_phase_is_caught():
    doc, backlog = _real()
    b = copy.deepcopy(backlog)
    b["phases"][3]["title"] = "Something else entirely"
    problems = sync_plan.check(doc, b)
    assert any("phase 3" in p and "titled" in p for p in problems), problems


def test_a_phase_missing_from_the_doc_is_caught():
    doc, backlog = _real()
    b = copy.deepcopy(backlog)
    b["phases"].append({"id": 18, "title": "Afterlife", "gate": True, "summary": "x"})
    problems = sync_plan.check(doc, b)
    assert any("phase 18" in p for p in problems), problems


def test_a_new_task_makes_the_index_stale():
    doc, backlog = _real()
    b = copy.deepcopy(backlog)
    extra = copy.deepcopy(b["tasks"][0])
    extra["id"], extra["title"] = "P0-T99", "A task added to the backlog only"
    b["tasks"].append(extra)
    problems = sync_plan.check(doc, b)
    assert any("stale" in p for p in problems), problems


def test_a_hand_edit_of_the_index_is_caught():
    doc, backlog = _real()
    edited = doc.replace("Decide the licence and record it in an ADR",
                         "Decide the licence someday")
    assert edited != doc
    problems = sync_plan.check(edited, backlog)
    assert any("stale or hand-edited" in p for p in problems), problems


def test_a_status_change_does_not_churn_the_doc():
    """Finishing a task must not make CI fail: status is not in the index."""
    doc, backlog = _real()
    b = copy.deepcopy(backlog)
    for t in b["tasks"]:
        t["status"] = "done"
    assert sync_plan.check(doc, b) == []


def test_an_italic_aside_in_a_heading_is_ignored():
    assert sync_plan.normalise("The language *(the most important artefact)*") == "The language"
    assert sync_plan.normalise("The LibreCAD live window (C++ plugin)") == \
        "The LibreCAD live window (C++ plugin)"
