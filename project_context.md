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

## Current status (30/09/2026, end of session 3)

**Workbench: finished except the live demonstration of one autonomous run,
which was scheduled at the end of session 3 (see "Last action").
Product: phase 0, 4 of 5 tasks done. Next: P0-T04, then the gate to phase 1.**

### Measured this session

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

Session 3, 29-30/09/2026: corrected this file against the measured state;
first commits; licence, ADR 0001/0002/0004; CI green on three systems; plan
sync; CI results readable from the cloud; `PROMPT.md` and `CLAUDE.md` rewritten
for the cloud loop; the loop switched on (`loop_enabled: true`) for the
demonstration run; a scheduled task created to run the loop unattended.

---

## Next steps

1. The scheduled run takes **P0-T04** (monorepo layout) end to end with nobody
   watching: work, verify, commit, push, read CI, report. Then it reaches the
   gate to phase 1 and stops.
2. At the gate Marco looks at phase 0 and says "vai" for phase 1 (the language),
   the riskiest phase of the project.
3. Open the upstream conversation with LibreCAD about `addDimension` /
   `addHatch` when convenient: long lead time, nothing depends on it.
