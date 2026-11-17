"""LANE 1 - VERIFIED checks. Plain code, no AI: the same input always gives the
same result. Each function returns a list of finding dicts."""
import re
from datetime import date

SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])|\n+")
PRICE_RE = re.compile(r"(?<![A-Za-z])(?:₹|Rs\.?|INR)[ \t]?(\d+(?:,\d{2,3})*(?:\.\d+)?)", re.I)
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?(?:%|percent\b|per cent\b)", re.I)
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATE_RE = re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\b|\b{_MONTH}\s+\d{{1,2}}\b|\b\d{{1,2}}[/-]\d{{1,2}}(?:[/-]\d{{2,4}})?\b", re.I)
NUMBER_RE = re.compile(r"(?<![\w.])(\d+(?:,\d{2,3})*(?:\.\d+)?)(?![\w%])")

SUPERLATIVES = [
    r"best", r"finest", r"no\.?\s?1", r"number one", r"#1", r"world'?s? (?:best|finest|leading)",
    r"guaranteed?", r"100\s?%", r"cheapest", r"fastest", r"healthiest", r"unbeatable",
    r"award[- ]winning", r"most (?:loved|trusted|popular)", r"leading", r"perfect", r"risk[- ]free",
]
SUPERLATIVE_RE = re.compile(r"(?<!\w)(?:" + "|".join(SUPERLATIVES) + r")(?!\w)", re.I)


def sentences(text: str):
    """Yield (start, end, sentence) so findings can point at exact positions."""
    pos = 0
    for m in SENT_SPLIT.finditer(text):
        if text[pos:m.start()].strip():
            yield pos, m.start(), text[pos:m.start()]
        pos = m.end()
    if text[pos:].strip():
        yield pos, len(text), text[pos:]


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _fmt(v: float) -> str:
    return str(int(v)) if v == int(v) else str(v)


def _finding(**kw):
    base = dict(lane="verified", severity="major", quote="", start=None, end=None, rule_code="",
                rule_version=1, rule_text="", reason="", suggestion="", replacement=None)
    base.update(kw)
    return base


# ---------------- facts (Claims Ledger) ----------------
def _shown(f) -> str:
    return {"price": f"Rs {f.value}", "percent": f"{f.value}%"}.get(f.value_type, f.value)


def _keyword_hit(f, low: str):
    kws = [k.strip().lower() for k in f.keywords.split(",") if k.strip()]
    for k in kws:
        m = re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", low)
        if m:
            return m.start()
    return None


def _value_matches(f, sent: str):
    if f.value_type == "price":
        return list(PRICE_RE.finditer(sent))
    if f.value_type == "percent":
        return list(PERCENT_RE.finditer(sent))
    # plain numbers: ignore ones that belong to a price, a percentage or a date ("31 Jan")
    taken = [m.span() for m in PRICE_RE.finditer(sent)] + [m.span() for m in PERCENT_RE.finditer(sent)] + \
            [m.span() for m in DATE_RE.finditer(sent)]
    return [m for m in NUMBER_RE.finditer(sent) if not any(a <= m.start() < b for a, b in taken)]


def check_facts(text: str, facts, today: date | None = None):
    """Compare numbers in the content with the Claims Ledger.

    A fact applies to a sentence when one of its keywords appears there. If a
    sentence has a price/percentage but names no product ("only Rs 499!"), it
    inherits the facts mentioned in the sentence just before it."""
    today = today or date.today()
    facts = [f for f in facts if f.value_type != "claim"]
    out, prev_hits = [], {}
    for s_start, s_end, sent in sentences(text):
        low = sent.lower()
        hits = {f.id: pos for f in facts if (pos := _keyword_hit(f, low)) is not None}
        applicable = dict(hits)
        for f in facts:  # carry context from the previous sentence, per value type
            if f.id in prev_hits and f.value_type in ("price", "percent") and \
                    not any(g.value_type == f.value_type and g.id in hits for g in facts):
                applicable.setdefault(f.id, 0)
        prev_hits = hits
        for f in facts:
            if f.id not in applicable:
                continue
            kw_pos = applicable[f.id]
            matches = _value_matches(f, sent)
            if f.value_type == "number":   # a count/year must sit close to its keyword
                matches = [m for m in matches if abs(m.start() - kw_pos) <= 40]
            if not matches:
                continue
            approved = _num(f.value)
            values = [_num(m.group(1)) for m in matches]
            expired = bool(f.valid_until and f.valid_until < today)
            mismatch = approved not in values
            if not (expired or mismatch):
                continue
            # point at the number closest to the keyword
            m = min(matches, key=lambda mm: abs(mm.start() - kw_pos)) if mismatch else \
                next(mm for mm in matches if _num(mm.group(1)) == approved)
            quote = m.group(0)
            start = s_start + m.start()
            rule_text = f"{f.label}: approved value is {_shown(f)}" + \
                        (f" (valid until {f.valid_until.strftime('%d %b %Y')})" if f.valid_until else "")
            reasons, replacement = [], None
            if mismatch:
                reasons.append(f"The content says {quote.strip()} but the approved value is {_shown(f)}.")
                replacement = quote.replace(m.group(1), _fmt(approved))
            if expired:
                reasons.append(f"This fact expired on {f.valid_until.strftime('%d %b %Y')}, so it should no longer be published.")
            suggestion = (f"Change to {replacement}." if replacement else "") + \
                         (" Confirm with the brand team whether this is still running, or remove it." if expired else "")
            out.append(_finding(category="fact", severity="blocking", quote=quote, start=start,
                                end=start + len(quote), rule_code=f.code, rule_version=f.version,
                                rule_text=rule_text, reason=" ".join(reasons), suggestion=suggestion.strip(),
                                replacement=None if expired else replacement))
    return out


