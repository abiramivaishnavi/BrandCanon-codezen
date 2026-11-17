# Plan for the remaining build window (deadline: Thu 19 Nov, 10:00 AM)

## Today (Tue) – get it running and online
1. **Everyone:** run the project locally (README → "Run it locally"). Log in with the three demo accounts and follow `docs/DEMO_SCRIPT.md` once.
2. **Create the GitHub repo (public).** Each member commits their own area from their own account (see "Who commits what"). Commit small and often from now on.
3. **AI owner:** get a Gemini API key, put it in `backend/.env`, check `/ai/test`, then run the caption demo and confirm Advisory cards appear. Tune the prompt in `advisory.py` if results are weak.
4. **Deployment owner:** Neon/Supabase Postgres → Render (backend) → Vercel (frontend). Share the live link in the group.
5. **Everyone:** read your section of `docs/CODE_TOUR.md`.

## Wednesday – make it yours and test it
6. **Each member makes at least one real improvement in their area** (ideas below) so you can honestly describe your contribution.
7. **User testing:** 3–5 people use the live link with the task in `docs/USER_FEEDBACK.md`. Write down what really happened.
8. **Data/testing owner:** add 10+ new cases to `eval/cases.json`, run `python ../eval/run_eval.py` with the AI key set, commit `eval/results.md`.
9. **Feature freeze at 6 PM.** After that: bug fixes, README, video.
10. Record a 3–4 minute demo video following `docs/DEMO_SCRIPT.md`.

## Thursday before 10 AM
11. Fill every `[placeholder]` in README (team, links, contributions, AI disclosure).
12. Open the live link in an incognito window and run the demo once more.
13. Submit: repo link, live link, video, README.

## Who commits what
| Member | Folders / files |
|---|---|
| Frontend | `frontend/` |
| Backend & workflow | `backend/app/main.py`, `models.py`, `auth.py`, `db.py`, `config.py`, `render.yaml` |
| AI / RAG | `backend/app/llm.py`, `advisory.py`, `engine.py`, `backend/tests/` |
| Documents & verified checks | `backend/app/extract.py`, `verified.py`, `campaign.py` |
| Data, testing & deployment | `backend/app/seed.py`, `backend/seed_data/`, `insights.py`, `demo/`, `eval/`, `scripts/`, `docs/`, `README.md` |

## Small improvement ideas (pick one each)
- **Frontend:** word-level diff between two versions; mobile layout for the review screen; a "copy approved text" button.
- **Backend:** let reviewers reassign; filter the audit log by content; export an approval report as PDF.
- **AI/RAG:** show the retrieved rules and similarity scores on the review screen; add few-shot examples to the prompt; detect conflicting rules (the 4th gap signal).
- **Verified checks:** numbers written as words ("forty"); prices without "Rs" ("650 rupees"); tolerate double spaces in brand names. These are the known misses in `eval/results.md`, so fixing them raises the measured score.
- **Data/testing:** more test cases, including tricky clean ones; a second fictional brand to show the engine is not hard-coded.
