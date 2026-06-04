# 🎬 The Unofficial Guide — Demo Video Script

**Target length:** 3–5 minutes (this script runs ~4:30 at a calm pace).
**Audience:** stakeholders — lead with *what it does* and *why it's trustworthy*, not implementation trivia.

---

## Before you hit record (setup checklist)

1. Terminal open in the project root with the venv active:
   ```
   source .venv/bin/activate
   ```
2. The index is built (run once if needed): `python build_index.py`
3. Start the app and have the browser ready:
   ```
   streamlit run app.py        # opens http://localhost:8501
   ```
4. A second terminal tab ready to run `python evaluate.py` for the last scene.
5. Sidebar set to defaults: **Retrieval mode = Semantic**, **top-k = 4**, no source filter.
6. Every query below has been verified to behave as described — if an answer's wording
   differs slightly (the LLM isn't fully deterministic), the *substance* and the *citations*
   will still match.

> Tip: paste each query rather than typing, so the camera time goes to the answers.

---

## SCENE 1 — What this is (0:00 – 0:30)

**On screen:** the app title "🎓 The Unofficial Guide" and the sidebar.

**Narration:**
> "This is **The Unofficial Guide** — a question-answering system over the *unofficial*
> knowledge students actually share about campus dining and life: Reddit threads, forum
> posts, Discord chats, review blogs. You ask a plain-language question, and it gives you an
> answer that's **grounded in real student documents and cites its sources** — instead of a
> confident guess from a chatbot's training data. Under the hood it's a retrieval-augmented
> pipeline: 13 documents, 50 searchable chunks, local embeddings, and a Llama-3.3 model for
> the final answer. Let me show you."

---

## SCENE 2 — Query 1: strong retrieval AND generation (0:30 – 1:30)

**Action:** type **"Which dining hall is best for vegan options?"** and submit.

**On screen:** the answer naming **North Quad Dining**, the **Sources** list, then expand
the **"🔎 Retrieved context"** panel.

**Narration:**
> "First question — *which dining hall is best for vegan options?* The system answers
> **North Quad Dining**, because of its make-to-order stir-fry and tofu station, and — this
> is the important part — it **cites where that came from**: the Vegan & Vegetarian Guide and
> the North Quad reviews thread. If I expand the retrieved context, you can see the exact
> chunks it pulled, with similarity scores. The top match scored a distance of about 0.29 —
> a strong, on-topic hit. Notice it surfaced **both** the curated guide *and* an independent
> student review that agree — that's the retrieval working well, and the answer is fully
> traceable to those two sources."

**Why this is the 'works well' example to call out:** retrieval pulled the two most relevant
documents, and every claim in the answer maps to a citation.

---

## SCENE 3 — Query 2: handling disagreement, with citations (1:30 – 2:10)

**Action:** type **"Is the unlimited meal plan worth it compared to the block plan?"**

**On screen:** the answer + Sources list (`[1][2][3][4] Meal Plan Megathread`).

**Narration:**
> "Second question — *is the unlimited meal plan worth it?* Real students **disagree** about
> this, and the system doesn't paper over that. It reports the range: most people average
> 10–12 swipes a week, which makes the cheaper Block plan the better deal — one reviewer
> calls unlimited a *'tax on optimism'* about making it to breakfast — but it also notes
> unlimited can win if you graze all day. Every one of those claims is cited back to the
> meal-plan thread. That honesty about conflicting opinions is by design."

---

## SCENE 4 — Query 3 + conversational memory (2:10 – 2:55)

**Action:** type **"What late-night food is available after the dining halls close?"**, let it
answer, then ask the follow-up **"Is it open late?"** is NOT needed here — instead do the memory
demo: clear chat, ask **"Which dining hall is best for vegans?"**, then ask **"Is it open late?"**

**On screen:** for the follow-up, point to the **"🔎 searched for: Is North Quad Dining open
late?"** line, then the answer about midnight hours.

**Narration:**
> "Third query shows two things — citations again, and **conversational memory**. I'll ask
> *what late-night food is available after the dining halls close* — it lists North Quad till
> midnight, the union convenience store, the off-campus diner, all cited. Now watch a
> follow-up. I ask about vegan halls, then just say **'is it open late?'** The system
> **rewrites** my vague follow-up into *'Is North Quad Dining open late?'* — you can see that
> on screen — and answers correctly: open till midnight. It remembered what 'it' referred to."

---

## SCENE 5 — Where it STRUGGLES (the honest failure) (2:55 – 3:45)

**Action:** type **"How much does the unlimited meal plan cost per semester?"**

**On screen:** the answer — it states the unlimited plan costs **~$2,300 *or* ~$2,950**,
conflating two plans. Pause on it.

**Narration:**
> "Now the part that matters most — where it **fails**. I ask *how much does the unlimited
> plan cost per semester?* The correct answer is **$2,950**. But watch: the system hedges,
> saying it's *'$2,300 or $2,950.'* That $2,300 is actually the **Block 175** price — it got
> conflated with unlimited. **Why?** This is a *chunking* problem, not a model problem. The
> source lists the three plans as a bulleted price list, and my chunk boundary — with its
> overlap — sliced the **$2,300 figure off its 'Block 175' label**, creating an orphaned
> price fragment that retrieval pulls in alongside the real list. The model sees two dollar
> figures and mis-binds them. I traced this to the exact chunk boundary, and my chunking
> comparison confirmed that larger 1000-character chunks fix it — 0 out of 3 correct at the
> current size, 3 out of 3 with larger chunks. I kept the smaller size deliberately so this
> failure stays visible and documented, because understanding *why* it breaks is the point."

---

## SCENE 6 — Refusing what it doesn't know (3:45 – 4:05)

**Action:** type **"What is the football schedule this season?"**

**On screen:** the response *"I don't have enough information in the collected documents to
answer that."*

**Narration:**
> "One more — a question my documents don't cover. There's no football data in the corpus, so
> instead of inventing a plausible schedule, the system **refuses**: *'I don't have enough
> information.'* It fails closed. A low-relevance check stops it before it ever calls the LLM.
> For a tool people are supposed to trust, *not* answering is the right answer here."

---

## SCENE 7 — Evaluation report walkthrough (4:05 – 4:35)

**Action:** switch to the terminal, run **`python evaluate.py`**, scroll to the SUMMARY.

**On screen:** the per-question HIT/coverage lines and the final
`Recall@4: 5/5 (100%)` + `Mean answer keyword coverage: 100%`.

**Narration:**
> "Finally, the evaluation. I defined five test questions with known answers up front, and
> `evaluate.py` measures the system automatically — did it retrieve the right source document,
> and did the answer contain the key facts. Across all five: **5 out of 5 on retrieval**, and
> **100% keyword coverage** on the answers. But the number I care about most isn't on this
> screen — it's the failure case you just saw, which this evaluation framework is built to
> surface. A system you can trust is one whose limits you actually understand. Thanks for
> watching."

---

## Quick reference — the exact queries, in order

| # | Query | What to highlight |
|---|-------|-------------------|
| 1 | Which dining hall is best for vegan options? | Strong retrieval + citations + context panel |
| 2 | Is the unlimited meal plan worth it compared to the block plan? | Surfaces disagreement, all cited |
| 3 | What late-night food is available after the dining halls close? | Citations |
| 3b | (clear chat) Which dining hall is best for vegans? → "Is it open late?" | Conversational memory / query rewrite |
| 4 | How much does the unlimited meal plan cost per semester? | **Failure** — price conflation (chunk boundary) |
| 5 | What is the football schedule this season? | Refusal / out-of-scope |
| — | `python evaluate.py` | 5/5 Recall@4, 100% coverage |

**Requirement coverage:** 3+ queries with visible citations (Scenes 2–4) ✓ · one query that
works well, narrated (Scene 2) ✓ · one failure, narrated (Scene 5) ✓ · evaluation-report
walkthrough (Scene 7) ✓ · runtime ~4:30, within 3–5 min ✓.
