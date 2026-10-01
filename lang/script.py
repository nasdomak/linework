"""lang.script -- the script language: readable, correctable, re-runnable.

ADR 0001: the engine writes the script, never the model. ADR 0006: what the
script is. The specification, with worked examples, is docs/SCRIPT.md.

A script is a plain text file, one decision per line:

    linework script 1
    domain architecture

    add wall wall_north: at origin, length 5 m
    add window w1: on wall_north, centred on wall_north, width 120 cm  # sill from the standard

Every statement is exactly one commitment form (ADR 0005) written as a sentence.
`parse` reads text into a Script; `str(script)` prints it back, and for text
written in the canonical layout the two are exact inverses. `from_forms` is the
engine writing a script from forms the gate accepted; `Script.forms()` turns a
script back into forms; `check` runs every statement through the form
validator, in order, against the drawing the script itself builds up.

Every error names the line, and the column when there is one:

    line 4, column 31: "6,5" is not a number here: write 6.5 -- in a script
    the comma separates clauses

Command line (from the repository root):

    python3 -m lang.script check FILE...   parse and validate scripts

Standard library only (CORE package).
"""

import difflib
import os
import re
import sys

from lang import form as _form

HEADER = "linework script 1"
SCRIPT_VERSION = 1

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = os.path.join(ROOT, "docs", "SCRIPT.md")

# How each relation is spelled. The words come from the catalogue's relation
# names; the parameter phrasing is fixed here, one way per parameter.
#   target   -- the relation name with "_" written as a space, then the targets
#   "and"    -- joins the two targets of "between"
#   by D     -- distance        on side S -- side
#   on axis A -- axis           in N copies -- count
PARAM_ORDER = ("distance", "side", "axis", "count")

_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_NAME_RE = re.compile(_form.NAME_PATTERN)


class ScriptError(Exception):
    """A script that cannot be read. Always says where."""

    def __init__(self, line, message, column=None, source=None):
        self.line, self.column, self.message, self.source = line, column, message, source
        Exception.__init__(self, str(self))

    def __str__(self):
        where = "line %d" % self.line
        if self.column is not None:
            where += ", column %d" % self.column
        return "%s: %s" % (where, self.message)


# ------------------------------------------------------------------ the model

class Blank(object):
    def __init__(self, line=0):
        self.line = line

    def __str__(self):
        return ""


class Comment(object):
    def __init__(self, text, line=0):
        self.text, self.line = text, line

    def __str__(self):
        return ("# " + self.text) if self.text else "#"


class Domain(object):
    def __init__(self, name, line=0):
        self.name, self.line = name, line

    def __str__(self):
        return "domain " + self.name


class Clause(object):
    """One clause of a statement, in the order it was written.

    kind "relation": word, targets, params (dict)
    kind "dimension": word (quantity), value, unit (None for a count)
    kind "property": word, value
    kind "text": value
    """

    def __init__(self, kind, word=None, value=None, unit=None, targets=None, params=None):
        self.kind, self.word, self.value, self.unit = kind, word, value, unit
        self.targets = list(targets or [])
        self.params = dict(params or {})

    def __str__(self):
        if self.kind == "dimension":
            return "%s %s" % (self.word, fmt_quantity(self.value, self.unit))
        if self.kind == "property":
            return "%s %s" % (self.word, self.value)
        if self.kind == "text":
            return "text " + quote(self.value)
        out = self.word.replace("_", " ") + " " + " and ".join(self.targets)
        for p in PARAM_ORDER:
            if p not in self.params:
                continue
            v = self.params[p]
            if p == "distance":
                out += " by " + fmt_quantity(*v)
            elif p == "side":
                out += " on side " + v
            elif p == "axis":
                out += " on axis " + v
            elif p == "count":
                out += " in %s copies" % fmt_number(v)
        return out

    def said(self):
        """The words a number in this clause came from: the clause itself."""
        return str(self)


