"""Campaign Check: compares the facts used across every format in one campaign
(poster, caption, PDF ...) and reports values that disagree."""
import re
from sqlalchemy.orm import Session

from .models import Content, Version
from .verified import PRICE_RE, PERCENT_RE

MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
DATE_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", re.I)
DATE_NUM_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-]\d{2,4})?\b")


def extract_values(text: str):
    prices = {m.group(1).replace(",", "").split(".")[0] for m in PRICE_RE.finditer(text)}
    percents = {m.group(1).split(".")[0] for m in PERCENT_RE.finditer(text)}
    dates = {f"{int(m.group(1))} {m.group(2)[:3].title()}" for m in DATE_RE.finditer(text)}
    for m in DATE_NUM_RE.finditer(text):
        d, mo = int(m.group(1)), int(m.group(2))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            dates.add(f"{d} {MONTHS[mo - 1].title()}")
    return {"price": prices, "discount": percents, "date": dates}


LABELS = {"price": "Price", "discount": "Discount", "date": "Date"}


def campaign_check(db: Session, campaign_id: int):
    items = db.query(Content).filter(Content.campaign_id == campaign_id).all()
    rows = []
    for c in items:
        v = db.query(Version).filter(Version.content_id == c.id, Version.number == c.current_version).first()
        vals = extract_values(v.text if v else "")
        rows.append({"content_id": c.id, "title": c.title, "kind": c.kind, "status": c.status,
                     "values": {k: sorted(s) for k, s in vals.items()}, "_sets": vals})
    mismatches = []
    for key in ("price", "discount", "date"):
        having = [r for r in rows if r["_sets"][key]]
        clash = any(not (a["_sets"][key] & b["_sets"][key]) for i, a in enumerate(having) for b in having[i + 1:])
        if clash:
            mismatches.append({
                "type": key, "label": LABELS[key],
                "message": f"{LABELS[key]} values do not agree across this campaign.",
                "items": [{"content_id": r["content_id"], "title": r["title"], "kind": r["kind"],
                           "values": r["values"][key]} for r in having]})
    for r in rows:
        del r["_sets"]
    return {"items": rows, "mismatches": mismatches, "consistent": not mismatches and len(rows) > 1}
