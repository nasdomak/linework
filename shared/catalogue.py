"""shared.catalogue -- load the closed vocabulary of the commitment form.

The catalogue (shared/catalogue_v1.json) is data: every word the model may use
when it commits, with its meaning (ADR 0005). This module only loads it and
checks that it is internally consistent -- that every word a kind refers to
exists, and that every word has a meaning. Validating a *form* against it is
lang.form's job.

Standard library only (CORE package).
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE_VERSION = 1
CATALOGUE_PATH = os.path.join(HERE, "catalogue_v%d.json" % CATALOGUE_VERSION)

NEEDS = ("required", "optional", "memory")
# What a relation fixes of the object's position (P1-T04, ADR 0008): the sheet
# axes x and y; "across" and "along" a side's edge or a target's long axis;
# "axis" the one named by an aligned_with relation.
FIX_KEYS = ("x", "y", "across", "along", "axis")
FIX_STRENGTHS = ("firm", "default")
PLACED_BY = ("corner",)
PARAM_NEEDS = ("required", "optional")


def load(path=CATALOGUE_PATH):
    """Return the catalogue as a dict. Raises ValueError if it is inconsistent."""
    with open(path, "r", encoding="utf-8") as fh:
        cat = json.load(fh)
    problems = check(cat)
    if problems:
        raise ValueError("the catalogue at %s is inconsistent:\n  %s"
                         % (path, "\n  ".join(problems)))
    return cat


def _meaning(where, entry, problems):
    if not isinstance(entry, dict) or not str(entry.get("meaning", "")).strip():
        problems.append("%s has no meaning" % where)


def check(cat):
    """Every internal reference resolves and every word has a meaning."""
    p = []
    if cat.get("catalogue") != "linework/catalogue":
        p.append("'catalogue' must be 'linework/catalogue'")
    if cat.get("version") != CATALOGUE_VERSION:
        p.append("'version' must be %d" % CATALOGUE_VERSION)
    for block in ("domains", "acts", "units", "measures", "quantities",
                  "parameters", "relations", "reserved_names", "properties", "objects"):
        if not isinstance(cat.get(block), dict) or not cat[block]:
            p.append("block '%s' is missing or empty" % block)
    if p:
        return p

    for block in ("domains", "acts", "units", "measures", "reserved_names",
                  "reference_points"):
        for word, entry in cat.get(block, {}).items():
            _meaning("%s.%s" % (block, word), entry, p)
    _meaning("sheet", cat.get("sheet"), p)
    if not cat.get("reference_points"):
        p.append("block 'reference_points' is missing or empty")

    for word, entry in cat["units"].items():
        if entry.get("measure") not in cat["measures"]:
            p.append("units.%s names an unknown measure" % word)
    if any(e.get("measure") == "count" for e in cat["units"].values()):
        p.append("a count takes no unit, so no unit may have measure 'count'")

    for word, entry in cat["quantities"].items():
        _meaning("quantities.%s" % word, entry, p)
        if entry.get("measure") not in cat["measures"]:
            p.append("quantities.%s names an unknown measure" % word)

    for word, entry in cat["parameters"].items():
        _meaning("parameters.%s" % word, entry, p)
        if entry.get("type") == "word":
            vals = entry.get("values")
            if not isinstance(vals, dict) or not vals:
                p.append("parameters.%s has no values" % word)
            else:
                for v, ve in vals.items():
                    _meaning("parameters.%s.%s" % (word, v), ve, p)
        elif entry.get("type") == "number":
            if entry.get("quantity") not in cat["quantities"]:
                p.append("parameters.%s names an unknown quantity" % word)
        else:
            p.append("parameters.%s has type %r; must be 'word' or 'number'"
                     % (word, entry.get("type")))

    for word, entry in cat["relations"].items():
        _meaning("relations.%s" % word, entry, p)
        if not str(entry.get("frame", "")).strip():
            p.append("relations.%s does not name its reference frame" % word)
        fixes = entry.get("fixes")
        if not isinstance(fixes, dict) or not set(fixes) <= set(FIX_KEYS) \
                or not set(fixes.values()) <= set(FIX_STRENGTHS):
            p.append("relations.%s: 'fixes' must map some of %s to one of %s"
                     % (word, FIX_KEYS, FIX_STRENGTHS))
        if entry.get("targets") not in (1, 2):
            p.append("relations.%s must take 1 or 2 targets" % word)
        for param, need in entry.get("params", {}).items():
            if param not in cat["parameters"]:
                p.append("relations.%s uses unknown parameter '%s'" % (word, param))
            if need not in PARAM_NEEDS:
                p.append("relations.%s.%s must be one of %s" % (word, param, PARAM_NEEDS))

    for word, entry in cat["properties"].items():
        _meaning("properties.%s" % word, entry, p)
        vals = entry.get("values")
        if not isinstance(vals, dict) or not vals:
            p.append("properties.%s has no values" % word)
            continue
        for v, ve in vals.items():
            _meaning("properties.%s.%s" % (word, v), ve, p)

    for word, entry in cat["objects"].items():
        where = "objects.%s" % word
        _meaning(where, entry, p)
        if word in cat["reserved_names"]:
            p.append("%s: an object kind cannot be a reserved name" % where)
        if entry.get("domain") not in cat["domains"]:
            p.append("%s names an unknown domain" % where)
        for q, need in entry.get("dimensions", {}).items():
            if q not in cat["quantities"]:
                p.append("%s uses unknown quantity '%s'" % (where, q))
            if need not in NEEDS:
                p.append("%s.%s must be one of %s" % (where, q, NEEDS))
        for group in entry.get("exactly_one_of", []):
            for q in group:
                if entry.get("dimensions", {}).get(q) != "optional":
                    p.append("%s: '%s' in exactly_one_of must be an optional dimension"
                             % (where, q))
        for prop, need in entry.get("properties", {}).items():
            if prop not in cat["properties"]:
                p.append("%s uses unknown property '%s'" % (where, prop))
            if need not in PARAM_NEEDS:
                p.append("%s.%s must be one of %s" % (where, prop, PARAM_NEEDS))
        for rel in entry.get("needs_relation", []):
            if rel not in cat["relations"]:
                p.append("%s needs unknown relation '%s'" % (where, rel))
        for host in entry.get("host", []):
            if host not in cat["objects"]:
                p.append("%s is hosted by unknown kind '%s'" % (where, host))
        if "placed_by" in entry and entry["placed_by"] not in PLACED_BY:
            p.append("%s: placed_by must be one of %s" % (where, PLACED_BY))
        if entry.get("placed_by") == "corner" and "corner" not in entry.get("properties", {}):
            p.append("%s is placed by its corner but has no property 'corner'" % where)
        if entry.get("host") and "on" not in entry.get("needs_relation", []):
            p.append("%s has a host but does not need the relation 'on'" % where)
        unknown = set(entry) - {"domain", "meaning", "dimensions", "properties",
                                "exactly_one_of", "needs_relation", "host", "takes_text",
                                "placed_by"}
        if unknown:
            p.append("%s has unknown keys %s" % (where, sorted(unknown)))
    return p


def words(cat):
    """Every vocabulary word, as (block, word) pairs -- one catalogue entry each."""
    out = []
    for block in ("domains", "acts", "units", "quantities", "relations",
                  "reserved_names", "objects"):
        out += [(block, w) for w in cat[block]]
    for name, entry in cat["parameters"].items():
        out.append(("parameters", name))
        out += [("parameters.%s" % name, v) for v in entry.get("values", {})]
    for name, entry in cat["properties"].items():
        out.append(("properties", name))
        out += [("properties.%s" % name, v) for v in entry["values"]]
    return out