# ---------------- terminology ----------------
def check_terms(text: str, terms):
    out = []
    for t in terms:
        for variant in [v.strip() for v in t.variants.split(",") if v.strip()]:
            for m in re.finditer(r"(?<!\w)" + re.escape(variant) + r"(?!\w)", text, re.I):
                found = m.group(0)
                if t.preferred and found == t.preferred:
                    continue  # already the approved form
                if t.preferred:
                    repl = t.preferred
                    if found[:1].isupper() and repl[:1].islower():
                        repl = repl[:1].upper() + repl[1:]
                    rule_text = f"Use \"{t.preferred}\" instead of \"{variant}\"." + (f" {t.note}" if t.note else "")
                    reason = f"\"{found}\" is not the approved term."
                    suggestion = f"Replace with \"{repl}\"."
                else:
                    repl = None
                    rule_text = f"Do not use \"{variant}\"." + (f" {t.note}" if t.note else "")
                    reason = f"\"{found}\" is on the banned-terms list."
                    suggestion = "Remove this word or rephrase the sentence."
                out.append(_finding(category="term", severity=t.severity, quote=found, start=m.start(),
                                    end=m.end(), rule_code=t.code, rule_text=rule_text, reason=reason,
                                    suggestion=suggestion, replacement=repl))
    # the same span can match two variants (e.g. different casing) -> keep one
    seen, unique = set(), []
    for f in out:
        if (f["start"], f["end"]) not in seen:
            seen.add((f["start"], f["end"]))
            unique.append(f)
    return unique


# ---------------- unsupported claims ----------------
def check_claims(text: str, facts, claim_rule=None):
    supported = set()
    for f in facts:
        if f.value_type == "claim":
            supported.add(f.value.lower().replace("-", " "))
    out = []
    for m in SUPERLATIVE_RE.finditer(text):
        phrase = m.group(0)
        if phrase.lower().replace("-", " ") in supported:
            continue
        out.append(_finding(
            category="claim", severity="major", quote=phrase, start=m.start(), end=m.end(),
            rule_code=claim_rule.code if claim_rule else "CLAIM",
            rule_version=claim_rule.version if claim_rule else 1,
            rule_text=claim_rule.text if claim_rule else "Promotional claims must be supported by an approved fact.",
            reason=f"\"{phrase}\" is a superlative or absolute claim and the Claims Ledger has no approved fact that supports it.",
            suggestion="Remove the claim, soften it, or ask the brand admin to add supporting evidence to the Claims Ledger."))
    return out


# ---------------- accessibility ----------------
def _syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups)
    if word.endswith("e") and n > 1 and not word.endswith(("le", "ee")):
        n -= 1
    return max(n, 1)


def flesch_reading_ease(text: str) -> float | None:
    words = re.findall(r"[A-Za-z']+", text)
    sents = [s for _, _, s in sentences(text) if re.search(r"[A-Za-z]", s)]
    if len(words) < 40 or not sents:
        return None
    syl = sum(_syllables(w) for w in words)
    return round(206.835 - 1.015 * (len(words) / len(sents)) - 84.6 * (syl / len(words)), 1)


