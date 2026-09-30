# project_context.md — persistent memory, linework

> Living memory. Read in full at the start of every session, updated at every
> checkpoint. Overwrite what is obsolete so the file stays short. Frozen
> decisions belong in `docs/adr/`.
> The FreeCAD Agent folder (`…/000009___Freecad_copilot`) is **read-only
> reference input** and must never be modified.
>
> **Every claim here must have been verified, not assumed.** Session 2 wrote
> "everything committed" and "CI written" when neither was true; session 3
> found out by looking. Write what you measured, and say when you measured it.

---

## Main goal

**A design partner that learns your trade, thinks about the problem, writes
readable recipes, and executes them without getting a single number wrong.**

The goal is **the drawing and productivity** — not LibreCAD, which is one window
onto the work and not the protagonist. **The declared ambition is rung 4: an
autonomous designer.** Everything local, via Ollama. Free public release on
GitHub. Domain: all of 2D. Completeness is the north star.

The project is named **`linework`** (Marco, 17/09/2026). The repository is
**public from the start** (his decision): `https://github.com/nasdomak/linework`.

---

## Standing rules

1. **Start of session:** read this file in full, plus `PROMPT.md` and
   `python tools/loop.py status`, before any action.
2. **Checkpoints:** after every completed logical step and before pausing,
   update this file, overwriting what is obsolete.
3. Never ask Marco for information already written here.
4. **Language:** the whole project is in **English** — code, comments, docs,
   ADRs, commits. **Only the live conversation with Marco is in Italian**, in
   plain simple words, with any command he must run himself ready to paste, one
   at a time, preferably as a file he can double-click.
5. **`PROMPT.md` is the standing session prompt** and never changes. A numbered
   `0N_PROMPT_SessionN.md` in the kDrive folder is written only while the
   workbench is unfinished, as a fallback.
6. **File hygiene.** Documents are updated in place, never renamed: a stable
   filename is what a fresh session can find.

---

## Current status

**Phase: FINISHING THE WORKBENCH — session 3 (29-30/09/2026). No product code yet.**

### Measured at the start of session 3 (29/09/2026)

- The repository had **zero commits**: every file untracked. Session 2's
  "everything committed" was false.
- `.github/workflows/ci.yml` **did not exist**. Session 2's "CI written" was false.
- **`device_bash` works again** on "dexter": both connected folders mount at
  `$HOME/mnt/000002___Librecad` and `$HOME/mnt/linework`, read and write.
  Deletion is gated; `device_request_delete_permission` on the folder root
  grants it for the rest of the session (needed by git for `index.lock`).
- The **`linework` local plugin is NOT loaded**: the device reports only a
  `Blender` local MCP server and no `lw_*` tool exists. The package is at
  `…\000002___Librecad\Claude outputs\linework.plugin`. Decision with Marco
  (30/09/2026): **keep it separate** from his personal `marco-ascani` plugin and
  do not install it now — see "GitHub" below for why it is no longer on the
  critical path.

### Environment facts for this project (verified 29-30/09/2026)

| What | Where it works | Where it does not |
|---|---|---|
| Files and **local git** in `C:\Users\ascan\linework` | `device_bash` (a Linux VM on dexter; git 2.x, python3.10, stdlib + numpy/matplotlib/pillow) | — |
| `ezdxf`, `pytest` | only in Marco's Windows Python (`py`) | not in the cloud container, not in the `device_bash` VM: **PyPI returns 403 from both** (30/09) |
| GitHub over HTTPS | nowhere from a shell yet | cloud container and `device_bash` VM both get **403 on CONNECT** (29/09) |
| GitHub in the browser | the built-in browser pane, signed in as **`nasdomak`** by Marco; the site is "high-risk", so **every single action needs Marco's "Allow"** | — |

**Consequence for verification:** the headless suite that needs `ezdxf` cannot
run in any shell this session can reach. Tests written from session 3 on are
plain `assert` functions with no third-party import where possible, runnable by
`tools/run_tests.py` without pytest; CI runs the full suite with pytest.

### GitHub — the path changed in session 3

