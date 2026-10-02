"""lang.escape -- the free channel, listed for review (P1-T05, ADR 0009).

The language cannot say everything; the free channel carries what it cannot --
the shape, never the place. Because it is the hole in the fence, everything that
came through it is listed here, separately from checked geometry, so a person
can review it on its own: where it came from, why the language was not enough,
what it is placed by, and every part of its shape.

    python3 -m lang.escape FILE...     list the free channel of each script

Standard library only (CORE package).
"""

import sys

from lang import script as _script


def report(script):
    """The review list of a script's free channel, as text."""
    free = script.free()
    total = len(free) + sum(1 for s in script.statements() if s.act == "add") \
        + sum(len(c.option_statements(c.decided)) for c in script.choices() if c.decided)
    if not free:
        return "# linework free channel -- empty: every object passed the gate\n"
    lines = ["# linework free channel -- %d of %d objects did not pass the gate; review each"
             % (len(free), total)]
    for f in free:
        placed = ", ".join(str(c) for c in f.clauses)
        lines.append("")
        lines.append("%s  line %d  source %s  %d part%s  unit %s  placed: %s"
                     % (f.name, f.line, f.source, len(f.shape), "" if len(f.shape) == 1
                        else "s", f.unit, placed))
        lines.append("  why: %s" % f.reason)
        for part in f.shape_text().split("; "):
            lines.append("  %s" % part)
    return "\n".join(lines) + "\n"


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    bad = 0
    for path in argv:
        with open(path, "r", encoding="utf-8") as fh:
            try:
                script = _script.parse(fh.read())
            except _script.ScriptError as exc:
                print("%s: %s" % (path, exc))
                bad += 1
                continue
        print("== %s" % path)
        print(report(script), end="")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
