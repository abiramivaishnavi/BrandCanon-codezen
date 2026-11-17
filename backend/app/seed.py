"""Creates demo users and loads the fictional AuroraBrew brand kit on first start."""
import os
from datetime import date
from sqlalchemy.orm import Session

from .auth import hash_password
from .extract import split_rules
from .models import User, Rule, Fact, Term, PaletteColor, Campaign

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seed_data")

USERS = [
    ("Asha (Brand Admin)", "admin@aurorabrew.demo", "admin", "admin123"),
    ("Kiran (Creator)", "creator@aurorabrew.demo", "creator", "creator123"),
    ("Meera (Agency Creator)", "agency@aurorabrew.demo", "creator", "agency123"),
    ("Ravi (Reviewer)", "reviewer@aurorabrew.demo", "reviewer", "reviewer123"),
]

FACTS = [
    ("F-01", "Morning Ember 250g price (Rs)", "549", "price", "morning ember", None),
    ("F-02", "Velvet Night decaf 250g price (Rs)", "599", "price", "velvet night", None),
    ("F-03", "Diwali festive offer discount (%)", "40", "percent", "diwali, festive", date(2026, 10, 25)),
    ("F-04", "Winter Warmers offer discount (%)", "20", "percent", "winter", date(2027, 1, 31)),
    ("F-05", "Number of AuroraBrew cafés", "38", "number", "cafés, cafes, café, cafe, outlets, stores", None),
    ("F-06", "Year AuroraBrew was founded", "2016", "number", "founded, since, established", None),
    ("F-07", "Award: Indian Coffee Fest 2025, Best Small Roaster", "award-winning", "claim", "award", None),
]

TERMS = [
    ("T-01", "AuroraBrew", "Aurora Brew, Aurorabrew, Aurora-Brew", "The brand name is one word with a capital A and B.", "major"),
    ("T-02", "Morning Ember", "Morning Amber, Morning Embers", "Product name.", "major"),
    ("T-03", "café", "coffee shop, outlet", "We call our locations cafés.", "minor"),
    ("T-04", "affordable", "cheap", "\"Cheap\" suggests low quality.", "major"),
    ("T-05", "", "hurry, limited stock", "Pressure words are not part of our voice.", "major"),
]

PALETTE = [("Ember Orange", "#E2703A"), ("Roast Brown", "#4A2C2A"), ("Cream", "#F5EBDD"), ("Leaf Green", "#3F6B4E")]

PREFIX = {"tone": "TN", "claim": "CL", "messaging": "MS", "visual": "VS", "accessibility": "AC", "term": "TM"}


def next_rule_code(db: Session, category: str) -> str:
    prefix = PREFIX.get(category, "GN")
    existing = [r.code for r in db.query(Rule).filter(Rule.code.like(f"{prefix}-%")).all()]
    nums = [int(c.split("-")[1]) for c in existing if c.split("-")[1].isdigit()]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):02d}"


def add_rules_from_text(db: Session, text: str, source: str) -> int:
    count = 0
    existing = {r.text for r in db.query(Rule).all()}
    for item in split_rules(text):
        if item["text"] in existing:
            continue
        severity = "major" if item["category"] in ("claim", "visual") else "minor" if item["category"] == "accessibility" else "major"
        db.add(Rule(code=next_rule_code(db, item["category"]), category=item["category"], text=item["text"],
                    severity=severity, source=source))
        db.flush()
        count += 1
    db.commit()
    return count


def seed(db: Session):
    if db.query(User).count():
        return
    for name, email, role, pw in USERS:
        db.add(User(name=name, email=email, role=role, password_hash=hash_password(pw)))
    for code, label, value, vtype, kw, until in FACTS:
        db.add(Fact(code=code, label=label, value=value, value_type=vtype, keywords=kw, valid_until=until))
    for code, pref, variants, note, sev in TERMS:
        db.add(Term(code=code, preferred=pref, variants=variants, note=note, severity=sev))
    for name, hex_ in PALETTE:
        db.add(PaletteColor(name=name, hex=hex_))
    db.add(Campaign(name="Winter Warmers 2026"))
    db.commit()
    with open(os.path.join(SEED_DIR, "brand_guidelines.txt"), encoding="utf-8") as f:
        add_rules_from_text(db, f.read(), "brand_guidelines.txt")
