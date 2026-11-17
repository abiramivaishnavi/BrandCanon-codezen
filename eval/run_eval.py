"""Measured reliability: runs the engine on a labelled test set and reports
detection rate and false-flag rate.

    cd backend
    python ../eval/run_eval.py            # verified lane (no API key needed)
    LLM_API_KEY=... python ../eval/run_eval.py   # also scores the AI lane

Each case lists the issues a human expects: [rule_code, text that should be flagged].
- detected     = an expected issue the engine found (same rule, overlapping text)
- missed       = an expected issue the engine did not find
- false flag   = something the engine flagged that the human did not expect
"""
import json, os, sys, tempfile
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "eval.db")

from app.db import Base, engine, SessionLocal   # noqa: E402
from app.seed import seed                        # noqa: E402
from app import engine as eng, llm               # noqa: E402

Base.metadata.create_all(engine)
db = SessionLocal()
seed(db)

cases = json.load(open(os.path.join(HERE, "cases.json"), encoding="utf-8"))
ai = llm.ai_enabled()
stats = defaultdict(lambda: {"expected": 0, "detected": 0, "false": 0, "cases": 0})
rows = []

for case in cases:
    lane = "advisory" if case.get("needs_ai") else "verified"
    if lane == "advisory" and not ai:
        continue
    findings, _, _ = eng.analyse(db, case["text"], "text", use_ai=ai)
    expected = [tuple(e) for e in case["expected"]]
    matched, used = 0, set()
    for code, quote in expected:
        for i, f in enumerate(findings):
            if i not in used and f["rule_code"] == code and (quote in f["quote"] or f["quote"] in quote):
                used.add(i); matched += 1
                break
    false = [f for i, f in enumerate(findings) if i not in used]
    s = stats[lane]
    s["cases"] += 1; s["expected"] += len(expected); s["detected"] += matched; s["false"] += len(false)
    rows.append((case["id"], lane, len(expected), matched, len(false),
                 "; ".join(f'{f["rule_code"]}:"{f["quote"][:30]}"' for f in false)))

lines = [f"# BrandCanon reliability results", "",
         f"Run: {datetime.now().strftime('%d %b %Y %H:%M')} · AI lane: {'on (' + llm.LLM_MODEL + ')' if ai else 'off (no API key)'}", "",
         "| Lane | Cases | Expected issues | Detected | Detection rate | False flags | False flags per case |",
         "|---|---|---|---|---|---|---|"]
for lane, s in stats.items():
    rate = f"{100 * s['detected'] / s['expected']:.0f}%" if s["expected"] else "n/a"
    lines.append(f"| {lane} | {s['cases']} | {s['expected']} | {s['detected']} | {rate} | {s['false']} | {s['false'] / s['cases']:.2f} |")
lines += ["", "| Case | Lane | Expected | Detected | False flags | Details |", "|---|---|---|---|---|---|"]
lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows]
lines += ["", "Note: this is a small test set written by the team for a fictional brand. "
              "It shows how the engine behaves on known cases; it is not a claim about accuracy on real-world content."]
report = "\n".join(lines)
print(report)
open(os.path.join(HERE, "results.md"), "w", encoding="utf-8").write(report + "\n")
