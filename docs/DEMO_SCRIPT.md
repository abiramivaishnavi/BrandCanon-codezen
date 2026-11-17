# Demo walkthrough (about 4 minutes)

All files are in `demo/`. The brand, AuroraBrew, is fictional.

**1. Brand Admin – the source of truth (40 s)**
Log in as Brand Admin → *Brand knowledge*.
- *Guideline rules*: each rule has an ID and version. Upload `06_social_media_guidelines_addendum.docx` and show three new rules appear.
- *Claims Ledger*: show F-03 (Diwali offer) is marked expired, F-04 (Winter offer) is 20%.
- *Terminology* and *Colours*: quick look.

**2. Creator – check a caption (60 s)**
Log in as Creator → *Check new content* → paste `01_instagram_caption.txt`, campaign "Winter Warmers 2026".
- Point at one **blocking** card: "Rs 499" → source F-01, approved value Rs 549, fix shown.
- Point at the "best" claim card and the brand-name card.
- With AI on: show an **Advisory · AI** card (health claim "boosts immunity") and the line "x rejected by validator".
- Click *Accept fix* on a few cards → *Apply accepted fixes* → version 2 is created and re-checked.
- Dismiss one minor finding with a reason (this feeds Insights).
- *Submit for review*.

**3. Creator – check a poster (40 s)**
Upload `02_winter_poster_offbrand.png` in the same campaign (type the text from `..._TEXT.txt` if AI is off).
- Show dominant colours and the two **visual** findings: blue and purple are not brand colours.
- Show 25% and Rs 499 are flagged from the poster text.

**4. Campaign Check (30 s)**
Open *Campaign Check* → the caption (now fixed) says 20% / Rs 549 but the poster says 25% / Rs 499. Mismatch shown with both sources.
Also upload `03_winter_brochure.pdf` to show a third format.

**5. Reviewer – human decision (40 s)**
Log in as Reviewer → open the caption.
- Try *Approve* while a blocking issue is open → the system asks for an override reason.
- *Request changes* with a comment instead. Log back in as Creator to show the comment and status.

**6. Admin – insights (30 s)**
Log in as Brand Admin → *Insights*: most frequent rules, gap signals (after a couple of dismissals of the same rule), audit log including any override.

**Clean example:** `05_clean_caption.txt` produces zero findings, showing the checker does not flag everything.