class Statement(object):
    def __init__(self, act, kind, name, clauses=None, reason=None, domain=None, line=0):
        self.act, self.kind, self.name = act, kind, name
        self.clauses = list(clauses or [])
        self.reason, self.domain, self.line = reason, domain, line

    def __str__(self):
        out = "%s %s %s" % (self.act, self.kind, self.name)
        if self.clauses:
            out += ": " + ", ".join(str(c) for c in self.clauses)
        if self.reason:
            out += "  # " + self.reason
        return out

    def form(self):
        """The commitment form this statement stands for."""
        f = {"form": _form.FORM_TAG, "version": _form.FORM_VERSION,
             "domain": self.domain, "act": self.act,
             "object": {"kind": self.kind, "name": self.name}}
        for c in self.clauses:
            if c.kind == "relation":
                r = {"relation": c.word, "to": list(c.targets)}
                for p, v in c.params.items():
                    if p == "distance":
                        r[p] = {"value": v[0], "unit": v[1], "said": fmt_quantity(*v)}
                    elif p == "count":
                        r[p] = {"value": v, "said": fmt_number(v)}
                    else:
                        r[p] = v
                f.setdefault("relations", []).append(r)
            elif c.kind == "dimension":
                d = {"value": c.value, "said": c.said()}
                if c.unit is not None:
                    d["unit"] = c.unit
                f.setdefault("dimensions", {})[c.word] = d
            elif c.kind == "property":
                f.setdefault("properties", {})[c.word] = c.value
            elif c.kind == "text":
                f["text"] = c.value
        if self.reason:
            f["reason"] = self.reason
        return f


class Script(object):
    def __init__(self, items=None):
        self.items = list(items or [])

    def statements(self):
        return [i for i in self.items if isinstance(i, Statement)]

    def forms(self):
        return [s.form() for s in self.statements()]

    def __str__(self):
        return "\n".join([HEADER] + [str(i) for i in self.items]) + "\n"


# ------------------------------------------------------------------ printing

def fmt_number(v):
    if isinstance(v, bool):
        raise ValueError("not a number: %r" % (v,))
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer()):
        return str(int(v))
    text = repr(float(v))
    if "e" in text or "E" in text:
        text = ("%.15f" % v).rstrip("0").rstrip(".")
    return text


def fmt_quantity(value, unit):
    return fmt_number(value) if unit is None else "%s %s" % (fmt_number(value), unit)


def quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ------------------------------------------------------------------- parsing

class _Line(object):
    """Tokenising one line, keeping the column of every piece."""

    def __init__(self, number, text, cat):
        self.n, self.text, self.cat = number, text, cat

    def fail(self, message, col=None):
        raise ScriptError(self.n, message, None if col is None else col + 1, self.text)

    def split_comment(self):
        """Code and trailing comment, ignoring a # inside quotes."""
        in_q = esc = False
        for i, ch in enumerate(self.text):
            if esc:
                esc = False
            elif ch == "\\" and in_q:
                esc = True
            elif ch == '"':
                in_q = not in_q
            elif ch == "#" and not in_q:
                return self.text[:i], self.text[i + 1:].strip(), i
        if in_q:
            self.fail("a text is opened with \" but never closed", self.text.index('"'))
        return self.text, None, None

    def split_clauses(self, start, end):
        """Comma-separated pieces of text[start:end] as (column, text)."""
        out, in_q, esc, begin = [], False, False, start
        for i in range(start, end):
            ch = self.text[i]
            if esc:
                esc = False
            elif ch == "\\" and in_q:
                esc = True
            elif ch == '"':
                in_q = not in_q
            elif ch == "," and not in_q:
                if 0 < i < len(self.text) - 1 and self.text[i - 1].isdigit() \
                        and self.text[i + 1].isdigit():
                    m0 = re.search(r"-?[\d.]+$", self.text[:i])
                    m1 = re.match(r"[\d.]+", self.text[i + 1:])
                    number = self.text[m0.start():i + 1 + m1.end()]
                    self.fail('"%s" is not a number here: write %s -- in a script the comma '
                              "separates clauses" % (number, number.replace(",", ".")),
                              m0.start())
                out.append((begin, self.text[begin:i]))
                begin = i + 1
        out.append((begin, self.text[begin:end]))
        return out


def _tokens(col, text):
    """Words of a clause with their columns; a quoted text is one token."""
    out, i = [], 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text[i] == '"':
            j, buf, esc = i + 1, [], False
            while j < len(text):
                ch = text[j]
                if esc:
                    if ch not in '"\\':
                        return out + [(col + j - 1, None, "bad-escape")]
                    buf.append(ch)
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    break
                else:
                    buf.append(ch)
                j += 1
            out.append((col + i, "".join(buf), "text"))
            i = j + 1
            continue
        j = i
        while j < len(text) and not text[j].isspace() and text[j] != '"':
            j += 1
        out.append((col + i, text[i:j], "word"))
        i = j
    return out


