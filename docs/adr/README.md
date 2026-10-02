# Architecture decision records

Frozen decisions, numbered. A decision is changed by a new ADR that supersedes
the old one, never by editing it quietly.

| No. | Title | Status |
|---|---|---|
| [0001](0001-thinking-is-free-the-hand-is-guided.md) | Thinking is free, the hand is guided | accepted, 2026-09-30 |
| [0002](0002-the-memory-model.md) | The memory model | accepted, 2026-09-30 |
| 0003 | *not written yet* — the number was left free when the plan named the licence ADR 0004 | — |
| [0004](0004-licence.md) | The licence: GPL-2.0-or-later | accepted, 2026-09-30 |
| [0005](0005-the-commitment-form.md) | The commitment form | accepted, 2026-10-01 |
| [0006](0006-the-script-language.md) | The script language | accepted, 2026-10-01 |
| [0007](0007-intent-and-alternatives.md) | Design intent and alternatives | accepted, 2026-10-01 |
| [0008](0008-the-blank-page.md) | The blank page: anchoring by rule | accepted, 2026-10-02 |
| [0009](0009-the-escape-hatch.md) | The escape hatch and its boundary | accepted, 2026-10-02 |
| [0010](0010-exact-numbers.md) | Exact numbers in the solver: algebraic, never floats | accepted, 2026-10-02 |
| [0011](0011-drafting-operations.md) | Drafting operations: exact, and refused when ambiguous | accepted, 2026-10-02 |
| [0012](0012-contours-close-exactly.md) | Contours close exactly, or are reported open | accepted, 2026-10-02 |
| [0013](0013-distributions-notable-points-edges.md) | Distributions, notable points, and edges as targets | accepted, 2026-10-02 |

Each ADR states its status, date, context, decision, consequences, and how it is
verified. `tests/test_repo_shape.py` checks the ones the plan depends on.
