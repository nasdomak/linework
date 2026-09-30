# The standing session prompt

> This file is never pasted. A session -- started by Marco saying a word, or by a
> schedule with nobody watching -- begins here and reconstructs everything else
> from the repository. It changes only when the way the project runs changes,
> and then in a commit that says why.
>
> Rewritten in session 3 (30/09/2026): the project now runs **in the cloud**.
> GitHub is the source of truth, a session reaches it through the `add_repo`
> grant, and nothing needs Marco's PC to be on. The session-2 version depended
> on a local plugin (`lw_*` tools) that is no longer on the critical path.

---

## 0. Get the repository, then load your experience

1. Attach and clone the repository, if this session does not already have it:
   `add_repo` with owner `nasdomak`, repo `linework`, access `push`; then the
   clone command it returns (`/home/claude/linework`). Work **only** in that
   clone.
2. `CLAUDE.md` in the repository root holds the non-negotiable constraints and
   every trap already paid for. It loads by itself once the clone is registered;
   if it has not, read it. **Do not rediscover what is written there.**
3. Then, in this order:
   - `python3 tools/loop.py status` -- where the loop is, in one screen;
   - `project_context.md` -- persistent memory: goal, status, last action,
     critical data, next steps;
   - `state/decisions.json` -- what is queued for Marco and what defaults are
     pending.

Never ask Marco for anything already in those places.

## 1. Check the ground, once

- `git log -1` and `git status` -- a clean checkout of `origin/main`.
- `python3 tools/ci_status.py` -- is the last commit green? If it is red, fixing
  it is the task, before anything from the backlog.

## 2. Decide whether to run at all

Read `state/state.json`:

- `loop_enabled: false` -- Marco has said "fermati". **Stop here.** Report the
  state if asked, change nothing.
- `loop_enabled: true` -- carry on.

## 3. Take the next task -- do not choose one

```
python3 tools/loop.py take-defaults
python3 tools/loop.py next --json
```

The plan decides, not you and not a conversation. If nothing is runnable, it
says why: read the reasons and go to step 8.

If the task comes back with `"gate": true`, the loop has reached a boundary
Marco wants to see. **Do not start it.** Write the report, say plainly what the
next phase would begin, and stop.

Otherwise: `python3 tools/loop.py start <TASK-ID>`

## 4. Do the work

- The whole project is in **English** -- code, comments, docs, ADRs, commit
  messages. Only the live conversation with Marco is in Italian, in plain
  simple words.
- The engine core (`engine/`, `lang/`, `geometry/`, `memory/`, `shared/`)
  imports **nothing outside the standard library**. `ezdxf` is confined to
  `dxf/` and `tools/`.
- Frozen decisions become numbered ADRs in `docs/adr/`, listed in its README.
- **One task at a time.** Do not widen the job because it was convenient.

If a question comes up that is not blocking, **do not stop to ask**:

```
python3 tools/loop.py queue --question "..." --default "..." --rationale "..."
```

If it is blocking and irreversible, add `--irreversible` and go to step 8 -- it
waits, however long it takes. If it is blocking and reversible, queue it and
take the default now.

## 5. Verify it -- this is the step that makes the rest legitimate

**Autonomy without verification is recklessness.** Never declare a task done on
the strength of "it ran". Use every check the task affords:

- `python3 tools/run_tests.py` -- every test that needs only the standard
  library, runnable here. (This container cannot install `ezdxf` or `pytest`:
  PyPI answers 403. CI runs the full suite.)
- `python3 tools/loop.py check` and `python3 tools/sync_plan.py check`.
- The task's own `verification` field, to the letter.
- For anything that produces geometry: **look at the picture**. After the push,
  `python3 tools/ci_status.py renders` fetches the PNGs CI drew for your commit;
  open them. A shape can look right at the wrong size, and a correct size can
  be invisible (docs/RENDER_FINDINGS.md).

## 6. Commit it, push it, read CI

```
git add -A
git commit -F <message file>          plain ASCII subject under 72 characters
git push origin main
git ls-remote origin main             must equal git rev-parse HEAD
python3 tools/ci_status.py --wait 900
```

Commit as `Marco Ascani <nasdomak@users.noreply.github.com>`, with the session
attribution lines the system gives you. **Read CI yourself** -- every job, and
the test count each one published. Never assume green. If it is red, the task
is not done: fix it, or `block` it with the reason.

## 7. Update the state and the memory

```
python3 tools/loop.py finish <TASK-ID>
```

Then update `project_context.md`: status, last action, next steps. **Overwrite
what is obsolete** -- the file stays short on purpose. Commit and push this too.

## 8. Write the report and stop, or continue

```
python3 tools/loop.py report --did "..." --verified "..." --pictures out/ci-renders/*.png
```

Commit and push the report. Then:

- If `gate_width` allows and there is another unblocked task, **go back to
  step 3**.
- At a gate, out of work, or facing something irreversible: stop, and give
  Marco the report in Italian, in plain words, with the pictures. In a
  scheduled run nobody is watching: send it with the message tool so it
  reaches him.

## What Marco says, and what it means

| He says | Do |
|---|---|
| "vai" | `python3 tools/loop.py go`, then start at step 1 |
| "fermati" | `python3 tools/loop.py stop` |
| "a che punto siamo?" | answer from `loop.py status`, never from memory |
| "voglio X" | find every affected task, ADR, module and test; update them all; re-plan; say what changed |
| "questa scelta non mi piace" | `loop.py decide` the other way, record why, re-plan what depended on it |
| "fammi vedere" | fetch or render the current pictures and show them |
| "questa regola tienila" | write it into `CLAUDE.md` |
| "fermati dopo ogni cosa" / "vai avanti quanto puoi" | `loop.py gate task` / `loop.py gate run` |

## The three rules that outrank convenience

1. **Marco never opens a terminal, never writes a commit message, never edits a
   backlog, never pastes a prompt.** A design that needs one of those has failed
   the brief. Find another way, or tell him plainly why it is impossible. **A
   manual step he does not know about is worse than one he does.**
2. **Irreversible actions never take a default.** They wait.
3. **The loop is the first prototype of the product.** If it cannot be made to
   work honestly here -- autonomous, bridled, self-verifying, with persistent
   memory, steered by a sentence -- it has no business being shipped to anyone.
