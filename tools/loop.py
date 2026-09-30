#!/usr/bin/env python3
"""
loop.py -- the state machine of the development loop.

The plan is executable: this is the program a session runs instead of asking
what to do. Standard library only, so it runs anywhere the project runs.

    py tools/loop.py status          what is going on, in one screen
    py tools/loop.py next            the next unblocked task (add --json)
    py tools/loop.py start P0-T02    mark it in progress
    py tools/loop.py finish P0-T02   mark it done and advance
    py tools/loop.py block P0-T05 --reason "waiting for the token"
    py tools/loop.py go              loop_enabled = true   ("vai")
    py tools/loop.py stop            loop_enabled = false  ("fermati")
    py tools/loop.py gate phase      how far it may run unattended
    py tools/loop.py queue  --question ... --default ... --rationale ...
    py tools/loop.py decide D-001 --choose ... --by marco
    py tools/loop.py take-defaults   apply unanswered reversible defaults
    py tools/loop.py check           integrity of the plan (CI runs this)
    py tools/loop.py report          write reports/<date>-run<N>.md

Exit codes: 0 fine, 1 a problem a human should see, 2 nothing to do.
"""

import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, "state")
BACKLOG = os.path.join(STATE_DIR, "backlog.json")
STATE = os.path.join(STATE_DIR, "state.json")
DECISIONS = os.path.join(STATE_DIR, "decisions.json")
REPORTS = os.path.join(ROOT, "reports")

DONE = "done"
TODO = "todo"
DOING = "doing"
BLOCKED = "blocked"


# ---------------------------------------------------------------- plumbing

