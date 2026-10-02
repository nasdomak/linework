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


class Choice(object):
    """An open or decided choice between alternatives (P1-T03, ADR 0006).

    choice entrance: open  # where does the entrance go?
    choice entrance: decided b  # the user wants the garden side
    """

    def __init__(self, name, decided=None, reason=None, line=0):
        self.name, self.decided, self.reason, self.line = name, decided, reason, line
        self.options = []

    def labels(self):
        out = []
        for o in self.options:
            if o.label not in out:
                out.append(o.label)
        return out

    def option_statements(self, label):
        return [o.statement for o in self.options if o.label == label]

    def __str__(self):
        out = "choice %s: %s" % (self.name, "open" if self.decided is None
                                 else "decided " + self.decided)
        if self.reason:
            out += "  # " + self.reason
        return out


class Option(object):
    """One line of one alternative: option <choice> <label>: <statement>"""

    def __init__(self, choice, label, statement, line=0):
        self.choice, self.label, self.statement, self.line = choice, label, statement, line

    def __str__(self):
        return "option %s %s: %s" % (self.choice, self.label, self.statement)


# ------------------------------------------------- the free channel (P1-T05)

FREE_SOURCES = ("user", "model", "import")
FREE_RELATIONS = ("at", "centred_on", "next_to", "offset_from", "aligned_with", "inside")
FREE_MAX_PARTS = 100
_FREE_PART_RE = {
    "line": re.compile(r"^line (\S+) (\S+) to (\S+) (\S+)$"),
    "circle": re.compile(r"^circle (\S+) (\S+) radius (\S+)$"),
    "arc": re.compile(r"^arc (\S+) (\S+) radius (\S+) from (\S+) to (\S+)$"),
}
FREE_PART_FORMS = ('"line X Y to X Y", "circle X Y radius R" or "arc X Y radius R from A to '
                   'A" (degrees, counter-clockwise)')


class Free(object):
    """Geometry the language cannot say (ADR 0009). Its SHAPE is free; its place
    is not: it is placed by the same checked relations as everything else, by its
    local origin (0 0). It states where it came from and why, it is drawn on its
    own layer, and checked geometry may never be placed by it.

    free cam: source user, at origin, unit mm, shape "line 0 0 to 120 0; ..."  # why
    """

    act, kind = "add", "free"

    def __init__(self, name, parts, line=0):
        self.name, self.parts, self.line = name, list(parts), line
        self.reason, self.domain = None, None

    def _get(self, key):
        for k, v in self.parts:
            if k == key:
                return v
        return None

    @property
    def source(self):
        return self._get("source")

    @property
    def unit(self):
        return self._get("unit")

    @property
    def shape(self):
        """[(primitive, numbers...)] in local coordinates, in `unit`."""
        return self._get("shape")

    @property
    def clauses(self):
        return [v for k, v in self.parts if k == "relation"]

    def shape_text(self):
        out = []
        for prim in self.shape:
            n = [fmt_number(x) for x in prim[1:]]
            if prim[0] == "line":
                out.append("line %s %s to %s %s" % tuple(n))
            elif prim[0] == "circle":
                out.append("circle %s %s radius %s" % tuple(n))
            else:
                out.append("arc %s %s radius %s from %s to %s" % tuple(n))
        return "; ".join(out)

    def __str__(self):
        pieces = []
        for k, v in self.parts:
            if k == "relation":
                pieces.append(str(v))
            elif k == "shape":
                pieces.append("shape " + quote(self.shape_text()))
            else:
                pieces.append("%s %s" % (k, v))
        return "free %s: %s  # %s" % (self.name, ", ".join(pieces), self.reason)


class OpenChoiceError(ScriptError):
    """Raised when a script with an open choice is asked for geometry."""


