# BrandCanon

**Every flag comes with a reason, a source and a fix.**

BrandCanon is a pre-publication brand-governance platform. It checks content (text, PDF, DOCX, images) against an organisation's own approved guidelines, facts, terminology and colours, explains every issue with evidence, suggests minimal fixes, and leaves the final decision to human reviewers.

Built for the Inkloom AI problem statement (We Code Coders hackathon), Round 2.

> Team: `[Team Name]` · Members: `[names]` · College: `[college]`
> Live demo: `[Vercel link]` · API: `[Render link]/docs` · Demo video: `[link]`

---

## What works today (Round 2 MVP)

| Area | Status |
|---|---|
| Login with roles (Brand Admin, Creator, Reviewer) | Working |
| Brand knowledge: guideline upload → versioned rules, Claims Ledger with validity dates, terminology, colour palette | Working |
| Content intake: pasted text, TXT, PDF, DOCX, PNG/JPG | Working |
| **Verified lane** (code): facts, expired offers, terminology, unsupported superlatives, capitals/exclamation style, readability, missing alt text, image colours vs palette | Working |
| **Advisory lane** (AI): RAG over the guideline rules + LLM, with a code validator that rejects ungrounded findings | Working when an API key is set |
| Evidence Cards: exact text, cited rule and version, reason, suggested fix | Working |
| Accept / edit / dismiss each finding, apply accepted fixes as a new version | Working |
| Review workflow: submit → approve / request changes, comments, version history, audit log | Working |
| Blocking gate: approval needs blocking issues fixed, or a written override that is logged | Working |
| Improvement 1 – Campaign Check (prices, discounts, dates across formats) | Early version |
| Improvement 2 – Guideline Clarity Insights (recurring issues, 3 of 4 gap-signal types) | Early version |
| Improvement 3 – Measured reliability (labelled test set + scoring script) | Baseline measured, see `eval/results.md` |

Nothing is ever published automatically. "Approved" means ready for a person to publish.

## How it works

```
React (Vite + Tailwind)  ──HTTPS + JWT──►  FastAPI
                                             ├─ auth.py        roles and tokens
                                             ├─ extract.py     PDF / DOCX / image → text, colours; guideline → rules
                                             ├─ verified.py    LANE 1: deterministic checks (no AI)
                                             ├─ advisory.py    LANE 2: retrieve rules → LLM → validator
                                             ├─ engine.py      runs both lanes, merges, stores findings
                                             ├─ campaign.py    cross-format consistency
                                             └─ insights.py    recurring issues and gap signals
                                           SQLite (local) or PostgreSQL (deployed) · LLM + embeddings API
```

**Two lanes.** Anything that can be checked exactly is checked by code and labelled *Verified*: a price either matches the Claims Ledger or it does not. Judgement calls (tone, messaging, implied claims) go to the LLM and are labelled *Advisory*.

**Keeping the AI honest.** The LLM only sees the rules retrieved for that content and must return JSON that quotes the content and cites a rule ID. A validator in code (`advisory.py`) drops any finding whose quote is not really in the content or whose rule was not in the retrieved set. The number of rejected findings is shown on the review screen.

**Main technical decisions**

- *One language for backend and AI (Python/FastAPI)* so extraction, checks and API live together.
- *Embeddings stored in the database as JSON and compared in Python.* With tens of rules this is fast and removes a separate vector database. pgvector is the planned upgrade when rule counts grow.
- *Any OpenAI-compatible LLM.* Provider, model and key are environment variables. With no key, the app still runs end to end on the Verified lane with a local bag-of-words retriever.
- *Findings store the rule version* they were checked against, so later guideline edits do not rewrite history.

## Run it locally

Requirements: Python 3.11+ and Node 18+.

```bash
# 1. Backend  (terminal 1)
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env   (then add your LLM_API_KEY)
python run_local.py           # API on http://localhost:8000, docs at /docs

# 2. Frontend  (terminal 2)
cd frontend
npm install
npm run dev                   # app on http://localhost:5173
```

The first start creates the database and loads a **fictional demo brand, AuroraBrew** (guidelines, facts, terms, colours) plus three users:

