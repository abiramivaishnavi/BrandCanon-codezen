"""LANE 2 - ADVISORY checks. Retrieval (RAG) + LLM, then a code validator that
throws away anything the model could not ground in the content and a retrieved rule."""
import re
from sqlalchemy.orm import Session

from . import llm
from .models import Rule
from .verified import sentences

ADVISORY_CATEGORIES = ("tone", "claim", "messaging", "accessibility", "visual")

SYSTEM = """You are a brand-compliance reviewer. You check CONTENT only against the RULES given to you.
Strict instructions:
- Use ONLY the rules provided. Do not use outside knowledge about the brand.
- Do NOT check prices, numbers, dates, or the spelling of brand/product names. Another system checks those.
- Report a finding only when the content clearly breaks a rule.
- "quote" must be copied EXACTLY, character for character, from the content (max 25 words).
- "rule_id" must be one of the rule IDs provided.
- "replacement" must be a minimal rewrite of the quote that fixes the problem and keeps the writer's meaning.
- "uncovered" lists issues that could harm the brand but that NO provided rule covers.
Return JSON only:
{"findings":[{"quote":"","rule_id":"","reason":"","severity":"major|minor","replacement":""}],
 "uncovered":[{"quote":"","issue":""}]}"""


def ensure_rule_embeddings(db: Session):
    """(Re)compute embeddings for rules that lack one or used a different method."""
    method = llm.embed_method()
    rules = db.query(Rule).filter(Rule.active == True).all()  # noqa: E712
    stale = [r for r in rules if not r.embedding or r.embedding.get("m") != method]
    if stale:
        used, vecs = llm.embed([r.text for r in stale])
        if used != method:  # API failed -> make every rule use the same local method
            stale = rules
            used, vecs = "local-bow", [llm._local_embed(r.text) for r in rules]
        for r, v in zip(stale, vecs):
            r.embedding = {"m": used, "v": v}
        db.commit()
    return rules


def retrieve_rules(db: Session, text: str, kind: str, per_chunk: int = 4, cap: int = 10):
    """Return the rules most relevant to this content, with similarity scores."""
    rules = [r for r in ensure_rule_embeddings(db) if r.category in ADVISORY_CATEGORIES]
    if kind != "image":
        rules = [r for r in rules if r.category != "visual"]
    if not rules or not text.strip():
        return []
    sents = [s.strip() for _, _, s in sentences(text) if s.strip()]
    chunks = [" ".join(sents[i:i + 3]) for i in range(0, len(sents), 3)] or [text]
    chunks = chunks[:12]
    method = rules[0].embedding["m"]
    if method == "local-bow":
        vecs = [llm._local_embed(c) for c in chunks]
    else:
        used, vecs = llm.embed(chunks)
        if used != method:
            return [(r, 0.0) for r in rules[:cap]]
    best: dict[int, float] = {}
    for v in vecs:
        scored = sorted(((llm.cosine(v, r.embedding["v"]), r) for r in rules), key=lambda x: -x[0])[:per_chunk]
        for score, r in scored:
            best[r.id] = max(best.get(r.id, 0), score)
    by_id = {r.id: r for r in rules}
    ranked = sorted(best.items(), key=lambda x: -x[1])[:cap]
    return [(by_id[i], round(s, 3)) for i, s in ranked]


def _locate(text: str, quote: str):
    """Find the quote in the content. Tolerates only whitespace differences."""
    quote = (quote or "").strip().strip('"“”')
    if len(quote) < 2:
        return None
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote)
    pattern = r"\s+".join(re.escape(w) for w in quote.split())
    m = re.search(pattern, text)
    return (m.start(), m.end()) if m else None


def run_advisory(db: Session, text: str, kind: str, image_path: str | None = None):
    """Returns (findings, uncovered_issues, stats)."""
    stats = {"ai_used": False, "rules_retrieved": 0, "ai_raw": 0, "ai_rejected": 0}
    if not llm.ai_enabled() or not text.strip():
        return [], [], stats
    retrieved = retrieve_rules(db, text, kind)
    stats["rules_retrieved"] = len(retrieved)
    if not retrieved:
        return [], [], stats
    rules_block = "\n".join(f"[{r.code}] ({r.category}) {r.text}" for r, _ in retrieved)
    user = f"RULES:\n{rules_block}\n\nCONTENT:\n\"\"\"\n{text[:6000]}\n\"\"\""
    data = llm.chat_json(SYSTEM, user)
    if data is None:
        return [], [], stats
    stats["ai_used"] = True
    allowed = {r.code: r for r, _ in retrieved}
    findings = []
    for item in data.get("findings") or []:
        stats["ai_raw"] += 1
        rule = allowed.get(str(item.get("rule_id", "")).strip("[] "))
        span = _locate(text, item.get("quote", ""))
        # ---- VALIDATOR: no real quote or no retrieved rule -> rejected ----
        if not rule or not span:
            stats["ai_rejected"] += 1
            continue
        quote = text[span[0]:span[1]]
        replacement = (item.get("replacement") or "").strip() or None
        if replacement == quote:
            replacement = None
        findings.append(dict(
            lane="advisory", category=rule.category,
            severity="minor" if item.get("severity") == "minor" else "major",
            quote=quote, start=span[0], end=span[1], rule_code=rule.code, rule_version=rule.version,
            rule_text=rule.text, reason=(item.get("reason") or "").strip(),
            suggestion=f"Suggested rewrite: \"{replacement}\"" if replacement else "Rephrase to follow the rule.",
            replacement=replacement))
    uncovered = []
    for item in (data.get("uncovered") or [])[:5]:
        if (item.get("issue") or "").strip():
            uncovered.append({"quote": (item.get("quote") or "")[:300], "issue": item["issue"].strip()[:400]})
    return findings, uncovered, stats
