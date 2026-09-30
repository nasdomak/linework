"""The phase gate of the loop stops it at every phase boundary until Marco
says "vai". The first unattended run (30/09/2026) found that finishing the
last task of a phase advanced current_phase, which the gate compared against,
so the loop would have walked straight into the next phase. These tests pin
the corrected behaviour.

Standard library only.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import loop  # noqa: E402


def _plan():
    backlog = {
        "phases": [{"id": 0, "title": "zero", "gate": True},
                   {"id": 1, "title": "one", "gate": True}],
        "tasks": [
            {"id": "A", "phase": 0, "status": "done", "depends_on": []},
            {"id": "B", "phase": 1, "status": "todo", "depends_on": ["A"]},
        ],
    }
    decisions = {"open": [], "settled": []}
    return backlog, decisions


def _task(backlog, tid):
    return [t for t in backlog["tasks"] if t["id"] == tid][0]


def test_a_finished_phase_does_not_open_the_next_one():
    backlog, _ = _plan()
    # What `finish` leaves behind after the last task of phase 0.
    state = {"gate_width": "phase", "current_phase": 1, "open_phase": 0}
    gate, why = loop.crosses_gate(state, _task(backlog, "B"), backlog)
    assert gate and "phase 1" in why


def test_vai_opens_the_gate_and_only_that_gate():
    backlog, decisions = _plan()
    state = {"gate_width": "phase", "current_phase": 1, "open_phase": 0}
    assert loop.open_gate(state, backlog, decisions) == 1
    assert state["open_phase"] == 1
    gate, _ = loop.crosses_gate(state, _task(backlog, "B"), backlog)
    assert not gate
    # Saying it again changes nothing.
    assert loop.open_gate(state, backlog, decisions) is None


def test_work_inside_an_open_phase_is_not_gated():
    backlog, _ = _plan()
    _task(backlog, "B")["phase"] = 0
    state = {"gate_width": "phase", "current_phase": 0, "open_phase": 0}
    gate, _ = loop.crosses_gate(state, _task(backlog, "B"), backlog)
    assert not gate


def test_run_width_never_gates_and_task_width_always_does():
    backlog, _ = _plan()
    b = _task(backlog, "B")
    assert loop.crosses_gate({"gate_width": "run", "open_phase": 0}, b, backlog)[0] is False
    assert loop.crosses_gate({"gate_width": "task", "open_phase": 5}, b, backlog)[0] is True


def test_a_state_without_open_phase_falls_back_to_current_phase():
    assert loop.open_phase({"current_phase": 3}) == 3
    assert loop.open_phase({}) == 0