| Role | Email | Password |
|---|---|---|
| Brand Admin | admin@aurorabrew.demo | admin123 |
| Creator | creator@aurorabrew.demo | creator123 |
| Reviewer | reviewer@aurorabrew.demo | reviewer123 |

To reset everything, stop the backend and delete `backend/brandcanon.db`.

**Turning on the AI lane:** create a free key at Google AI Studio, put it in `backend/.env` as `LLM_API_KEY`, restart, log in, then open `http://localhost:8000/ai/test` through `/docs` to confirm the model names work. If the chat test fails, change `LLM_MODEL` to the current flash model shown in AI Studio.

## Try it

Sample files are in `demo/`. A guided walkthrough is in `docs/DEMO_SCRIPT.md`.

## Tests and measured reliability

```bash
cd backend
python -m pytest -q            # 10 automated tests, including the AI validator
python ../eval/run_eval.py     # scores the engine on eval/cases.json → eval/results.md
```

Round 2 baseline on our own 28-case test set (Verified lane): **18 of 23 seeded issues detected (78%), 1 false flag**. The misses are known gaps (numbers written as words, prices without a currency sign, double spaces in brand names) and the false flag is "best" used in a non-claim sense. These are our Round 3 targets. This is a small team-written set for a fictional brand, not a claim about real-world accuracy.

## Deploy

1. **Database (recommended):** create a free Postgres on Neon or Supabase and copy the connection string.
2. **Backend on Render:** New → Blueprint → pick this repo (uses `render.yaml`). Set `LLM_API_KEY` and `DATABASE_URL`. Without `DATABASE_URL` it uses SQLite, which is wiped on every restart.
3. **Frontend on Vercel:** import the repo, set *Root Directory* to `frontend`, add the environment variable `VITE_API_URL` = your Render URL (no trailing slash), deploy.
4. Optional: set `CORS_ORIGINS` on Render to your Vercel URL.

## APIs, models, libraries and services used

- **LLM + vision + embeddings:** Google Gemini API through its OpenAI-compatible endpoint (`openai` Python SDK). Models are set by `LLM_MODEL` / `EMBED_MODEL`.
- **Backend:** FastAPI, Uvicorn, SQLAlchemy, PyJWT, PyMuPDF, python-docx, Pillow, NumPy.
- **Frontend:** React, React Router, Vite, Tailwind CSS.
- **Hosting:** Vercel (frontend), Render (backend), Neon/Supabase Postgres.
- **Data:** all demo brand data and test content were written by the team for a fictional brand. No real company data is used.

## Responsible design

- Human control: no auto-publishing; every suggestion can be accepted, edited or dismissed; blocking overrides need an authorised role and a written reason.
- Transparency: AI findings are labelled "Advisory · AI"; the review screen shows whether AI was used and how many AI findings the validator rejected.
- Security: hashed passwords (PBKDF2), JWT sessions, role checks on every write, creators can only open their own content, uploaded files are served only to logged-in users, audit log of all actions.
- Privacy: content is sent to the configured external AI service only when a key is set. Organisations should use a provider whose API terms exclude training on submitted data.

## Known limitations

- One organisation per deployment (no multi-tenant separation yet).
- Fact matching relies on keywords near numbers; numbers written as words are missed.
- Image checks cover dominant colours and text read by the vision model; logo misuse and text contrast are not checked yet.
- On free hosting, uploaded files are lost when the server restarts.
- Gap signals for conflicting rules are not built yet (planned for Round 3).

## AI-assistance disclosure

As required by the event rules: AI tools (Claude) were used heavily during the build window to generate the code, tests and demo data in this repository. The team reviewed, ran, tested and deployed it, and each member is responsible for understanding and explaining their area. `[Edit this paragraph so it accurately describes what your team did.]`

## Team contributions

| Member | Area | Contribution |
|---|---|---|
| `[Name]` | Frontend | `[what you did]` |
| `[Name]` | Backend & workflow | `[what you did]` |
| `[Name]` | AI / RAG | `[what you did]` |
| `[Name]` | Documents & verified checks | `[what you did]` |
| `[Name]` | Data, testing & deployment | `[what you did]` |

## User feedback

See `docs/USER_FEEDBACK.md`.