class Script(object):
    def __init__(self, items=None):
        self.items = list(items or [])

    def statements(self):
        """The statements outside any choice."""
        return [i for i in self.items if isinstance(i, Statement)]

    def free(self):
        """Every object that came through the free channel (ADR 0009)."""
        return [i for i in self.items if isinstance(i, Free)]

    def choices(self):
        return [i for i in self.items if isinstance(i, Choice)]

    def open_choices(self):
        return [c for c in self.choices() if c.decided is None]

    def drawable(self):
        """The statements to draw, in order, with every decided choice replaced by
        its chosen option. An open choice cannot be drawn: this raises
        OpenChoiceError naming every open choice and its options."""
        open_ = self.open_choices()
        if open_:
            what = ["%s (line %d, options %s)" % ('"%s"' % c.name, c.line,
                                                  ", ".join(c.labels())) for c in open_]
            if len(open_) == 1:
                msg = ('cannot draw: choice "%s" is still open -- options %s; decide it '
                       "first" % (open_[0].name, ", ".join(open_[0].labels())))
            else:
                msg = ("cannot draw: %d choices are still open: %s; decide them first"
                       % (len(open_), "; ".join(what)))
            raise OpenChoiceError(open_[0].line, msg)
        out = []
        for item in self.items:
            if isinstance(item, (Statement, Free)):
                out.append(item)
            elif isinstance(item, Choice):
                out.extend(item.option_statements(item.decided))
        return out

    def decide(self, choice, label, reason=None):
        """A new script with `choice` decided as `label`. The alternatives stay in
        the script: they are the record of what was considered."""
        new = parse(str(self))
        found = [c for c in new.choices() if c.name == choice]
        if not found:
            raise ValueError('there is no choice called "%s"' % choice)
        c = found[0]
        if label not in c.labels():
            raise ValueError('choice "%s" has no option "%s"; its options are %s'
                             % (choice, label, ", ".join(c.labels())))
        c.decided = label
        if reason is not None:
            c.reason = " ".join(reason.split()) or None
        return parse(str(new))

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


def _edge(L, toks, i, targets, cat):
    """An edge or corner word right after a target ("plate1 top") joins it (D-003).
    Whether the relation accepts one is the form's call, with its own message."""
    if i < len(toks) and toks[i][2] == "word" and toks[i][1] in cat.get("edges", {}):
        targets[-1] = "%s %s" % (targets[-1], toks[i][1])
        return i + 1
    return i


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
        i = _edge(L, toks, i, targets, cat)
        if spec["targets"] == 2:
            tok = _need(L, toks, i, 'the word "and" and a second object', end)
            if tok[1] != "and":
                L.fail('"%s" takes two objects: %s X and Y' % (" ".join(words), " ".join(words)),
                       tok[0])
            targets.append(_name(L, _need(L, toks, i + 1, "the second object", end),
                                 'what follows "and"'))
            i += 2
            i = _edge(L, toks, i, targets, cat)
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


def _statement(L, code, start, domain, reason, cat):
    """Read "<act> <kind> <name>: <clauses>" from code[start:]."""
    if domain is None:
        L.fail('no domain yet: write "domain <name>" before the first statement')
    colon = code.find(":", start)
    head_end = colon if colon >= 0 else len(code)
    head = _tokens(start, code[start:head_end])
    if len(head) > 3:
        L.fail('a colon must follow the name "%s"; then come the clauses'
               % head[2][1], head[3][0])
    if len(head) != 3:
        L.fail("a statement starts with: <act> <kind> <name>, then a colon and its "
               "clauses", start)
    act, kind_tok, name_tok = head
    if act[1] not in cat["acts"]:
        L.fail('a statement starts with an act (%s), not "%s"'
               % (", ".join(sorted(cat["acts"])), act[1]), act[0])
    kind = kind_tok[1]
    if kind not in cat["objects"]:
        L.fail('"%s" is not an object kind' % kind, kind_tok[0])
    name = _name(L, name_tok, "the object's name")
    clauses = []
    if colon >= 0:
        for col, piece in L.split_clauses(colon + 1, len(code)):
            clauses.append(_clause(L, col, piece, cat))
    return Statement(act[1], kind, name, clauses, reason or None, domain, L.n)


def _choice(L, code, reason):
    """choice <name>: open | choice <name>: decided <label>"""
    colon = code.find(":")
    head = _tokens(0, code[:colon if colon >= 0 else len(code)])
    if len(head) != 2 or colon < 0:
        L.fail("a choice is written as: choice <name>: open -- or -- choice <name>: "
               "decided <option>", head[min(len(head), 3) - 1][0] if len(head) > 2 else 0)
    name = _name(L, head[1], "the choice's name")
    rest = _tokens(colon + 1, code[colon + 1:])
    if [t[1] for t in rest] == ["open"]:
        return Choice(name, None, reason or None, L.n)
    if len(rest) == 2 and rest[0][1] == "decided":
        return Choice(name, _name(L, rest[1], "the option decided"), reason or None, L.n)
    L.fail('after "choice %s:" comes "open" or "decided <option>"' % name,
           rest[0][0] if rest else colon)


def _option(L, code, domain, reason, cat):
    """option <choice> <label>: <statement>"""
    colon = code.find(":")
    head = _tokens(0, code[:colon if colon >= 0 else len(code)])
    if len(head) != 3 or colon < 0:
        L.fail("an option is written as: option <choice> <label>: <statement>",
               head[3][0] if len(head) > 3 else 0)
    choice = _name(L, head[1], "the choice an option belongs to")
    label = _name(L, head[2], "the option's label")
    start = colon + 1
    while start < len(code) and code[start] == " ":
        start += 1
    if start >= len(code):
        L.fail("an option holds a statement after its colon", colon)
    return Option(choice, label, _statement(L, code, start, domain, reason, cat), L.n)


