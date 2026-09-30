# The standing session prompt

> This file does not change. That is its whole point: it is never pasted again.
> A session — started by Marco saying a word, or by a schedule with nobody
> watching — begins here and reconstructs everything else from the repository.
>
> Written in session 2 (17/09/2026). If you are reading it in a fresh session,
> this is your instruction set. Follow it in order.

---

## 0. Load your experience before doing anything

The `linework-operativita` skill holds this project's non-negotiable constraints
and every trap already paid for. It should load on its own; if it has not, load
it. **Do not rediscover what is written there.**

Then, in this order:

1. `py tools/loop.py status` — where the loop is, in one screen.
2. `project_context.md` — persistent memory: goal, status, last action,
   critical data, next steps.
3. `state/decisions.json` — what is queued for Marco and what defaults are
   pending.

Never ask Marco for anything already in those three places.

## 1. Check the ground, once

The workbench depends on things that have broken before. Check, do not assume:

- `lw_env` — the state of Marco's machine and of the repository. It changes
  nothing and it is cheap.
- `device_bash` — try to mount the connected folders. It has been broken since
  a Windows update of 08/09/2026; **if it works again, say so in the report**,
  because several workarounds can then be retired.

## 2. Decide whether to run at all

Read `state/state.json`:

- `loop_enabled: false` → Marco has said "fermati". **Stop here.** Report the
  state if asked, change nothing.
- `loop_enabled: true` → carry on.

## 3. Take the next task — do not choose one

```
py tools/loop.py next --json
```

The plan decides, not you and not a conversation. If it answers that nothing is
runnable, it also says why: read the reasons, and go to step 8.

If the task comes back with `"gate": true`, the loop has reached a boundary
Marco wants to see. **Do not start it.** Write the report, say plainly what the
next phase would begin, and stop.

Then:

```
py tools/loop.py start <TASK-ID>
```

## 4. Do the work

- The whole project is in **English** — code, comments, docs, ADRs, commit
  messages. Only the live conversation with Marco is in Italian, in plain
  simple words, with any command he must run himself ready to paste, one at a
  time.
- The engine core (`engine/`, `lang/`, `geometry/`, `memory/`) imports **nothing
  outside the standard library**. `ezdxf` is confined to `dxf/` and to
  `tools/`.
- Frozen decisions become numbered ADRs in `docs/adr/`.
- **One task at a time.** Do not widen the job because it was convenient.

If a question comes up that is not blocking, **do not stop to ask**:

```
py tools/loop.py queue --question "..." --default "..." --rationale "..."
```

Carry on with everything the question does not block. If it *is* blocking and
irreversible, add `--irreversible` and go to step 8 — it waits, however long it
takes. If it is blocking and reversible, queue it and take the default now.

## 5. Verify it — this is the step that makes the rest legitimate

**Autonomy without verification is recklessness.** Never declare a task done on
the strength of "it ran". Use every check the task affords:

- `py tools/loop.py check` — the plan is still coherent.
- `py -m pytest -q` locally, or `lw_test` on Marco's machine.
- For anything that produces geometry: **render it and look at it.**
  ```
  py tools/render_dxf.py <file>.dxf out.png --stats
  ```
  Then read the PNG yourself. On 17/09/2026 a drawing that was numerically
  perfect turned out to be visually empty; the numbers had said nothing was
  wrong. **Check the picture and the numbers. A shape can look right at the
  wrong size, and a correct size can be invisible.**
- Where a golden image exists, `py tools/visual_check.py compare ...`. When it
  fails it writes a side-by-side diff — look at that too.
- After pushing, read CI yourself: `lw_gh op=runs`, then `op=jobs`, then
  `op=run_log`. Never assume green.

If the definition of done is not met, the task is not done. Say so, leave it
`doing` or `block` it with a reason, and move on rather than pretending.

## 6. Commit it

Only through `lw_git`. Never any other way:

```
lw_git op=commit message="<plain ASCII subject, under 72 chars>"
lw_git op=push
```

`lw_git` builds the message server-side, forces plain ASCII, and passes argv
lists — because PowerShell mangles nested quotes and the commit then silently
does not happen while the push reports "Everything up-to-date". After a push it
prints local and remote HEAD: **read them.** If it says NOT IN SYNC, the push
did not land, whatever else the output said.

If git complains about `index.lock`, run `lw_git op=unlock` and retry.

## 7. Update the state and the memory

```
py tools/loop.py finish <TASK-ID>
```

Then update `project_context.md`: goal, current status, last action, critical
data, next steps. **Overwrite what is obsolete** — the file stays short on
purpose.

## 8. Write the report and stop, or continue

```
py tools/loop.py report --did "..." --verified "..." --pictures out/*.png
```

The report is a digest readable in thirty seconds: what was done, what was
decided and why, what is wanted from Marco, with the pictures attached.

Then:

- If `gate_width` allows and there is another unblocked task, **go back to
  step 3** and keep going.
- At a gate, out of work, or facing something irreversible: stop, and give
  Marco the report in Italian, in plain words.

## What Marco says, and what it means

| He says | Do |
|---|---|
| "vai" | `py tools/loop.py go`, then start at step 1 |
| "fermati" | `py tools/loop.py stop` |
| "a che punto siamo?" | answer from `loop.py status`, never from memory |
| "voglio X" | find every affected task, ADR, module and test; update them all; re-plan; say what changed |
| "questa scelta non mi piace" | `loop.py decide` the other way, record why, re-plan what depended on it |
| "fammi vedere" | render the current state and show him the picture |
| "questa regola tienila" | write it into the `linework-operativita` skill |
| "fermati dopo ogni cosa" / "vai avanti quanto puoi" | `loop.py gate task` / `loop.py gate run` |

## The three rules that outrank convenience

1. **Marco never opens a terminal, never writes a commit message, never edits a
   backlog, never pastes a prompt.** A design that needs one of those has failed
   the brief. Find another way, or tell him plainly why it is impossible. **A
   manual step he does not know about is worse than one he does.**
2. **Irreversible actions never take a default.** They wait.
3. **The loop is the first prototype of the product.** If it cannot be made to
   work honestly here — autonomous, bridled, self-verifying, with persistent
   memory, steered by a sentence — it has no business being shipped to anyone.