def check_accessibility(text: str, meta: dict | None, kind: str, acc_rule=None, alt_rule=None):
    out = []
    code = acc_rule.code if acc_rule else "ACCESS"
    rtext = acc_rule.text if acc_rule else "Content should be easy to read and usable by everyone."
    alt_code = alt_rule.code if alt_rule else code
    alt_text = alt_rule.text if alt_rule else "Every image must have alt text."
    score = flesch_reading_ease(text)
    if score is not None and score < 30:
        out.append(_finding(category="accessibility", severity="minor", rule_code=code, rule_text=rtext,
                            reason=f"Readability score is {score} (Flesch Reading Ease; below 30 is very hard to read).",
                            suggestion="Use shorter sentences and simpler words."))
    long_count = 0
    for s_start, s_end, sent in sentences(text):
        if len(sent.split()) > 40 and long_count < 3:
            long_count += 1
            q = sent.strip()
            st = text.find(q, s_start)
            out.append(_finding(category="accessibility", severity="minor", quote=q, start=st, end=st + len(q),
                                rule_code=code, rule_text=rtext,
                                reason=f"This sentence has {len(sent.split())} words, which is hard to follow.",
                                suggestion="Split it into two or three shorter sentences."))
    meta = meta or {}
    if meta.get("images_without_alt"):
        n = meta["images_without_alt"]
        out.append(_finding(category="accessibility", severity="major", rule_code=alt_code, rule_text=alt_text,
                            reason=f"{n} image(s) in this document have no alt text, so screen-reader users cannot understand them.",
                            suggestion="Add a short description (alt text) to every image."))
    if kind == "image" and not (meta.get("alt_text") or "").strip():
        out.append(_finding(category="accessibility", severity="minor", rule_code=alt_code, rule_text=alt_text,
                            reason="No alt text was provided for this image.",
                            suggestion="Add a one-line description to publish with the image."))
    return out


# ---------------- style: capitals and exclamation marks ----------------
def check_style(text: str, style_rule=None):
    """Simple, countable style rules. Only runs when a guideline about capitals /
    exclamation marks exists, and cites that guideline."""
    if not style_rule:
        return []
    out = []
    for s_start, s_end, sent in sentences(text):
        letters = [ch for ch in sent if ch.isalpha()]
        q = sent.strip().rstrip('!?. ')
        if len(q.split()) >= 3 and len(letters) >= 10 and all(ch.isupper() for ch in letters):
            st = text.find(q, s_start)
            fixed = q[:1] + q[1:].lower()
            out.append(_finding(category="tone", severity="minor", quote=q, start=st, end=st + len(q),
                                rule_code=style_rule.code, rule_version=style_rule.version, rule_text=style_rule.text,
                                reason="This whole sentence is written in capital letters.",
                                suggestion="Use normal sentence case.", replacement=fixed))
    for m in re.finditer(r"!{2,}", text):
        out.append(_finding(category="tone", severity="minor", quote=m.group(0), start=m.start(), end=m.end(),
                            rule_code=style_rule.code, rule_version=style_rule.version, rule_text=style_rule.text,
                            reason=f"{len(m.group(0))} exclamation marks in a row.",
                            suggestion="Use a single exclamation mark at most.", replacement="!"))
    return out


# ---------------- visual: colour palette ----------------
def _rgb(hex_: str):
    h = hex_.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lab(rgb):
    def lin(c):
        c /= 255
        return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
    r, g, b = (lin(c) for c in rgb)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def color_distance(hex_a: str, hex_b: str) -> float:
    """CIE76 Delta-E: roughly, under 10 looks 'the same colour', over 25 clearly different."""
    a, b = _lab(_rgb(hex_a)), _lab(_rgb(hex_b))
    return sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5


def _is_neutral(hex_: str) -> bool:
    r, g, b = _rgb(hex_)
    return max(r, g, b) - min(r, g, b) < 28  # white / grey / black are always allowed


def check_palette(colors, palette, visual_rule=None, threshold: float = 25.0, min_share: float = 0.06):
    if not colors or not palette:
        return []
    out = []
    approved = ", ".join(f"{p.name} {p.hex}" for p in palette)
    merged = []                       # the quantiser can return the same colour twice
    for c in colors:
        twin = next((m for m in merged if color_distance(m["hex"], c["hex"]) < 10), None)
        if twin:
            twin["share"] += c["share"]
        else:
            merged.append(dict(c))
    for c in merged:
        if c["share"] < min_share or _is_neutral(c["hex"]):
            continue
        nearest = min(palette, key=lambda p: color_distance(c["hex"], p.hex))
        dist = color_distance(c["hex"], nearest.hex)
        if dist > threshold:
            out.append(_finding(
                category="visual", severity="major", quote=c["hex"],
                rule_code=visual_rule.code if visual_rule else "PALETTE",
                rule_version=visual_rule.version if visual_rule else 1,
                rule_text=f"Approved brand colours: {approved}.",
                reason=f"{c['hex']} covers about {round(c['share'] * 100)}% of the image and is not close to any approved brand colour (nearest: {nearest.name} {nearest.hex}, colour distance {round(dist)}).",
                suggestion=f"Use {nearest.name} ({nearest.hex}) or another approved colour."))
    return out