def _free_shape(L, col, text):
    parts = [p.strip() for p in text.split(";")]
    if len(parts) > FREE_MAX_PARTS:
        L.fail("a free shape holds at most %d parts, not %d: the free channel is for what "
               "the language cannot say, not a second way to draw" % (FREE_MAX_PARTS,
                                                                       len(parts)), col)
    out = []
    for i, part in enumerate(parts, start=1):
        part = " ".join(part.split())
        m = None
        for prim, rx in _FREE_PART_RE.items():
            m = rx.match(part)
            if m:
                break
        if not m:
            L.fail('in the shape, part %d "%s": a part is %s' % (i, part, FREE_PART_FORMS), col)
        nums = []
        for w in m.groups():
            if not _NUM_RE.match(w):
                fix = (": write %s" % w.replace(",", ".")) if re.match(r"^-?\d+,\d+$", w) \
                    else ""
                L.fail('in the shape, part %d "%s": "%s" is not a number%s'
                       % (i, part, w, fix), col)
            nums.append(float(w) if "." in w else int(w))
        if prim in ("circle", "arc") and nums[2] <= 0:
            L.fail('in the shape, part %d "%s": a radius must be greater than zero'
                   % (i, part), col)
        if prim == "arc" and not all(-360 <= a <= 360 for a in nums[3:]):
            L.fail('in the shape, part %d "%s": angles lie between -360 and 360 degrees'
                   % (i, part), col)
        out.append(tuple([prim] + nums))
    return out


def _free(L, code, reason, domain, cat):
    """free <name>: source S, unit U, shape "...", <placing relations>  # why"""
    colon = code.find(":")
    head = _tokens(0, code[:colon if colon >= 0 else len(code)])
    if len(head) != 2 or colon < 0:
        L.fail('a free object is written as: free <name>: source <who>, <where>, unit <u>, '
               'shape "..."  # why', head[2][0] if len(head) > 2 else 0)
    name = _name(L, head[1], "the free object's name")
    parts, seen = [], set()
    for col, piece in L.split_clauses(colon + 1, len(code)):
        toks = _tokens(col, piece)
        if not toks:
            L.fail("an empty clause: two commas in a row, or a comma at the end", col)
        c0, w0, _ = toks[0]
        if w0 in ("source", "unit", "shape"):
            if w0 in seen:
                L.fail('"%s" is given twice' % w0, c0)
            seen.add(w0)
            if len(toks) != 2:
                L.fail('%s is written as: %s' % (w0, {"source": "source user|model|import",
                                                       "unit": "unit mm|cm|m",
                                                       "shape": 'shape "..."'}[w0]), c0)
            c1, v, typ = toks[1]
            if w0 == "source":
                if v not in FREE_SOURCES:
                    L.fail('"%s" is not a source; a free object comes from: %s'
                           % (v, ", ".join(FREE_SOURCES)), c1)
                parts.append(("source", v))
            elif w0 == "unit":
                if v not in ("mm", "cm", "m"):
                    L.fail('"%s" is not a length unit; use one of: cm, m, mm' % v, c1)
                parts.append(("unit", v))
            else:
                if typ != "text":
                    L.fail('the shape is written in quotes: shape "line 0 0 to 10 0"', c1)
                parts.append(("shape", _free_shape(L, c1, v)))
            continue
        clause = _clause(L, col, piece, cat)
        if clause.kind != "relation":
            L.fail('a free object takes source, unit, shape and the relations that place '
                   'it; "%s" is a word for catalogue objects' % w0, c0)
        if clause.word not in FREE_RELATIONS:
            L.fail('a free object is placed with %s; "%s" would make it part of checked '
                   "geometry" % (", ".join(r.replace("_", " ") for r in FREE_RELATIONS),
                                 clause.word.replace("_", " ")), c0)
        parts.append(("relation", clause))
    for key in ("source", "unit", "shape"):
        if key not in seen:
            L.fail('a free object must give its %s' % key, colon)
    if not reason:
        L.fail("a free object must say why the language could not say it: end the line "
               "with # and the reason", len(code.rstrip()))
    f = Free(name, parts, L.n)
    f.reason, f.domain = reason, domain
    return f


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
        if words[0] == "choice":
            items.append(_choice(L, code, reason))
            continue
        if words[0] == "option":
            items.append(_option(L, code, domain, reason, cat))
            continue
        if words[0] == "free":
            items.append(_free(L, code, reason, domain, cat))
            continue
        if words[0] not in cat["acts"]:
            L.fail('a line starts with domain, choice, option, free, #, or an act (%s), not "%s"'
                   % (", ".join(sorted(cat["acts"])), words[0]), L.text.index(words[0]))
        items.append(_statement(L, code, len(code) - len(code.lstrip()), domain, reason, cat))
    while items and isinstance(items[-1], Blank):
        items.pop()
    _link_choices(items)
    return Script(items)


