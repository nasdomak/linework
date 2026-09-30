"""The plan must stay coherent, because a session trusts it at three in the
morning with nobody watching.

These tests need no CAD, no Ollama and no network.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")


def load(name):
    with open(os.path.join(STATE, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_loop_check_passes():
    """tools/loop.py check is the single gate on plan integrity: unique ids,
    known phases, resolvable dependencies, no cycles, a definition of done and
    a verification for every task."""
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "loop.py"),
                           "check"],
                          stdin=subprocess.DEVNULL, capture_output=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout.decode() + proc.stderr.decode()


def test_every_task_has_a_way_to_verify_itself():
    """Verification comes first, autonomy second. A task the agent cannot check
    by itself must not exist in the plan."""
    for task in load("backlog.json")["tasks"]:
        assert task["verification"].strip(), "%s has no verification" % task["id"]
        assert task["definition_of_done"], "%s has no DoD" % task["id"]
        for item in task["definition_of_done"]:
            assert item.strip()


def test_every_task_says_why_it_exists():
    """A backlog of titles is a to-do list. A backlog that says why is a plan
    a fresh session can act on without asking."""
    for task in load("backlog.json")["tasks"]:
        assert len(task["why"]) > 40, "%s does not explain itself" % task["id"]


def test_phases_are_contiguous_and_all_populated():
    backlog = load("backlog.json")
    ids = sorted(p["id"] for p in backlog["phases"])
    assert ids == list(range(len(ids))), "phase numbers must be 0..N"
    populated = {t["phase"] for t in backlog["tasks"]}
    missing = set(ids) - populated
    assert not missing, "phases with no tasks: %s" % sorted(missing)


def test_task_ids_match_their_phase():
    for task in load("backlog.json")["tasks"]:
        assert task["id"].startswith("P%s-" % task["phase"]), \
            "%s is in phase %s" % (task["id"], task["phase"])


def test_state_is_consistent_with_the_backlog():
    state, backlog = load("state.json"), load("backlog.json")
    ids = {t["id"] for t in backlog["tasks"]}
    if state.get("current_task"):
        assert state["current_task"] in ids
    phases = {p["id"] for p in backlog["phases"]}
    assert state["current_phase"] in phases
    assert state["gate_width"] in state["gate_width_options"]


def test_open_decisions_carry_a_default_and_a_reason():
    """The loop never blocks on a question and never guesses silently: every
    open question must already have a proposal and the reasoning behind it."""
    for d in load("decisions.json")["open"]:
        assert d["proposed_default"].strip(), "%s has no default" % d["id"]
        assert len(d["rationale"]) > 30, "%s has no rationale" % d["id"]
        assert isinstance(d["reversible"], bool)


def test_irreversible_decisions_block_rather_than_default():
    """An irreversible decision must name what it blocks, otherwise nothing
    stops the loop from walking past it."""
    for d in load("decisions.json")["open"]:
        if not d["reversible"]:
            assert d.get("blocks"), \
                "%s is irreversible but blocks nothing" % d["id"]
