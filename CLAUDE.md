# linework -- how this project operates

These rules were paid for with wasted runs. Follow them instead of rediscovering
them. Session 2 (17/09/2026) wrote the first version as a plugin skill; session 3
(30/09/2026) moved it here, into the repository, so every session that clones the
project inherits it without installing anything.

**Start with `PROMPT.md`.** It is the procedure. This file is the background.

## The point of the project

A design partner that learns your trade, thinks about the problem, writes
readable recipes, and executes them without getting a single number wrong. The
goal is the **drawing and productivity**, not LibreCAD, which is one window onto
the work.

**Thinking is free; the hand is guided** (ADR 0001). **Numbers enter through two
doors only: the user dictates them, or the solver computes them.** The model never
emits executable text and never a final coordinate. The ambition is rung 4 of the
autonomy ladder -- an autonomous designer. A 4B model is the floor, not the roof.

## Non-negotiable constraints

- **Marco never opens a terminal, never writes a commit message, never edits a
  backlog, never pastes a prompt.** A manual step he does not know about is worse
  than one he does.
- **Verification before autonomy.** Never declare done on "it ran". Numbers and
  pictures catch different things: look at both.
- **Irreversible actions never take a default.** They wait. Reversible ones
  proceed, are recorded with their reasoning, and are flagged in the report.
- **Secrets never appear in the chat, in the repository, or in a log.**
- **The whole project is in English.** Only the live conversation with Marco is
  in Italian, in plain simple words, as to someone who is not a developer.
- **The FreeCAD project at `...\001_Progetti\000009___Freecad_copilot` is
  READ-ONLY** reference input. Never modify anything inside it.
- **Every claim in `project_context.md` is measured, not assumed.** Session 2
  wrote "everything committed" and "CI written"; neither was true.

## The environment, already mapped -- do not rediscover this

Measured 29-30/09/2026.

- **GitHub is the source of truth**: `https://github.com/nasdomak/linework`,
  branch `main`. A cloud session gets push access through `add_repo`
  (owner `nasdomak`, repo `linework`, access `push`). This works because Marco
  linked GitHub to Claude and installed the Claude GitHub App on **`nasdomak`**,
  for this one repository. His SSH key belongs to a different account
  (`invimak`): irrelevant here.
- **The cloud container can reach the GitHub API and git, but not the blob
  storage** behind raw job logs and artefact downloads (403 on CONNECT). That is
  why CI publishes what a session needs where it can read it:
  `tools/ci_report.py` turns pytest's JUnit XML into annotations (a count line
  per job, one error per failure), and the render job pushes its pictures to the
  `ci-renders` branch. `tools/ci_status.py` reads both. There is no `gh`.
- **PyPI answers 403** in the cloud container (and in the `device_bash` VM on
  Marco's PC). `ezdxf` and `pytest` cannot be installed there.
  `tools/run_tests.py` runs every test that needs only the standard library;
  CI runs everything. Write new tests as plain `assert` functions without
  fixtures wherever possible, so they run in both places.
- **Marco's PC ("dexter", Windows 11)** is reachable only when a session is
  linked to it: `device_bash` then mounts `C:\Users\ascan\linework` (a local
  mirror of the repository) and the kDrive folder
  `C:\Users\ascan\kDrive\003_Sigic\001_Progetti\000002___Librecad` (prose from
  session 1, the fallback session prompts). The VM behind `device_bash` is
  Linux: it cannot run Windows programs, and it cannot reach GitHub. To update
  the mirror, bundle from the cloud clone (`git bundle create`), write it into
  the mirror's `.git/` with the device file tools, and `git fetch` it there.
  Deleting in a mounted folder needs `device_request_delete_permission` on the
  folder root first -- git needs it for its own `index.lock`.
  `device_commit_files` refuses to write anything under `.github/`.
- **The `linework` local plugin** (`lw_*` tools, session 2) is not installed
  and not needed for the loop. It returns when the product must drive Ollama
  and LibreCAD on Marco's PC (phases 5 and 14). Its package is in the kDrive
  folder under `Claude outputs`.
- **GitHub in the built-in browser** works when Marco is signed in there as
  `nasdomak`, but the site is "high-risk": every single action asks Marco for
  approval. Use it only for things the API grant cannot do.
- **DXF rendering is the backbone of self-verification.** `ezdxf` plus
  matplotlib renders a drawing to PNG. Two render defects are open (P3-T04,
  `docs/RENDER_FINDINGS.md`): colour-7 layers draw nothing, and hatch patterns
  draw nothing. Until they are fixed, no golden image is blessed.

## Traps already paid for

- **A commit message with nested quotes through PowerShell silently does not
  commit**, and the push then says "Everything up-to-date". Build messages in a
  file, commit with `-F`, and always compare `git rev-parse HEAD` with
  `git ls-remote origin main` after a push.
- **Every `subprocess` must use `stdin=DEVNULL`** in anything that may run under
  an MCP server: inheriting stdin corrupts the JSON-RPC pipe.
- **`.bat` files must have CRLF** line endings or they flash and close on
  Windows (`.gitattributes` enforces it).
- **Never put raw `<`, `>` or `&` inside XML text.**
- **`pgrep -f X` / `pkill -f X` match themselves.** Use bracketed patterns.
- **The kDrive folder is cloud-synced** and can hand out half-written files.
  Nothing authoritative lives there any more.
- **A test that measures "some ink" cannot see a missing outline** when holes
  and text are present. Look at the picture.

## The development loop

The loop is the first prototype of the product: autonomous, bridled,
self-verifying, with persistent memory, steered by natural language.

- One task at a time from `state/backlog.json`: take the next unblocked one,
  do it, **verify it**, commit and push it, read CI, update the state, report.
- The loop runs freely inside a product phase and **stops at phase boundaries**
  (`gate_width` in `state/state.json`, changed by a sentence from Marco).
- A non-blocking question goes into `state/decisions.json` with a default and a
  rationale; work continues. Unanswered on the next run, the default is taken,
  recorded as reversible, and flagged. Anything irreversible waits.
- "vai" starts the loop, "fermati" stops it. Both are sentences, not commands.
- `tools/sync_plan.py` keeps `docs/ACTION_PLAN.md` and the backlog in agreement;
  after changing a phase or a task title, run `python3 tools/sync_plan.py write`.

## At the end of every logical step

Update `project_context.md` and `state/state.json`. Overwrite what is obsolete
instead of accumulating. Frozen decisions go into `docs/adr/` as numbered ADRs.