def _link_choices(items):
    """Options follow their choice line; a choice has two options or more; a
    decided choice names one of them. Errors point at the line at fault."""
    current, seen = None, {}

    def close(choice):
        if choice is None:
            return
        labels = choice.labels()
        if len(labels) < 2:
            raise ScriptError(choice.line, 'choice "%s" needs at least two options to choose '
                              "between; it has %d" % (choice.name, len(labels)))
        if choice.decided is not None and choice.decided not in labels:
            raise ScriptError(choice.line, 'choice "%s" is decided as "%s", but its options '
                              "are %s" % (choice.name, choice.decided, ", ".join(labels)))

    for item in items:
        if isinstance(item, Choice):
            close(current)
            if item.name in seen:
                raise ScriptError(item.line, 'there is already a choice called "%s" (line %d)'
                                  % (item.name, seen[item.name].line))
            seen[item.name] = current = item
        elif isinstance(item, Option):
            if current is None or current.name != item.choice:
                if item.choice in seen:
                    raise ScriptError(item.line, 'the options of choice "%s" must follow its '
                                      "choice line (line %d), with nothing but comments and "
                                      "blank lines in between"
                                      % (item.choice, seen[item.choice].line))
                raise ScriptError(item.line, 'there is no choice called "%s": write "choice '
                                  '%s: open" first' % (item.choice, item.choice))
            current.options.append(item)
        elif isinstance(item, (Statement, Domain, Free)):
            close(current)
            current = None
    close(current)


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

    Each option of a choice is checked on its own, from the drawing as it stands
    at the choice. After a decided choice the drawing is the chosen option's;
    after an open one it holds only what every option agrees on -- a name that
    exists, with the same kind, whichever option is taken.
    Returns a list of ScriptError (empty when the script is sound)."""
    known = dict(known or {})
    errors = []

    def run(statements, k):
        for s in statements:
            tainted = [(c, t) for c in s.clauses if c.kind == "relation"
                       for t in c.targets if k.get(_form.split_target(t)[0]) == "free"]
            if tainted:
                c, t = tainted[0]
                errors.append(ScriptError(
                    s.line, 'in "%s": "%s" is free geometry, and checked geometry is never '
                    "placed by it -- free may lean on checked, never the reverse" % (c, t),
                    source=str(s)))
                continue
            f = s.form()
            v = _form.validate(f, known=k)
            for p in v.problems:
                errors.append(ScriptError(s.line, _locate(s, p), source=str(s)))
            if v.ok:
                _apply(k, f)

    for item in script.items:
        if isinstance(item, Statement):
            run([item], known)
        elif isinstance(item, Free):
            bad = None
            if item.name in known:
                bad = '"%s" already exists (%s); a free object needs a new name' % (
                    item.name, _form._a(known[item.name]))
            elif item.name in _form.default_catalogue()["reserved_names"]:
                bad = '"%s" is a reserved name' % item.name
            else:
                for c in item.clauses:
                    missing = [t for t in (_form.split_target(x)[0] for x in c.targets)
                               if t not in known
                               and t not in _form.default_catalogue()["reserved_names"]]
                    if missing:
                        bad = 'in "%s": there is no object called "%s"' % (c, missing[0])
                        break
            if not item.clauses:
                bad = bad or ('"%s" has no place: a free shape is placed by relations like '
                              "everything else (the first object goes at origin)" % item.name)
            if bad:
                errors.append(ScriptError(item.line, bad, source=str(item)))
            else:
                known[item.name] = "free"
        elif isinstance(item, Choice):
            after = {}
            for label in item.labels():
                k = dict(known)
                run(item.option_statements(label), k)
                after[label] = k
            if item.decided is not None:
                known = after[item.decided]
            else:
                first = after[item.labels()[0]]
                known = dict((n, kind) for n, kind in first.items()
                             if all(a.get(n) == kind for a in after.values()))
    errors.sort(key=lambda e: e.line)
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
    "linework-refused" for one that must be refused, and "linework-unplaced" for
    a sound script that is not one determinate drawing (P1-T04); their last line
    is a comment "# refused: ..." or "# unplaced: ..." stating the error.
    """
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^```(linework(?:-refused|-unplaced)?)\s*$", lines[i])
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
