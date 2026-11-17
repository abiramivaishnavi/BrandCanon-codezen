"""Automated tests. Run from the backend folder:  python -m pytest -q
They use a temporary database and a fake AI, so no API key is needed."""
import os, tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["LLM_API_KEY"] = ""

from app.db import Base, engine, SessionLocal   # noqa: E402
from app.seed import seed                        # noqa: E402
from app import engine as eng, advisory, llm     # noqa: E402

Base.metadata.create_all(engine)
db = SessionLocal()
seed(db)


def codes(findings):
    return {(f["rule_code"], f["quote"]) for f in findings}


def test_price_mismatch_is_blocking_and_fixable():
    f, _, _ = eng.analyse(db, "Morning Ember is now Rs 499 for 250g.", "text")
    hit = next(x for x in f if x["rule_code"] == "F-01")
    assert hit["severity"] == "blocking" and hit["lane"] == "verified" and hit["replacement"] == "Rs 549"


def test_correct_price_is_not_flagged():
    f, _, _ = eng.analyse(db, "Morning Ember is Rs 549 and Velvet Night is Rs 599.", "text")
    assert not [x for x in f if x["category"] == "fact"]


def test_expired_offer_is_flagged_even_when_value_is_right():
    f, _, _ = eng.analyse(db, "Diwali festive sale: flat 40% off.", "text")
    hit = next(x for x in f if x["rule_code"] == "F-03")
    assert "expired" in hit["reason"]


def test_price_in_next_sentence_inherits_product():
    f, _, _ = eng.analyse(db, "Try our Morning Ember today. Only Rs 499!", "text")
    assert ("F-01", "Rs 499") in codes(f)


def test_dates_are_not_mistaken_for_counts():
    f, _, _ = eng.analyse(db, "20% off at every café until 31 Jan.", "text")
    assert not [x for x in f if x["rule_code"] == "F-05"]


def test_brand_name_variants():
    f, _, _ = eng.analyse(db, "Aurora Brew and aurorabrew are wrong, AuroraBrew is right.", "text")
    quotes = [x["quote"] for x in f if x["rule_code"] == "T-01"]
    assert sorted(quotes) == ["Aurora Brew", "aurorabrew"]


def test_supported_claim_is_allowed_unsupported_is_not():
    f, _, _ = eng.analyse(db, "Our award-winning roast is the best in India.", "text")
    claims = [x["quote"] for x in f if x["category"] == "claim"]
    assert claims == ["best"]


def test_clean_content_has_no_findings():
    text = open(os.path.join(os.path.dirname(__file__), "..", "..", "demo", "05_clean_caption.txt"), encoding="utf-8").read()
    f, _, _ = eng.analyse(db, text, "text")
    assert f == []


def test_palette_flags_off_brand_colour_only():
    from app.verified import check_palette
    from app.models import PaletteColor
    pal = db.query(PaletteColor).all()
    out = check_palette([{"hex": "#2B3A8C", "share": 0.6}, {"hex": "#E0723C", "share": 0.3}, {"hex": "#FFFFFF", "share": 0.1}], pal)
    assert [x["quote"] for x in out] == ["#2B3A8C"]


def test_validator_rejects_ungrounded_ai_findings(monkeypatch):
    """The AI returns 3 findings: one real, one with an invented quote, one citing
    a rule that was never retrieved. Only the real one may survive."""
    text = "Customers who drink it daily will find that it boosts immunity. Act now!"
    monkeypatch.setattr(llm, "ai_enabled", lambda: True)
    monkeypatch.setattr(llm, "embed_method", lambda: "local-bow")
    monkeypatch.setattr(llm, "embed", lambda texts: ("local-bow", [llm._local_embed(t) for t in texts]))
    retrieved = advisory.retrieve_rules(db, text, "text")
    real_rule = next(r.code for r, _ in retrieved if "health" in r.text)
    fake = {"findings": [
        {"quote": "boosts immunity", "rule_id": real_rule, "reason": "Health claim.", "severity": "major", "replacement": "tastes great"},
        {"quote": "cures cancer", "rule_id": real_rule, "reason": "Invented quote.", "severity": "major", "replacement": ""},
        {"quote": "Act now", "rule_id": "ZZ-99", "reason": "Invented rule.", "severity": "major", "replacement": ""},
    ], "uncovered": [{"quote": "", "issue": "No rule about response time promises."}]}
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: fake)
    findings, uncovered, stats = advisory.run_advisory(db, text, "text")
    assert [f["quote"] for f in findings] == ["boosts immunity"]
    assert findings[0]["lane"] == "advisory" and findings[0]["start"] == text.index("boosts immunity")
    assert stats["ai_raw"] == 3 and stats["ai_rejected"] == 2
    assert len(uncovered) == 1
