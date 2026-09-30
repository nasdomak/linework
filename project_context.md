# project_context.md — persistent memory, linework

> Living memory. Read in full at the start of every session, updated at every
> checkpoint. Overwrite what is obsolete so the file stays short. Frozen
> decisions belong in `docs/adr/`; operating rules and traps in `CLAUDE.md`;
> the procedure in `PROMPT.md`.
>
> **Every claim here must have been measured, not assumed**, with the date.
> Session 2 wrote "everything committed" and "CI written" when neither was true.

---

## Main goal

**A design partner that learns your trade, thinks about the problem, writes
readable recipes, and executes them without getting a single number wrong.**

The goal is **the drawing and productivity** — not LibreCAD, which is one window
onto the work. **The declared ambition is rung 4: an autonomous designer.**
Everything local, via Ollama. Free public release on GitHub. Domain: all of 2D.
Completeness is the north star. Name **`linework`** (Marco, 17/09/2026).

---

## Standing rules

1. **Start of session:** follow `PROMPT.md`. It says what to read and in what order.
2. **Checkpoints:** after every completed logical step, update this file,
   overwriting what is obsolete.
3. Never ask Marco for information already written here or in `CLAUDE.md`.
4. **Language:** the project is in **English**; only the live conversation with
   Marco is in Italian, plain and simple, numbered steps, a file to click rather
   than a command to paste.
5. **File hygiene.** Documents are updated in place, never renamed.

---

## Current status (30/09/2026, first unattended run of the loop)

**Workbench: finished, and demonstrated: the scheduled run took P0-T04 end to
end with nobody watching. Product: phase 0 complete, 5 of 5 tasks.
The loop is stopped at the gate to phase 1 (the language), waiting for "vai".**

### Measured in the unattended run (30/09/2026)

- **P0-T04 done**: `lang/ geometry/ memory/ engine/ shared/ dxf/` exist, each
  with an `__init__.py` docstring and a `README.md` stating what it may and
  may not import. `tests/test_dependency_rules.py` walks the imports
  independently of `tools/check_core_imports.py`; a deliberate `import numpy`
  in `geometry/` made it fail, as it must. CI green on all 8 jobs for commit
  `43863d6`: **51 passed, 0 failed, 0 skipped on each of the six test jobs**.
- **A loop defect found and fixed**: `finish` advanced `current_phase` when a
  phase completed, and the gate compared against `current_phase`, so the loop
  would have walked into phase 1 without stopping. The gate now compares with
  `state.open_phase`, which only `loop.py go` ("vai") at a gate raises.
  `tests/test_loop_gate.py` pins it. Reversible; flagged in the report.
- The CI pictures for `43863d6` are unchanged: the P3-T04 render defects
  (no plate outline, no walls, no dimension lines, no hatch) are still open.

### Measured in session 3 (29-30/09/2026)

- **GitHub is the source of truth** and the loop runs in the cloud:
  `https://github.com/nasdomak/linework`, public, created 30/09/2026 from the
  built-in browser. Marco linked GitHub to Claude and installed the Claude
  GitHub App on `nasdomak`, **this repository only**. `add_repo` (access
  `push`) then gives a cloud session push access: verified by pushing three
  commits and comparing `git rev-parse HEAD` with `git ls-remote origin main`.
  **No token, no local plugin, no PC left on at night.**
- **CI is green on all 8 jobs** (commit `0823a6a`): plan and rules, render, and
  pytest on ubuntu/windows/macos × Python 3.11/3.13 — **41 passed, 0 failed,
  0 skipped on each of the six**, read back by `tools/ci_status.py` without a
  browser.
- **The pictures CI drew were looked at** (`tools/ci_status.py renders`): plate
  and room show holes, openings, text and dimension text, but **not** the plate
  outline, the room walls, the dimension lines, or the hatch pattern. These are
  the open render defects of P3-T04, now confirmed on Linux too
  (`docs/RENDER_FINDINGS.md`). The ink test passes anyway: it measures some ink,
  not the right ink.