def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    """Write atomically-ish and always with a trailing newline, so a diff of
    the state file stays readable."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return datetime.date.today().isoformat()


def tasks_by_id(backlog):
    return {t["id"]: t for t in backlog["tasks"]}


def phases_by_id(backlog):
    return {p["id"]: p for p in backlog["phases"]}


# ---------------------------------------------------------------- logic

def blocking_reasons(task, index, decisions):
    """Why this task cannot start. Empty list means it can."""
    reasons = []
    for dep in task.get("depends_on") or []:
        other = index.get(dep)
        if other is None:
            reasons.append("depends on unknown task %s" % dep)
        elif other["status"] != DONE:
            reasons.append("waits for %s (%s) [%s]" % (dep, other["title"], other["status"]))
    did = task.get("decision")
    if did:
        for d in decisions.get("open") or []:
            if d["id"] == did:
                reasons.append("waits for decision %s: %s" % (did, d["question"]))
    if task["status"] == BLOCKED:
        reasons.append("marked blocked: %s" % (task.get("blocked_reason") or "no reason given"))
    return reasons


def next_task(backlog, decisions):
    index = tasks_by_id(backlog)
    # An already-started task comes first: finish what is open before
    # starting something new.
    for t in backlog["tasks"]:
        if t["status"] == DOING:
            return t, []
    for t in backlog["tasks"]:
        if t["status"] != TODO:
            continue
        reasons = blocking_reasons(t, index, decisions)
        if not reasons:
            return t, []
    # Nothing runnable: report why, so a session can say something useful.
    waiting = []
    for t in backlog["tasks"]:
        if t["status"] in (TODO, BLOCKED):
            waiting.append((t, blocking_reasons(t, index, decisions)))
    return None, waiting


def crosses_gate(state, task, backlog):
    """Would starting this task cross a gate the loop must stop at?"""
    width = state.get("gate_width", "phase")
    if width == "task":
        return True, "gate_width is 'task': the loop stops after every task."
    if width == "run":
        return False, ""
    phase = task["phase"]
    if phase != state.get("current_phase"):
        p = phases_by_id(backlog).get(phase, {})
        if p.get("gate", True):
            return True, ("this task opens phase %s (%s), and the loop stops at "
                          "phase boundaries." % (phase, p.get("title", "?")))
    return False, ""


def phase_progress(backlog):
    out = {}
    for t in backlog["tasks"]:
        d = out.setdefault(t["phase"], {"done": 0, "total": 0})
        d["total"] += 1
        if t["status"] == DONE:
            d["done"] += 1
    return out


# ---------------------------------------------------------------- commands

def cmd_status(args):
    backlog, state, decisions = load(BACKLOG), load(STATE), load(DECISIONS)
    prog = phase_progress(backlog)
    phases = phases_by_id(backlog)
    total = len(backlog["tasks"])
    done = sum(1 for t in backlog["tasks"] if t["status"] == DONE)

    print("linework -- state at %s" % now())
    print("loop: %s        gate width: %s        runs so far: %s"
          % ("RUNNING (vai)" if state.get("loop_enabled") else "STOPPED (fermati)",
             state.get("gate_width"), state.get("runs", 0)))
    print("progress: %s of %s tasks done" % (done, total))
    print("")
    print("phase   done/total  title")
    for pid in sorted(phases):
        d = prog.get(pid, {"done": 0, "total": 0})
        mark = "<-- current" if pid == state.get("current_phase") else ""
        print("  %-5s %3s/%-3s    %s %s" % (pid, d["done"], d["total"],
                                            phases[pid]["title"], mark))
    print("")
    if state.get("current_task"):
        print("in progress: %s" % state["current_task"])
    nxt, waiting = next_task(backlog, decisions)
    if nxt:
        gate, why = crosses_gate(state, nxt, backlog)
        print("next: %s  %s" % (nxt["id"], nxt["title"]))
        if gate:
            print("      GATE: %s" % why)
    else:
        print("next: nothing runnable.")
        for t, reasons in waiting[:6]:
            print("      %s blocked by: %s" % (t["id"], "; ".join(reasons)))
    print("")
    openq = decisions.get("open") or []
    print("open decisions: %s" % len(openq))
    for d in openq:
        print("  %s  %s" % (d["id"], d["question"]))
        print("      default: %s   (%s)"
              % (d["proposed_default"],
                 "reversible" if d.get("reversible") else "IRREVERSIBLE - waits"))
    if state.get("awaiting_marco"):
        print("")
        print("waiting on Marco: %s" % "; ".join(state["awaiting_marco"]))
    return 0


def cmd_next(args):
    backlog, state, decisions = load(BACKLOG), load(STATE), load(DECISIONS)
    task, waiting = next_task(backlog, decisions)
    if task is None:
        payload = {"task": None, "waiting": [
            {"id": t["id"], "reasons": r} for t, r in waiting]}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Nothing runnable.")
            for t, reasons in waiting:
                print("  %s: %s" % (t["id"], "; ".join(reasons)))
        return 2
    gate, why = crosses_gate(state, task, backlog)
    payload = dict(task)
    payload["gate"] = gate
    payload["gate_reason"] = why
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print("%s  [phase %s, %s]" % (task["id"], task["phase"], task["size"]))
    print("  %s" % task["title"])
    print("")
    print("  why: %s" % task["why"])
    print("")
    print("  done when:")
    for item in task["definition_of_done"]:
        print("    - %s" % item)
    print("")
    print("  verified by: %s" % task["verification"])
    if gate:
        print("")
        print("  GATE: %s" % why)
    return 0


def _set_status(task_id, status, reason=""):
    backlog, state = load(BACKLOG), load(STATE)
    index = tasks_by_id(backlog)
    if task_id not in index:
        print("no such task: %s" % task_id, file=sys.stderr)
        return 1
    task = index[task_id]
    task["status"] = status
    task["blocked_reason"] = reason if status == BLOCKED else ""
    if status == DOING:
        state["current_task"] = task_id
        state["current_phase"] = task["phase"]
    elif state.get("current_task") == task_id:
        state["current_task"] = None
    if status == DONE:
        state.setdefault("history", []).append(
            {"task": task_id, "title": task["title"], "finished": now()})
        # Advance the current phase once every task in it is done.
        prog = phase_progress(backlog)
        pid = task["phase"]
        if prog[pid]["done"] == prog[pid]["total"]:
            later = sorted(p for p in prog if p > pid)
            if later:
                state["current_phase"] = later[0]
    state["updated"] = now()
    save(BACKLOG, backlog)
    save(STATE, state)
    print("%s -> %s%s" % (task_id, status, (" (%s)" % reason) if reason else ""))
    return 0


def cmd_start(args):
    return _set_status(args.task_id, DOING)


def cmd_finish(args):
    return _set_status(args.task_id, DONE)


def cmd_block(args):
    return _set_status(args.task_id, BLOCKED, args.reason)


def cmd_reopen(args):
    return _set_status(args.task_id, TODO)


def cmd_go(args):
    state = load(STATE)
    state["loop_enabled"] = True
    state["updated"] = now()
    save(STATE, state)
    print("loop enabled. 'fermati' stops it.")
    return 0


def cmd_stop(args):
    state = load(STATE)
    state["loop_enabled"] = False
    state["updated"] = now()
    save(STATE, state)
    print("loop stopped. 'vai' starts it again.")
    return 0


def cmd_gate(args):
    state = load(STATE)
    if args.width not in state["gate_width_options"]:
        print("gate width must be one of %s" % state["gate_width_options"],
              file=sys.stderr)
        return 1
    state["gate_width"] = args.width
    state["updated"] = now()
    save(STATE, state)
    print("gate width: %s" % args.width)
    return 0


def cmd_queue(args):
    decisions = load(DECISIONS)
    existing = [d["id"] for d in (decisions.get("open") or [])] + \
               [d["id"] for d in (decisions.get("settled") or [])]
    n = 1
    while "D-%03d" % n in existing:
        n += 1
    entry = {
        "id": "D-%03d" % n,
        "raised": today(),
        "question": args.question,
        "context": args.context or "",
        "proposed_default": args.default,
        "rationale": args.rationale,
        "reversible": not args.irreversible,
        "blocks": args.blocks or [],
    }
    decisions.setdefault("open", []).append(entry)
    save(DECISIONS, decisions)
    print("queued %s (%s)" % (entry["id"],
                              "waits - irreversible" if args.irreversible
                              else "default applies on the next run"))
    return 0


def cmd_decide(args):
    decisions = load(DECISIONS)
    for i, d in enumerate(decisions.get("open") or []):
        if d["id"] != args.decision_id:
            continue
        d["chosen"] = args.choose or d["proposed_default"]
        d["by"] = args.by
        d["when"] = today()
        decisions["settled"].append(d)
        decisions["open"].pop(i)
        save(DECISIONS, decisions)
        print("%s settled: %s (by %s)" % (d["id"], d["chosen"], args.by))
        return 0
    print("no open decision %s" % args.decision_id, file=sys.stderr)
    return 1


def cmd_take_defaults(args):
    """Apply the default to every open reversible decision. Irreversible ones
    are left alone, for as long as it takes."""
    decisions = load(DECISIONS)
    taken, waiting = [], []
    for d in list(decisions.get("open") or []):
        if d.get("reversible"):
            d["chosen"] = d["proposed_default"]
            d["by"] = "default"
            d["when"] = today()
            decisions["settled"].append(d)
            decisions["open"].remove(d)
            taken.append(d["id"])
        else:
            waiting.append(d["id"])
    save(DECISIONS, decisions)
    print("defaults taken: %s" % (", ".join(taken) or "none"))
    if waiting:
        print("still waiting (irreversible): %s" % ", ".join(waiting))
    return 0


def cmd_check(args):
    """Integrity of the plan. CI runs this, so a broken plan fails a build
    instead of confusing a session at three in the morning."""
    problems = []
    backlog, state, decisions = load(BACKLOG), load(STATE), load(DECISIONS)
    index = tasks_by_id(backlog)
    phases = phases_by_id(backlog)

    if len(index) != len(backlog["tasks"]):
        problems.append("duplicate task ids")
    for t in backlog["tasks"]:
        for field in ("id", "phase", "title", "why", "depends_on",
                      "definition_of_done", "verification", "status"):
            if field not in t:
                problems.append("%s is missing '%s'" % (t.get("id", "?"), field))
        if t.get("status") not in backlog["status_values"]:
            problems.append("%s has status '%s'" % (t["id"], t.get("status")))
        if not t.get("definition_of_done"):
            problems.append("%s has an empty definition_of_done" % t["id"])
        if not t.get("verification"):
            problems.append("%s has no verification: autonomy without "
                            "verification is recklessness" % t["id"])
        if t.get("phase") not in phases:
            problems.append("%s is in unknown phase %s" % (t["id"], t.get("phase")))
        for dep in t.get("depends_on") or []:
            if dep not in index:
                problems.append("%s depends on unknown task %s" % (t["id"], dep))
        did = t.get("decision")
        if did:
            known = [d["id"] for d in (decisions.get("open") or [])] + \
                    [d["id"] for d in (decisions.get("settled") or [])]
            if did not in known:
                problems.append("%s references unknown decision %s" % (t["id"], did))

    # Dependency cycles.
    colour = {}

    def visit(tid, trail):
        if colour.get(tid) == "done":
            return
        if colour.get(tid) == "open":
            problems.append("dependency cycle: %s" % " -> ".join(trail + [tid]))
            return
        colour[tid] = "open"
        for dep in index.get(tid, {}).get("depends_on") or []:
            if dep in index:
                visit(dep, trail + [tid])
        colour[tid] = "done"

    for tid in index:
        visit(tid, [])

    # A done task whose dependency is not done is a state we must never reach.
    for t in backlog["tasks"]:
        if t["status"] == DONE:
            for dep in t.get("depends_on") or []:
                if index.get(dep, {}).get("status") != DONE:
                    problems.append("%s is done but its dependency %s is not"
                                    % (t["id"], dep))

    if state.get("gate_width") not in state.get("gate_width_options", []):
        problems.append("state.gate_width is not one of the options")
    ct = state.get("current_task")
    if ct and ct not in index:
        problems.append("state.current_task %s is not a known task" % ct)

    for d in decisions.get("open") or []:
        for field in ("id", "question", "proposed_default", "rationale",
                      "reversible"):
            if field not in d:
                problems.append("decision %s is missing '%s'"
                                % (d.get("id", "?"), field))

    if problems:
        print("PLAN CHECK FAILED (%s problems)" % len(problems))
        for p in problems:
            print("  - %s" % p)
        return 1
    print("plan check passed: %s tasks across %s phases, no cycles, every task "
          "has a definition of done and a way to verify it."
          % (len(index), len(phases)))
    return 0


def cmd_report(args):
    """The thirty-second digest. Pictures are attached by whoever sends it."""
    backlog, state, decisions = load(BACKLOG), load(STATE), load(DECISIONS)
    run_no = state.get("runs", 0) + 1
    os.makedirs(REPORTS, exist_ok=True)
    path = os.path.join(REPORTS, "%s-run%03d.md" % (today(), run_no))

    finished = [h for h in (state.get("history") or [])][-10:]
    nxt, waiting = next_task(backlog, decisions)
    prog = phase_progress(backlog)
    done = sum(1 for t in backlog["tasks"] if t["status"] == DONE)

    lines = []
    lines.append("# Run %s -- %s" % (run_no, today()))
    lines.append("")
    lines.append("**Progress:** %s of %s tasks done. Phase %s (%s of %s tasks)."
                 % (done, len(backlog["tasks"]), state.get("current_phase"),
                    prog.get(state.get("current_phase"), {}).get("done", 0),
                    prog.get(state.get("current_phase"), {}).get("total", 0)))
    lines.append("")
    lines.append("## Done in this run")
    if args.did:
        for item in args.did:
            lines.append("- %s" % item)
    elif finished:
        for h in finished[-5:]:
            lines.append("- %s -- %s" % (h["task"], h["title"]))
    else:
        lines.append("- nothing completed")
    lines.append("")
    lines.append("## Verified how")
    for item in (args.verified or ["- not stated"]):
        lines.append("- %s" % item if not item.startswith("-") else item)
    lines.append("")
    lines.append("## Decided, and why")
    settled_today = [d for d in decisions.get("settled") or []
                     if d.get("when") == today()]
    if settled_today:
        for d in settled_today:
            lines.append("- **%s** %s -> **%s** (by %s)"
                         % (d["id"], d["question"], d.get("chosen"), d.get("by")))
            lines.append("  - why: %s" % d.get("rationale", ""))
            if d.get("by") == "default":
                lines.append("  - taken as the default because it was unanswered; "
                             "reversible, say so and it is undone")
    else:
        lines.append("- nothing decided")
    lines.append("")
    lines.append("## Wanted from Marco")
    openq = decisions.get("open") or []
    if openq or state.get("awaiting_marco"):
        for d in openq:
            lines.append("- **%s** %s" % (d["id"], d["question"]))
            lines.append("  - proposal: %s" % d["proposed_default"])
            lines.append("  - %s" % ("reversible: if you say nothing, this is what "
                                     "happens, and it can be undone"
                                     if d.get("reversible")
                                     else "IRREVERSIBLE: nothing happens until you answer"))
        for item in state.get("awaiting_marco") or []:
            lines.append("- %s" % item)
    else:
        lines.append("- nothing. The loop has what it needs.")
    lines.append("")
    lines.append("## Next")
    if nxt:
        gate, why = crosses_gate(state, nxt, backlog)
        lines.append("- %s -- %s" % (nxt["id"], nxt["title"]))
        if gate:
            lines.append("- **Stopped at a gate:** %s" % why)
    else:
        lines.append("- nothing runnable:")
        for t, reasons in waiting[:5]:
            lines.append("  - %s: %s" % (t["id"], "; ".join(reasons)))
    lines.append("")
    if args.pictures:
        lines.append("## Pictures")
        for p in args.pictures:
            lines.append("![%s](%s)" % (os.path.basename(p), p))
        lines.append("")

    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))

    state["runs"] = run_no
    state["last_run"] = {"when": now(), "report": os.path.relpath(path, ROOT)}
    state["updated"] = now()
    save(STATE, state)
    print(path)
    return 0


# ---------------------------------------------------------------- cli

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("status").set_defaults(fn=cmd_status)

    q = sub.add_parser("next")
    q.add_argument("--json", action="store_true")
    q.set_defaults(fn=cmd_next)

    for name, fn in (("start", cmd_start), ("finish", cmd_finish),
                     ("reopen", cmd_reopen)):
        s = sub.add_parser(name)
        s.add_argument("task_id")
        s.set_defaults(fn=fn)

    b = sub.add_parser("block")
    b.add_argument("task_id")
    b.add_argument("--reason", required=True)
    b.set_defaults(fn=cmd_block)

    sub.add_parser("go").set_defaults(fn=cmd_go)
    sub.add_parser("stop").set_defaults(fn=cmd_stop)

    g = sub.add_parser("gate")
    g.add_argument("width")
    g.set_defaults(fn=cmd_gate)

    qu = sub.add_parser("queue")
    qu.add_argument("--question", required=True)
    qu.add_argument("--default", required=True)
    qu.add_argument("--rationale", required=True)
    qu.add_argument("--context")
    qu.add_argument("--blocks", nargs="*")
    qu.add_argument("--irreversible", action="store_true")
    qu.set_defaults(fn=cmd_queue)

    d = sub.add_parser("decide")
    d.add_argument("decision_id")
    d.add_argument("--choose")
    d.add_argument("--by", default="marco", choices=["marco", "default", "claude"])
    d.set_defaults(fn=cmd_decide)

    sub.add_parser("take-defaults").set_defaults(fn=cmd_take_defaults)
    sub.add_parser("check").set_defaults(fn=cmd_check)

    r = sub.add_parser("report")
    r.add_argument("--did", nargs="*")
    r.add_argument("--verified", nargs="*")
    r.add_argument("--pictures", nargs="*")
    r.set_defaults(fn=cmd_report)

    args = p.parse_args(argv)
    if not getattr(args, "fn", None):
        p.print_help()
        return 1
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
