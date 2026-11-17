# Code tour: understand the project in 30 minutes

Judges may ask any member to explain their part. Read your section, then run the app and follow one request through the code.

## The life of one upload
1. `frontend/src/pages/NewContent.jsx` sends the form to `POST /contents`.
2. `backend/app/main.py → create_content()` saves the file, calls `build_version()` to get text (and colours for images), creates a `Content` row and `Version` 1.
3. `engine.py → run_check()` calls `analyse()`:
   - `verified.py` runs the exact checks and returns finding dictionaries.
   - `advisory.py → run_advisory()` retrieves relevant rules, asks the LLM, validates the answer.
   - overlapping results are merged; findings are saved in the `findings` table.
4. `frontend/src/pages/ContentDetail.jsx` loads `GET /contents/{id}` and draws the highlighted text and Evidence Cards.
5. Accept/dismiss → `PATCH /findings/{id}`. *Apply accepted fixes* → `POST /contents/{id}/apply-fixes` makes a new version and re-checks.
6. *Submit* → `in_review`. Reviewer → `POST /contents/{id}/review` (approve needs no open blocking findings, or an override reason).

## Frontend owner
- `src/api.js`: one `api()` helper adds the token and handles errors.
- `src/App.jsx`: routes and the top navigation, different per role.
- `src/pages/ContentDetail.jsx`: the main screen. `HighlightedText` turns finding positions into coloured spans. `EvidenceCard` is one finding with its actions.
- `src/ui.jsx`: shared Button, Card, Pill.
- Be ready to explain: how highlights are built from `start`/`end`, how role decides which buttons appear (`canEdit`, `canReview`).

## Backend & workflow owner
- `app/models.py`: all tables. Note `Finding.rule_version` and `Version.number`.
- `app/auth.py`: PBKDF2 password hashing, JWT, `require("admin")` role guard.
- `app/main.py`: every endpoint. Look at `review()` for the blocking gate and override, and `log()` for the audit trail.
- Be ready to explain: status flow `draft → in_review → approved / changes_requested`, why creators cannot dismiss blocking findings, how versions are created.

## AI / RAG owner
- `app/llm.py`: OpenAI-compatible client, `embed()`, `chat_json()`, `read_image_text()` (vision OCR), local fallback embedding.
- `app/advisory.py`:
  - `ensure_rule_embeddings()` embeds rules once and stores vectors in the DB.
  - `retrieve_rules()` splits content into 3-sentence chunks, takes the top 4 rules per chunk by cosine similarity, keeps the best 10.
  - `SYSTEM` is the prompt. `run_advisory()` calls the LLM and then the **validator**: `_locate()` must find the quote in the content, and the rule ID must be in the retrieved set.
- `tests/test_engine.py → test_validator_rejects_ungrounded_ai_findings` proves the validator works with a fake AI answer.
- Be ready to explain: why retrieval instead of sending all rules, what happens when the model invents a quote, why AI findings are never "blocking".

## Documents & verified checks owner
- `app/extract.py`: PDF (PyMuPDF), DOCX (python-docx, counts images without alt text), image colours (Pillow quantiser), `split_rules()` for guideline documents.
- `app/verified.py`:
  - `check_facts()`: keyword near a number → compare with the Claims Ledger; expired facts; context carried from the previous sentence.
  - `check_terms()`, `check_claims()` (superlative list vs supported claims), `check_style()`, `check_accessibility()` (Flesch score, long sentences, alt text), `check_palette()` (Delta-E colour distance).
- `app/campaign.py`: extracts prices, discounts and dates from each item and flags sets that do not overlap.
- Be ready to explain: one regex (e.g. `PRICE_RE`), how a date is kept from being read as a count, what Delta-E 25 means.

## Data, testing & deployment owner
- `backend/seed_data/brand_guidelines.txt` and `app/seed.py`: the fictional brand.
- `scripts/make_demo_files.py`: regenerates everything in `demo/`.
- `eval/cases.json` + `eval/run_eval.py`: the reliability test set and score. Add cases; re-run; commit `results.md`.
- `app/insights.py`: counts per rule and the three gap-signal types.
- `render.yaml`, `frontend/vercel.json`, `.env.example`: deployment.
- Be ready to explain: how detection rate and false-flag rate are calculated, what the known misses are.