def _number(L, col, word, what):
    if word is None or not _NUM_RE.match(word):
        if word and re.match(r"^-?\d+,\d+$", word):
            L.fail('"%s" is not a number here: write %s -- in a script the comma separates '
                   "clauses" % (word, word.replace(",", ".")), col)
        L.fail('%s needs a number, but "%s" is not one' % (what, word or ""), col)
    v = float(word)
    return int(v) if "." not in word else v


def _need(L, toks, i, what, after_col):
    if i >= len(toks):
        L.fail("%s is missing here" % what, after_col)
    return toks[i]


def _name(L, tok, what):
    col, word, typ = tok
    if typ != "word" or not _NAME_RE.match(word):
        L.fail('%s must be a name (lower-case letters, digits, underscores), not "%s"'
               % (what, word if word is not None else ""), col)
    return word


def _unit(L, toks, i, quantity, cat, end_col):
    measure = cat["quantities"][quantity]["measure"]
    if measure == "count":
        return None, i
    units = sorted(u for u, e in cat["units"].items() if e["measure"] == measure)
    col, word, _ = _need(L, toks, i, "the unit of %s (%s)" % (quantity, ", ".join(units)), end_col)
    if word not in units:
        L.fail('"%s" is not a unit of %s; use one of: %s' % (word, quantity, ", ".join(units)), col)
    return word, i + 1


def _relation_heads(cat):
    """First word of each relation as written -> list of (words, relation)."""
    heads = {}
    for rel in cat["relations"]:
        words = rel.split("_")
        heads.setdefault(words[0], []).append((words, rel))
    return heads


def _clause(L, col, text, cat):
    toks = _tokens(col, text)
    for c, w, typ in toks:
        if typ == "bad-escape":
            L.fail('inside a text only \\" and \\\\ may follow a backslash', c)
    end = col + len(text.rstrip())
    if not toks:
        L.fail("an empty clause: two commas in a row, or a comma at the end", col)
    c0, w0, t0 = toks[0]
    if t0 == "text":
        L.fail("a text must be introduced by the word text", c0)

    if w0 == "text":
        if len(toks) != 2 or toks[1][2] != "text":
            L.fail('text is written as: text "the words"', c0)
        return Clause("text", value=toks[1][1])

    if w0 in cat["quantities"]:
        _, vw, _ = _need(L, toks, 1, "the value of %s" % w0, end)
        value = _number(L, toks[1][0], vw, w0)
        unit, i = _unit(L, toks, 2, w0, cat, end)
        if i < len(toks):
            L.fail('unexpected "%s" after %s' % (toks[i][1], w0), toks[i][0])
        return Clause("dimension", word=w0, value=value, unit=unit)

    if w0 in cat["properties"]:
        if len(toks) != 2 or toks[1][2] != "word":
            L.fail("%s is written as: %s <value>" % (w0, w0), c0)
        return Clause("property", word=w0, value=toks[1][1])

    for words, rel in sorted(_relation_heads(cat).get(w0, []), key=lambda x: -len(x[0])):
        if [t[1] for t in toks[:len(words)]] != words:
            continue
        spec = cat["relations"][rel]
        i = len(words)
        targets = [_name(L, _need(L, toks, i, "the object it is %s" % " ".join(words), end),
                         "what follows \"%s\"" % " ".join(words))]
        i += 1
        if spec["targets"] == 2:
            tok = _need(L, toks, i, 'the word "and" and a second object', end)
            if tok[1] != "and":
                L.fail('"%s" takes two objects: %s X and Y' % (" ".join(words), " ".join(words)),
                       tok[0])
            targets.append(_name(L, _need(L, toks, i + 1, "the second object", end),
                                 'what follows "and"'))
            i += 2
        params = {}
        while i < len(toks):
            c, w, _ = toks[i]
            if w == "by" and "distance" in spec["params"]:
                _, vw, _ = _need(L, toks, i + 1, "the distance after by", end)
                value = _number(L, toks[i + 1][0], vw, "by")
                unit, i = _unit(L, toks, i + 2, "distance", cat, end)
                params["distance"] = (value, unit)
            elif w == "on" and i + 1 < len(toks) and toks[i + 1][1] in ("side", "axis") \
                    and toks[i + 1][1] in spec["params"]:
                p = toks[i + 1][1]
                c2, v, _ = _need(L, toks, i + 2, "the %s after \"on %s\"" % (p, p), end)
                params[p] = v
                i += 3
            elif w == "in" and "count" in spec["params"]:
                _, vw, _ = _need(L, toks, i + 1, "the number of copies", end)
                n = _number(L, toks[i + 1][0], vw, "in ... copies")
                c3, cw, _ = _need(L, toks, i + 2, 'the word "copies"', end)
                if cw != "copies":
                    L.fail('write "in %s copies"' % vw, c3)
                params["count"] = n
                i += 3
            else:
                allowed = []
                for p in sorted(spec["params"]):
                    allowed.append({"distance": "by <distance>", "side": "on side <side>",
                                    "axis": "on axis <axis>", "count": "in <n> copies"}[p])
                if allowed:
                    L.fail('unexpected "%s" after "%s %s"; it takes only: %s'
                           % (w, " ".join(words), " and ".join(targets), "; ".join(allowed)), c)
                L.fail('unexpected "%s": "%s" takes nothing after its object'
                       % (w, " ".join(words)), c)
        return Clause("relation", word=rel, targets=targets, params=params)

    known = sorted(set([r.split("_")[0] for r in cat["relations"]]) | set(cat["quantities"])
                   | set(cat["properties"]) | {"text"})
    close = difflib.get_close_matches(w0 or "", known, n=1, cutoff=0.6)
    hint = ' Did you mean "%s"?' % close[0] if close else ""
    L.fail('a clause cannot start with "%s".%s It starts with a relation, a dimension, a '
           "property or text: %s" % (w0, hint, ", ".join(known)), c0)


