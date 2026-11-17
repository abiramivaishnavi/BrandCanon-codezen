"""The compliance engine: runs both lanes, merges the results and stores them."""
from sqlalchemy.orm import Session

from . import verified, advisory
from .models import Rule, Fact, Term, PaletteColor, Finding, Version, Content, UncoveredIssue


def _first_rule(rules, category, contains=None):
    for r in rules:
        if r.category == category and (contains is None or contains in r.text.lower()):
            return r
    return next((r for r in rules if r.category == category), None)


def _overlaps(a, b):
    if a["start"] is None or b["start"] is None:
        return False
    return a["start"] < b["end"] and b["start"] < a["end"]


def analyse(db: Session, text: str, kind: str, colors=None, meta=None, image_path=None, use_ai=True):
    """Pure analysis (no DB writes). Returns (findings, uncovered, stats)."""
    rules = db.query(Rule).filter(Rule.active == True).all()  # noqa: E712
    facts = db.query(Fact).all()
    terms = db.query(Term).all()
    palette = db.query(PaletteColor).all()

    v = []
    v += verified.check_facts(text, facts)
    v += verified.check_terms(text, terms)
    v += verified.check_claims(text, facts, _first_rule(rules, "claim", "superlative"))
    v += verified.check_style(text, next((r for r in rules if r.category == "tone" and "capital" in r.text.lower()), None))
    v += verified.check_accessibility(text, meta, kind, _first_rule(rules, "accessibility", "plain language"),
                                      _first_rule(rules, "accessibility", "alt text"))
    if kind == "image":
        v += verified.check_palette(colors, palette, _first_rule(rules, "visual", "colour"))

    a, uncovered, stats = advisory.run_advisory(db, text, kind, image_path) if use_ai else ([], [], {"ai_used": False})

    # merge: code-verified findings win; an overlapping AI finding only donates its rewrite
    merged = list(v)
    for af in a:
        clash = next((vf for vf in v if _overlaps(af, vf)), None)
        if clash:
            if clash["category"] == "claim" and not clash["replacement"] and af["replacement"] and \
                    af["start"] <= clash["start"] and af["end"] >= clash["end"]:
                clash.update(quote=af["quote"], start=af["start"], end=af["end"], replacement=af["replacement"],
                             suggestion=clash["suggestion"] + f" AI suggestion: \"{af['replacement']}\"")
            continue
        merged.append(af)
    merged.sort(key=lambda f: (f["start"] is None, f["start"] or 0))
    stats.update(verified=len(v), advisory=len([m for m in merged if m["lane"] == "advisory"]))
    return merged, uncovered, stats


def run_check(db: Session, content: Content, version: Version):
    findings, uncovered, stats = analyse(db, version.text or "", content.kind, version.colors,
                                         version.meta, version.file_path)
    # dismissed findings on the previous version stay dismissed (same rule + same text)
    prev = db.query(Finding).filter(Finding.content_id == content.id,
                                    Finding.version_number == version.number - 1,
                                    Finding.status.in_(["dismissed", "overridden"])).all()
    carried = {(p.rule_code, p.quote): p for p in prev}

    db.query(Finding).filter(Finding.content_id == content.id,
                             Finding.version_number == version.number).delete()
    for f in findings:
        row = Finding(content_id=content.id, version_number=version.number, **f)
        old = carried.get((f["rule_code"], f["quote"]))
        if old:
            row.status, row.resolution_note, row.resolved_by = old.status, old.resolution_note, old.resolved_by
        db.add(row)
    db.query(UncoveredIssue).filter(UncoveredIssue.content_id == content.id).delete()
    for u in uncovered:
        db.add(UncoveredIssue(content_id=content.id, **u))
    meta = dict(version.meta or {})
    meta["check"] = stats
    version.meta = meta
    db.commit()
    return stats
