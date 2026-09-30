# ADR 0004 — The licence: GPL-2.0-or-later

- **Status:** accepted
- **Date:** 2026-09-30
- **Decision queue entry:** `D-001` in `state/decisions.json`
- **Decided by:** the loop's default, because the question had been open since
  2026-09-17 with no answer. Reversible, and flagged to Marco in the report.

SPDX-License-Identifier: GPL-2.0-or-later

## Context

linework is meant to be free, public and open source from its first commit. A
repository published with no licence file is "all rights reserved" by default:
anyone may look at the code, nobody may legally reuse it. That contradicts the
stated ambition, so the licence has to exist before the first push.

Two different pieces of software will live in this repository, and they do not
face the same constraint:

| Piece | What it links | Constraint |
|---|---|---|
| **The engine** (`lang/`, `geometry/`, `memory/`, `engine/`, `dxf/`, `shared/`, `tools/`) | nothing of LibreCAD's. It is a standalone Python program that reads and writes DXF files, a public format, and talks to Ollama over HTTP. `ezdxf` (MIT) is its only third-party dependency, confined to `dxf/` and `tools/`. | none from LibreCAD. Any OSI licence would be legal. |
| **The C++ plugin** (`plugin/`, product phase 14) | LibreCAD's plugin headers (`qc_plugininterface.h`, `document_interface.h`) and Qt, and is loaded into the LibreCAD process. | LibreCAD is distributed under the **GNU GPL version 2**. A plugin compiled against its headers and loaded into its address space is, on the usual reading of the GPL, a combined work, so the plugin must carry a licence compatible with GPL v2. |

The evidence this rests on:

- LibreCAD is licensed under the GNU General Public License version 2 (its
  repository and its About box say so).
- GPL-3.0-**only** code cannot be combined with GPL-2.0-**only** code: the two
  licences are mutually incompatible. GPL-2.0-**or-later** code can be combined
  with either, because the recipient may choose version 2.
- A permissive licence (MIT, BSD, Apache-2.0) would be legal for the engine alone,
  but the plugin would then need a different licence from the rest of the
  repository, or the whole repository would have to change licence in phase 14.

## Decision

**The whole repository is licensed GPL-2.0-or-later.**

- **The engine may be** GPL-2.0-or-later, and is. Nothing forces that — it links
  nothing of LibreCAD's — but one licence for one repository is simpler for every
  contributor and user, and it keeps the engine combinable with LibreCAD code if a
  helper is ever shared between them.
- **The plugin must be** GPL-compatible with version 2. GPL-2.0-or-later satisfies
  that, and so does GPL-2.0-only; GPL-3.0-only would not.
- `LICENSE` at the repository root holds the unmodified text of the GNU General
  Public License version 2. The "or later" part is stated here, in the README, and
  in the SPDX line of each source file as files gain headers.

## Why not the alternatives

- **GPL-3.0-or-later** — would make the phase-14 plugin impossible to combine with
  LibreCAD's GPL v2 code. Rejected.
- **MIT / Apache-2.0 for everything** — legal today, wrong in phase 14: the plugin
  would force a split or a relicence, and a relicence across a public history with
  outside contributors needs every contributor's consent.
- **Two licences (permissive engine, GPL plugin)** — defensible, and it would let
  the engine be embedded in closed products. Nobody has asked for that; it adds a
  rule every contributor must understand. It can still be chosen later **while
  Marco is the only copyright holder** (see below).

## Consequences

- The repository can be published, forked and contributed to from the first push.
- Anyone who distributes a modified linework must publish their changes under the
  same terms. That is the intended effect.
- **Reversibility has a deadline.** Marco is the sole copyright holder until the
  first outside contribution is merged, so until then this ADR can be superseded by
  a commit. After that, changing the licence needs every contributor's agreement.
  If the licence is to change, it must change before the first outside pull
  request is merged.
- This is a reading of the licences and of common practice, **not legal advice**.
  If the licence ever matters commercially, a lawyer should confirm it.

## Verification

`tests/test_repo_shape.py` asserts that `LICENSE` exists and is the GNU GPL
version 2 text, that this ADR names `GPL-2.0-or-later` as its SPDX identifier, and
that the README's licence section names the same identifier.