def parse(text, catalogue=None):
    """Read a script. Raises ScriptError naming the line and column."""
    cat = catalogue or _form.default_catalogue()
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0].rstrip("\r") != HEADER:
        raise ScriptError(1, 'a script starts with the line "%s"' % HEADER)
    items, domain = [], None
    for n, raw in enumerate(lines[1:], start=2):
        L = _Line(n, raw.rstrip("\r"), cat)
        if "\t" in L.text:
            L.fail("a tab: use spaces", L.text.index("\t"))
        stripped = L.text.strip()
        if not stripped:
            items.append(Blank(n))
            continue
        if stripped.startswith("#"):
            items.append(Comment(stripped[1:].strip(), n))
            continue
        code, reason, _ = L.split_comment()
        words = code.split()
        if words[0] == "domain":
            if len(words) != 2:
                L.fail("domain is written as: domain <name>", 0)
            if words[1] not in cat["domains"]:
                L.fail('"%s" is not a domain; use one of: %s'
                       % (words[1], ", ".join(sorted(cat["domains"]))), L.text.index(words[1]))
            domain = words[1]
            items.append(Domain(domain, n))
            continue
        if words[0] not in cat["acts"]:
            L.fail('a line starts with domain, #, or an act (%s), not "%s"'
                   % (", ".join(sorted(cat["acts"])), words[0]), L.text.index(words[0]))
        if domain is None:
            L.fail('no domain yet: write "domain <name>" before the first statement')
        colon = code.find(":")
        head_end = colon if colon >= 0 else len(code)
        head = _tokens(0, code[:head_end])
        if len(head) > 3:
            L.fail('a colon must follow the name "%s"; then come the clauses'
                   % head[2][1], head[3][0])
        if len(head) != 3:
            L.fail("a statement starts with: <act> <kind> <name>, then a colon and its "
                   "clauses", 0)
        act, kind_tok, name_tok = head
        kind = kind_tok[1]
        if kind not in cat["objects"]:
            L.fail('"%s" is not an object kind' % kind, kind_tok[0])
        name = _name(L, name_tok, "the object's name")
        clauses = []
        if colon >= 0:
            for col, piece in L.split_clauses(colon + 1, len(code)):
                clauses.append(_clause(L, col, piece, cat))
            if not code[colon + 1:].strip():
                L.fail("a colon with nothing after it", colon)
        items.append(Statement(act[1], kind, name, clauses, reason or None, domain, n))
    while items and isinstance(items[-1], Blank):
        items.pop()
    return Script(items)


# ------------------------------------------------------------ the engine side

