"""Governance insights: recurring mistakes and Guideline Gap signals."""
from collections import Counter, defaultdict
from sqlalchemy.orm import Session

from .models import Finding, Content, Rule, Fact, Term, UncoveredIssue


def build_insights(db: Session):
    contents = {c.id: c for c in db.query(Content).all()}
    findings = db.query(Finding).all()
    # the same issue repeats on every version of a document -> count it once
    unique = {}
    for f in findings:
        key = (f.content_id, f.rule_code, f.quote)
        if key not in unique or f.version_number > unique[key].version_number:
            unique[key] = f
    uniq = list(unique.values())

    rule_text = {r.code: r.text for r in db.query(Rule).all()}
    rule_text.update({f.code: f"{f.label}: {f.value}" for f in db.query(Fact).all()})
    rule_text.update({t.code: (f"Use \"{t.preferred}\"" if t.preferred else "Banned term") + f" (not: {t.variants})"
                      for t in db.query(Term).all()})

    per_rule = defaultdict(lambda: {"count": 0, "dismissed": 0, "contents": set(), "creators": set(), "lane": "", "category": ""})
    for f in uniq:
        if not f.rule_code:
            continue
        p = per_rule[f.rule_code]
        p["count"] += 1
        p["dismissed"] += f.status == "dismissed"
        p["contents"].add(f.content_id)
        if f.content_id in contents:
            p["creators"].add(contents[f.content_id].creator_id)
        p["lane"], p["category"] = f.lane, f.category

    top_rules = sorted(
        [{"rule_code": code, "rule_text": rule_text.get(code, ""), "count": p["count"], "dismissed": p["dismissed"],
          "contents": len(p["contents"]), "creators": len(p["creators"]), "lane": p["lane"], "category": p["category"]}
         for code, p in per_rule.items()], key=lambda x: -x["count"])

    gaps = []
    for r in top_rules:
        if r["dismissed"] >= 2 and r["dismissed"] / r["count"] >= 0.4:
            gaps.append({"type": "vague_or_strict", "title": f"{r['rule_code']} is often dismissed",
                         "rule_code": r["rule_code"], "rule_text": r["rule_text"],
                         "evidence": f"Dismissed {r['dismissed']} of {r['count']} times by creators or reviewers.",
                         "suggestion": "The rule may be too strict or too vague. Add examples of acceptable and unacceptable wording, or narrow when it applies."})
        if r["contents"] >= 3:
            gaps.append({"type": "unclear", "title": f"{r['rule_code']} is broken repeatedly",
                         "rule_code": r["rule_code"], "rule_text": r["rule_text"],
                         "evidence": f"Broken in {r['contents']} different pieces of content by {r['creators']} creator(s).",
                         "suggestion": "People may not know this rule. Make it more visible, reword it in plain language, or add it to creator onboarding."})
    for u in db.query(UncoveredIssue).order_by(UncoveredIssue.id.desc()).limit(10):
        c = contents.get(u.content_id)
        gaps.append({"type": "missing_rule", "title": "Issue with no matching rule",
                     "rule_code": "", "rule_text": "",
                     "evidence": f"In \"{c.title if c else 'content'}\": {u.issue}" + (f" (text: \"{u.quote}\")" if u.quote else ""),
                     "suggestion": "Consider adding a guideline that covers this situation."})

    return {
        "totals": {
            "contents": len(contents),
            "by_status": dict(Counter(c.status for c in contents.values())),
            "findings": len(uniq),
            "by_category": dict(Counter(f.category for f in uniq)),
            "by_lane": dict(Counter(f.lane for f in uniq)),
            "by_finding_status": dict(Counter(f.status for f in uniq)),
        },
        "top_rules": top_rules[:12],
        "gap_signals": gaps,
        "gap_types_planned": ["conflicting_rules (planned for Round 3)"],
    }