- **Licence: GPL-2.0-or-later** (D-001), taken as the loop's reversible default
  after 12 days unanswered. ADR 0004. Changeable by Marco **until the first
  outside contribution is merged**.
- `device_bash` on "dexter" works (mounted both folders, read, wrote, deleted
  after permission). The local mirror `C:\Users\ascan\linework` was in sync with
  GitHub at commit `20bdbac` and is **not** updated automatically; GitHub wins.
- PyPI answers 403 in the cloud container and in the `device_bash` VM: the full
  suite runs only in CI. `tools/run_tests.py` runs the stdlib-only tests
  anywhere (31 of the 41).

### Built and verified

- The executable plan (`state/backlog.json`, 45 tasks, 18 phases), the loop
  (`tools/loop.py`), the decision queue, the standing prompt (`PROMPT.md`, now
  cloud-native), the operating rules (`CLAUDE.md`).
- ADR 0001 (thinking is free, the hand is guided), ADR 0002 (the memory model),
  ADR 0004 (licence); index in `docs/adr/README.md`.
- `docs/ACTION_PLAN.md` (living copy of the plan) and
  `docs/BRAINSTORMING_SUMMARY.md`; `tools/sync_plan.py` keeps plan and backlog
  in agreement, enforced in CI.
- `tools/check_core_imports.py` (engine core is stdlib-only, enforced in CI).
- CI (`.github/workflows/ci.yml`), `tools/ci_report.py` (test counts as
  annotations), `tools/ci_status.py` (reads jobs, counts, pictures), the
  `ci-renders` branch (pictures per commit).
- The render and visual-regression harness from session 2.

---

## Critical data

- Source of truth: `https://github.com/nasdomak/linework`, branch `main`.
  Commit identity `Marco Ascani <nasdomak@users.noreply.github.com>`.
- Local mirror on Marco's PC: `C:\Users\ascan\linework`.
- Prose from session 1 and the fallback session prompts (kDrive):
  `C:\Users\ascan\kDrive\003_Sigic\001_Progetti\000002___Librecad`.
- FreeCAD reference (**READ-ONLY, NEVER MODIFY**):
  `C:\Users\ascan\kDrive\003_Sigic\001_Progetti\000009___Freecad_copilot`.
- The session-2 local plugin package: `…\000002___Librecad\Claude outputs\linework.plugin`
  (not installed; returns in phases 5/14). `install_token.bat` in the kDrive
  folder is obsolete (no token is needed).
- Claude Project attached: **2026_006___Librecad**.
- Marco's machine "dexter" (17/09/2026): Windows 11, Python 3.13.7 (`py`),
  git 2.54.0, Ollama 0.34.1, LibreCAD at `C:\Program Files (x86)\LibreCAD`,
  `ezdxf` 1.4.4, `pytest` 9.1.1.

---

## Open issues (product design, from session 1)

- **A** The script language — the bridle on the hand. *(P1-T01..T05.)*
- **B** The escape hatch. **C** The blank page. **D** Non-text input *(phase 15)*.
- **E** Memory retrieval for layer 2. **F** Design criteria.
- **H** Plugin binary compatibility and panel persistence *(phase 14)*.

---

## Last action

30/09/2026, first scheduled unattended run: P0-T04 (monorepo layout and
dependency rules) done and verified; the phase-gate defect in `tools/loop.py`
fixed with tests; stopped at the gate to phase 1.

---

## Next steps

1. Marco looks at phase 0 and says "vai" for phase 1 (the language), the
   riskiest phase of the project. `loop.py go` then opens the gate and the next
   run takes **P1-T01** (the commitment form).
2. Open the upstream conversation with LibreCAD about `addDimension` /
   `addHatch` when convenient: long lead time, nothing depends on it.