def statement_from_form(form):
    """The engine writes one line from a form the gate accepted."""
    clauses = []
    for r in form.get("relations", []):
        params = {}
        for p in PARAM_ORDER:
            if p not in r:
                continue
            v = r[p]
            if p == "distance":
                params[p] = (v["value"], v["unit"])
            elif p == "count":
                params[p] = v["value"]
            else:
                params[p] = v
        clauses.append(Clause("relation", word=r["relation"], targets=r["to"], params=params))
    for q, v in form.get("dimensions", {}).items():
        clauses.append(Clause("dimension", word=q, value=v["value"], unit=v.get("unit")))
    for p, v in form.get("properties", {}).items():
        clauses.append(Clause("property", word=p, value=v))
    if "text" in form:
        clauses.append(Clause("text", value=form["text"]))
    reason = form.get("reason")
    if reason:
        reason = " ".join(reason.split())
    return Statement(form["act"], form["object"]["kind"], form["object"]["name"], clauses,
                     reason or None, form["domain"])


def from_forms(forms, known=None, user_texts=None):
    """Write a script from forms. Every form must pass the gate first: a form the
    validator refuses never becomes a line (ADR 0001). Raises ValueError naming
    the form and the reasons."""
    known = dict(known or {})
    items, domain = [], None
    for i, f in enumerate(forms):
        user = user_texts[i] if user_texts else None
        v = _form.validate(f, user_text=user, known=known)
        if not v.ok:
            raise ValueError("form %d is refused, so it is not written:\n%s"
                             % (i + 1, v.explain()))
        if f["domain"] != domain:
            if items:
                items.append(Blank())
            domain = f["domain"]
            items.append(Domain(domain))
        items.append(statement_from_form(f))
        _apply(known, f)
    return Script(items)


def _apply(known, f):
    name = f["object"]["name"]
    if f["act"] == "add":
        known[name] = f["object"]["kind"]
    elif f["act"] == "remove":
        known.pop(name, None)


def check(script, known=None):
    """Validate every statement, in order, against the drawing built so far.
    Returns a list of ScriptError (empty when the script is sound)."""
    known = dict(known or {})
    errors = []
    for s in script.statements():
        f = s.form()
        v = _form.validate(f, known=known)
        for p in v.problems:
            errors.append(ScriptError(s.line, _locate(s, p), source=str(s)))
        if v.ok:
            _apply(known, f)
    return errors


def _locate(statement, problem):
    """Say a form problem in the script's own words: which clause it is about."""
    m = re.match(r"^(relations)\[(\d+)\]|^(dimensions|properties)\.(\w+)|^(text)\b",
                 problem.path or "")
    clause = None
    if m and m.group(1):
        rels = [c for c in statement.clauses if c.kind == "relation"]
        clause = rels[int(m.group(2))] if int(m.group(2)) < len(rels) else None
    elif m and m.group(3):
        kind = "dimension" if m.group(3) == "dimensions" else "property"
        found = [c for c in statement.clauses if c.kind == kind and c.word == m.group(4)]
        clause = found[0] if found else None
    elif m and m.group(5):
        found = [c for c in statement.clauses if c.kind == "text"]
        clause = found[0] if found else None
    if clause is not None:
        return 'in "%s": %s' % (clause, problem.message)
    return problem.message


def load(text, known=None):
    """Parse and check. Raises the first ScriptError found."""
    script = parse(text)
    errors = check(script, known)
    if errors:
        raise errors[0]
    return script


# ---------------------------------------------------------------- the spec

def spec_blocks(path=SPEC_PATH):
    """The fenced examples of docs/SCRIPT.md: (kind, first line number, text).

    kind is "linework" for a script that must be accepted and round-trip, and
    "linework-refused" for one that must be refused; a refused example's last
    line is a comment "# refused: line N: <message>" stating the error.
    """
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^```(linework(?:-refused)?)\s*$", lines[i])
        if m:
            j = i + 1
            while lines[j] != "```":
                j += 1
            out.append((m.group(1), i + 2, "\n".join(lines[i + 1:j]) + "\n"))
            i = j
        i += 1
    return out


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] != "check":
        print("unknown command %r; try --help" % argv[0])
        return 2
    bad = 0
    for path in argv[1:]:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        try:
            errors = check(parse(text))
        except ScriptError as exc:
            errors = [exc]
        for e in errors:
            print("%s: %s" % (path, e))
        if not errors:
            print("%s: ok" % path)
        bad += bool(errors)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