The session now has an **`add_repo` tool** (it did not exist in session 2). It
grants the cloud container push access to a named repository, which removes the
need for the token, `lw_git`, `lw_gh`, and Marco's PC being on at night.
It needs Marco's GitHub account linked to Claude
(claude.ai → Settings → Connectors → GitHub, as **`nasdomak`**). On 30/09 it
answered `permission_denied: link your GitHub account` — waiting on that link.

Fallback if linking does not work: the old plan (token + `lw_git`/`lw_gh` from
the local plugin).

**His SSH key on GitHub authenticates as `invimak`, not `nasdomak`.** Two
different accounts; everything for this project is `nasdomak`.

### Built and present in the repository

- **The executable plan**: `state/backlog.json` — 45 tasks, 18 phases, each with
  dependencies, a definition of done and a way to verify it. `tools/loop.py
  check` enforces that.
- **The loop state machine**: `tools/loop.py` (standard library only).
- **The decision queue**: `state/decisions.json`.
- **The standing session prompt**: `PROMPT.md`.
- **The render and visual-regression harness**: `tools/render_dxf.py`,
  `tools/visual_check.py`, `tests/fixtures/make_fixtures.py`. Session 2 reports
  18 headless tests green on dexter on 17/09 (not re-run since: no `ezdxf`
  reachable, see above).

### Not built yet

See `state/backlog.json` phase 0 and the session-3 checklist in the kDrive
`03_PROMPT_Session3.md`: CI, licence ADR, ADR 0001/0002, `docs/` plan copy and
`tools/sync_plan.py`, first push, scheduled trigger, end-to-end demonstration.

---

## Critical data

- Repository working copy (**the source of truth**): `C:\Users\ascan\linework`
  — deliberately **off kDrive**, because cloud sync can hand out half-written
  files. Git identity: `Marco Ascani <nasdomak@users.noreply.github.com>`.
- Remote: `https://github.com/nasdomak/linework` (created 30/09/2026, empty).
- Prose documents (kDrive): `C:\Users\ascan\kDrive\003_Sigic\001_Progetti\000002___Librecad`
- FreeCAD reference (**READ-ONLY, NEVER MODIFY**):
  `C:\Users\ascan\kDrive\003_Sigic\001_Progetti\000009___Freecad_copilot`
- GitHub token (only if the fallback is ever needed):
  `C:\Users\ascan\.linework\github_token` — never in chat, never committed.
  `install_token.bat` is in the kDrive folder for that case.
- Claude Project attached: **2026_006___Librecad**.

### Marco's machine "dexter", measured 17/09/2026

Windows 11 · Python 3.13.7 (`py` launcher) · git 2.54.0 · Ollama 0.34.1 ·
LibreCAD at `C:\Program Files (x86)\LibreCAD` · `ezdxf` 1.4.4 and `pytest` 9.1.1 ·
matplotlib 3.10.8 · numpy 2.4.1 · no `gh`, no `cmake`.

---

## Open issues (product design, from session 1)

- **A** The script language — the bridle on the hand. *(P1-T01..T05.)*
- **B** The escape hatch: what happens when something cannot be said.
- **C** The blank page: where the first object goes, what "next to it" means.
- **D** Non-text input: sketch photo, PDF, scan → clean DXF. *(Phase 15.)*
- **E** Memory retrieval — layer 2 is harder than layer 1 and needs design.
- **F** Design criteria: what the agent critiques its own work against.
- **H** Plugin binary compatibility and panel persistence after `execComm`.
  *(Phase 14.)*

---

## Last action

Session 3, 30/09/2026: corrected this file against the measured state; created
the GitHub repository from the built-in browser; asked Marco to link GitHub.

---

## Next steps

1. Commit everything that exists (local git over `device_bash`).
2. CI workflow, licence ADR (D-001), ADR 0001 and 0002, `docs/` plan copy and
   `tools/sync_plan.py`.
3. When GitHub is linked: `add_repo`, push, read CI, fix until green.
4. Scheduled trigger and one end-to-end autonomous task.
5. Then product phase 0 via the loop.
