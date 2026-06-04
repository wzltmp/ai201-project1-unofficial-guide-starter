# The Unofficial Guide — Project 1

**Repository:** https://github.com/wzltmp/ai201-project1-unofficial-guide-starter
(forked from the AI201 starter)
**Demo video script:** [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)

A Retrieval-Augmented Generation (RAG) system that answers plain-language questions
about **dining & campus life at Brightwood University** using a corpus of realistic
student-generated documents (reviews, forum threads, Discord chats). Ask *"Which
dining hall is best for vegan options?"* and get a grounded, **cited** answer drawn
only from what students actually wrote.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then paste a free Groq key from console.groq.com
python build_index.py         # ingest -> chunk -> embed -> store (run once)

streamlit run app.py          # the query interface
python evaluate.py            # run the 5-question evaluation framework
```

Retrieval (semantic search) works without an API key; only the grounded-answer
generation step calls Groq.

## Demo Video

A complete, timed narration script (≈4:30, stakeholder-facing) is in
[`DEMO_SCRIPT.md`](DEMO_SCRIPT.md). It walks through, in order:
1. Three queries with **source citations visible** (vegan halls, meal-plan worth-it, late-night food).
2. A query where retrieval **and** generation work well, with the relevance narrated.
3. **Conversational memory** — a vague follow-up ("is it open late?") resolved to the right hall.
4. The honest **failure case** narrated live (unlimited-plan price conflated across a chunk boundary).
5. An **out-of-scope refusal** ("football schedule" → "not enough information").
6. A walkthrough of the **evaluation report** (`python evaluate.py` → 5/5 Recall@4).

> The recorded `.mp4`/`.mov` goes here once filmed (e.g. `demo.mp4` in the repo root or a shared link).

## Pipeline at a glance

```
documents/ ──► ingest.py ──► chunk.py ──► embed_store.py ──► ChromaDB
 (13 .md)     (clean +       (700/100      (all-MiniLM        (cosine)
              metadata)      paragraph)     -L6-v2)              │
                                                                ▼
   answer ◄── generate.py ◄── retrieve.py (top-k semantic search) ◄┘
 (cited)      (Groq, grounded prompt)
```

Code map: `src/config.py` (all knobs) · `src/ingest.py` (M3) · `src/chunk.py` (M3) ·
`src/embed_store.py` (M4) · `src/retrieve.py` (M4) · `src/generate.py` (M5) ·
`app.py` (M5 UI) · `build_index.py` (orchestrator) · `evaluate.py` (eval framework).

---

## Domain

**Dining & campus life at Brightwood University** (a consistent fictional campus, so
every document references the same knowable set of dining halls, cafés, and study
spots — real scraped data would be inconsistent and far harder to evaluate against).

The system covers the lived-experience knowledge students trade to survive: which
dining hall is worth the walk, whether the unlimited meal plan pays off, where the
vegan/halal/gluten-free food actually is, where to study late, and what's open after
the halls close. This is valuable because official channels tell you a dining hall
*exists* and lists its hours — they don't tell you the noon rush at Hillside Commons
means a 20-minute line, or that "unlimited" is a bad deal if you skip breakfast. That
signal only lives in reviews, threads, and Discord chatter.

---

## Document Sources

13 simulated student-generated documents in `documents/`, each tagged with a
`source_type` so the mix of perspectives is explicit. All are labeled "(simulated)"
and are trivially swappable for real `.md`/`.txt` files.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | r/BrightwoodU (simulated) | forum_thread | `documents/01-hillside-commons-reviews.md` |
| 2 | r/BrightwoodU (simulated) | forum_thread | `documents/02-north-quad-dining-reviews.md` |
| 3 | r/BrightwoodU (simulated) | forum_thread | `documents/03-the-marketplace-reviews.md` |
| 4 | BrightwoodEats blog (simulated) | review | `documents/04-riverside-hall-reviews.md` |
| 5 | BrightwoodU forums (simulated) | forum_thread | `documents/05-meal-plan-megathread.md` |
| 6 | Brightwood Veg Society (simulated) | guide | `documents/06-vegan-vegetarian-guide.md` |
| 7 | r/BrightwoodU (simulated) | forum_thread | `documents/07-halal-kosher-glutenfree.md` |
| 8 | Brightwood Discord #food (simulated) | discord | `documents/08-late-night-food.md` |
| 9 | r/BrightwoodU (simulated) | forum_thread | `documents/09-coffee-on-campus.md` |
| 10 | BrightwoodU forums (simulated) | forum_thread | `documents/10-best-study-spots.md` |
| 11 | BrightwoodEats blog (simulated) | review | `documents/11-tewell-library.md` |
| 12 | Brightwood Discord #new-students (simulated) | discord | `documents/12-clubs-and-orgs.md` |
| 13 | Brightwood Off-Campus Guide (simulated) | guide | `documents/13-getting-around.md` |

**Ingestion / preprocessing (`src/ingest.py`).** Each document opens with a `---`
metadata header (`title`, `source_type`, `source`). Ingestion (1) parses that header
into attribution metadata carried through to citations; (2) strips markdown noise —
heading `#` markers, `*_`` emphasis/code markers — while keeping the words;
(3) normalizes list bullets and collapses runs of blank lines into clean paragraph
breaks; (4) drops empty files. Output is a structured record per document
(`doc_id, title, source, source_type, text`) ready for chunking.

The loader also accepts `.txt` and `.pdf` drop-ins: PDFs are text-extracted with
**pdfplumber** (`pip install pdfplumber`, lazy-imported only when a PDF is present).
pdfplumber does not OCR, so scanned image-only PDFs yield no text and are skipped —
digitally-created PDFs (housing guides, syllabi, handbooks) extract fine.

---

## Chunking Strategy

**Chunk size:** 700 characters (~150 tokens). **Overlap:** 100 characters.

**Why these choices fit the documents.** The corpus is review/forum-thread style —
many short, self-contained opinions, not a few long guides. Two constraints set the
size: (1) the embedding model `all-MiniLM-L6-v2` silently truncates input beyond
**256 tokens**, so chunks must stay comfortably under that — 700 chars ≈ 150 tokens
leaves margin; (2) a chunk should be large enough to hold one complete opinion so a
retrieved chunk is a standalone, citable thought. The 100-char overlap keeps a review
that straddles a boundary from being cut mid-sentence. Chunking is **paragraph-aware**
(`src/chunk.py`): it greedily packs whole paragraphs up to the size limit and only
hard-splits (on word boundaries) a paragraph that alone exceeds the limit — so it
never breaks words or merges two unrelated forum posts into one chunk.

**Final chunk count:** 50 chunks across 13 documents (min 178, max 733, avg 513
characters per chunk).

---

## Sample Chunks

Five real chunks from the index, each labeled with its source document (first chunk of
five different documents). Note each is one self-contained opinion or fact — the unit a
citation points back to.

**1 — source: `01-hillside-commons-reviews.md`** (Hillside Commons — honest reviews)
> Is Hillside Commons actually good or do people just go because it's central?
> u/quadratkid: Hillside is fine. The food is solidly average — the rotating entrées are
> hit or miss but the salad bar and the pasta station carry it. The real problem is the
> lunch rush. If you show up between 12:00 and 1:00 you are looking at a 15 to 20 minute
> line just to swipe in, and then every seat is taken. Go before 11:30 or after 1:00 and
> it's a completely different building. Honestly the wait is the #1 complaint everyone has.

**2 — source: `02-north-quad-dining-reviews.md`** (North Quad Dining — stir-fry station)
> North Quad appreciation thread (the stir-fry station is elite)
> u/greenhousegremlin: North Quad is the best dining hall for anyone who doesn't eat meat,
> full stop. The stir-fry / wok station lets you build a tofu and veggie bowl to order and
> it's the single most reliable hot vegan meal on campus… The tofu is actually pressed and
> crispy, not the rubbery cubes you get elsewhere.

**3 — source: `03-the-marketplace-reviews.md`** (The Marketplace — prices and meal swipes)
> u/budgetbrain: The Marketplace is the food-court-style spot — it's not all-you-can-eat
> like the halls, it's individual stations… where you pay per item with dining dollars or a
> meal swipe. One meal swipe = one combo, which is a good deal at the grill but a waste at
> the grab-and-go fridge where a sandwich is cheaper in dining dollars. Do the math.

**4 — source: `04-riverside-hall-reviews.md`** (Riverside Hall — the small quiet hall)
> Riverside Hall review: small, quiet, and the best breakfast on campus. Riverside is the
> smallest of the four dining halls and it's tucked over by the river dorms, so unless you
> live on that side you probably never go. That's a shame, because Riverside does a few
> things better than anywhere else.

**5 — source: `05-meal-plan-megathread.md`** (Meal Plan Megathread)
> u/budgetbrain (OP): Every year people overpay for the unlimited plan out of fear. Here's
> the actual math. Brightwood has three plans: Unlimited: ~$2,950/semester. Block 175: 175
> swipes (about 12/week), ~$2,300/semester. Commuter 80: 80 swipes, ~$1,150, for people who
> aren't on campus every day.

---

## Retrieval Test Results

Queries run through semantic retrieval (`python -m src.retrieve` / the app), top-k=4.
ChromaDB uses **cosine distance** (lower = more similar); `retrieve()` also reports a
`similarity = 1 − distance`. As a rule of thumb, distance < 0.5 is a strong match and
> 0.6–0.7 is weak/off-topic. **Every top result below is < 0.35.**

**Query 1: "Which dining hall is best for vegan options?"**

| Distance | Similarity | Source document (chunk) |
|---|---|---|
| **0.292** | 0.708 | `06-vegan-vegetarian-guide.md` (#0) |
| 0.353 | 0.647 | `06-vegan-vegetarian-guide.md` (#1) |
| 0.358 | 0.642 | `06-vegan-vegetarian-guide.md` (#2) |
| 0.367 | 0.633 | `02-north-quad-dining-reviews.md` (#0) |

*Why these are relevant:* the top three chunks are from the dedicated vegan/vegetarian
guide — the single most on-topic document, whose chunk #0 literally opens "North Quad Dining
is the best dining hall for vegans and vegetarians, no contest" — and the fourth is the North
Quad reviews thread that independently praises the stir-fry/tofu station. Retrieval surfaces
both the curated recommendation **and** the corroborating student review, the exact spread a
good answer should cite. Note semantic search ranked the *guide* above the *reviews* even
though the question says "dining hall" (more frequent in the reviews) — it matched on
meaning, not keywords.

**Query 2: "Where is the best quiet place to study late at night?"**

| Distance | Similarity | Source document (chunk) |
|---|---|---|
| **0.222** | 0.778 | `10-best-study-spots.md` (#1) |
| 0.403 | 0.597 | `11-tewell-library.md` (#0) |
| 0.455 | 0.545 | `10-best-study-spots.md` (#2) |
| 0.469 | 0.531 | `11-tewell-library.md` (#1) |

*Why these are relevant:* the top hit (distance 0.222 — the strongest match in the whole
eval set) is the study-spots chunk that names the Tewell 3rd/4th "quiet floors" and the
24-hr Engineering lounge, backed by two chunks from the Tewell floor-by-floor guide. This is
semantic matching at work — the query word "quiet" maps onto chunks about "silence enforced"
floors even where the exact word differs, and all four results come from the two study-focused
documents, none off-topic.

**Query 3: "What do students say about wait times at Hillside Commons during lunch?"**

| Distance | Similarity | Source document (chunk) |
|---|---|---|
| **0.254** | 0.746 | `01-hillside-commons-reviews.md` (#1) |
| 0.345 | 0.655 | `01-hillside-commons-reviews.md` (#0) |
| 0.496 | 0.504 | `09-coffee-on-campus.md` (#1) |
| 0.503 | 0.497 | `01-hillside-commons-reviews.md` (#3) |

Three of the top four are the Hillside Commons reviews thread (the correct source), led by
the chunk describing the "15 to 20 minute line" during the 12–1 lunch rush. The one outlier —
a coffee-doc chunk at distance 0.496 — is about café *lines/wait times* (semantically near
"wait times") but the right document still dominates, and the grounded answer cites only the
Hillside chunks.

*(All five eval queries were tested; the remaining two — meal plans and late-night food —
likewise return their correct source at top-result distances of 0.341 and 0.259.)*

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` — 384-dimensional,
runs locally (no API cost or latency), fast, and strong on short semantic-similarity
text, which is exactly this corpus. Vectors are stored in a persistent **ChromaDB**
collection using **cosine** distance; at query time distance is converted to a
`similarity = 1 − distance` score used for ranking, display, and the relevance cutoff.

**Production tradeoff reflection.** If cost weren't a constraint and this served real
users, I'd weigh a larger hosted embedding model (OpenAI `text-embedding-3-large`,
Voyage, or Cohere):

- **Context length** — MiniLM's 256-token cap forces small chunks; an 8k-token model
  could embed a whole review thread as one unit and preserve more surrounding context.
- **Domain accuracy** — campus slang and place nicknames are effectively
  out-of-vocabulary for a general small model; a larger or lightly fine-tuned model
  would match nicknames to their referents more reliably.
- **Multilingual** — an international student body posts in mixed languages; MiniLM is
  English-centric, so a multilingual model would improve recall.
- **Against all that: latency & cost** — local MiniLM is ~instant and free; a hosted
  model adds a network round-trip per query plus per-document indexing cost.

For a class project the local model clearly wins. For production I'd A/B a hosted model
and measure whether the recall gain justifies the added latency and cost.

---

## Grounded Generation

**System prompt grounding instruction (`src/generate.py`).** The model is told to
answer using **only** the numbered context and never its own prior knowledge; to cite
every claim inline with bracketed `[n]` numbers that map to the context items; to
report the *range* of opinions when student documents disagree (rather than inventing a
consensus); and — critically — to reply with the exact sentence *"I don't have enough
information in the collected documents to answer that."* whenever the context doesn't
cover the question. Temperature is set low (0.2) for faithful, non-creative answers.

**Structural grounding.** Two structural choices back up the prompt: (1) context is
formatted as a **numbered list, each item prefixed with its source title**, giving the
model explicit, citable units; (2) a **low-relevance guard** — if the top retrieved
chunk's cosine similarity is below `MIN_RELEVANCE_SCORE` (0.25), the system returns the
not-enough-info answer *without ever calling the LLM*, so out-of-corpus questions
("what's the football schedule?") fail closed instead of hallucinating.

**How source attribution is surfaced.** Attribution is **programmatically guaranteed**, not
left to the LLM: `_format_sources()` builds the **Sources** list directly from the retrieved
chunks (title, source type, original source, similarity score), so a response always names
its documents even if the model forgets to cite. The numbered context items map to sources
by `_format_sources` grouping chunks per document and keeping the **full list of citation
numbers** for each — so *every* inline `[n]` the model emits resolves to a listed source,
even when one document supplied several cited chunks (e.g. `[1][2][3] Meal Plan Megathread`).
The UI's "Retrieved context" panel additionally shows each underlying chunk with its score,
so a reader can trace any claim back to the exact student post it came from.

---

## Example Responses

Real, unedited system output (`python -m src.generate "<question>"` / the app). Note the
inline `[n]` citations and the Sources list on every grounded answer.

**Example 1 — "Is the unlimited meal plan worth it compared to the block plan?"**
> Some students say the unlimited meal plan is not worth it, as they averaged around 10-12
> swipes per week, which is the Block 175 sweet spot, saving around $650 [2, 4]. Others
> argue that the unlimited plan can be valuable if you have a high visit frequency, not
> just meal count, such as swiping in for coffee and snacks between classes [3]. However,
> some students consider the unlimited plan a "tax on optimism" about their morning routine,
> as they often don't make it to breakfast [4]. Ultimately, it depends on individual eating
> habits, with commuters recommending the Commuter 80 plan [2].
>
> **Sources:** [1][2][3][4] Meal Plan Megathread — unlimited vs. block vs. commuter (forum_thread)

Note how it surfaces the *disagreement* between students rather than flattening it — the
grounding prompt explicitly asks for the range of opinions. All four cited chunks come from
the one meal-plan thread, so every inline number maps to that source.

**Example 2 — "What late-night food is available after the dining halls close?"**
> After the dining halls close, there are several late-night food options available. On
> campus, North Quad Dining is open till midnight on weeknights for hot food [1]. The
> Marketplace grab-and-go fridge and convenience corner stay open late… [1][4]. The
> convenience store in the student union is open 24/7-ish, until around 1am… [2]. Off
> campus, options include Moonlight Diner, a 24-hour diner [2][3], Slice Night Pizza…
> open till 3am on weekends [2], and food trucks on College Ave… till ~1am on weekends [2][3].
>
> **Sources:** [1][2][3] Where to get food after the dining halls close (discord) · [4] The
> Marketplace — food court reviews (forum_thread)

**Out-of-scope query (refusal) — "What is the football schedule this season?"**
> I don't have enough information in the collected documents to answer that.

There is no football document in the corpus, so the low-relevance guard short-circuits
before the LLM is ever called — the system refuses instead of hallucinating a schedule.

---

## Query Interface

A **Streamlit chat app** (`streamlit run app.py`).

**Input fields:**
- *Chat box* (`st.chat_input`) — the natural-language question; supports multi-turn
  follow-ups (conversational memory).
- *Sidebar — Top-k slider* (1–8) — how many chunks to retrieve.
- *Sidebar — Retrieval mode* — Semantic or Hybrid (semantic + BM25).
- *Sidebar — Filter by source type* — restrict to forum_thread / review / guide / discord.
- *Sidebar — Clear chat* — reset the conversation.

**Output fields (per answer):**
- The grounded answer with inline `[n]` citations.
- A **Sources** list (citation number, title, source type, similarity score).
- A collapsible **Retrieved context** panel showing every retrieved chunk with its score,
  so retrieval quality is inspectable.
- For follow-ups, a "🔎 searched for: …" line showing the rewritten standalone query.

**Sample interaction transcript:**
```
User:      Which dining hall is best for vegan options?
Assistant: North Quad Dining is the best for vegans — its make-to-order stir-fry/wok
           station with pressed tofu is the most reliable hot vegan meal on campus [1][2].
           The vegan guide ranks it first and notes clearly labeled allergens [1].
           Sources:
             [1] Vegan & Vegetarian Dining Guide (guide, similarity 0.71)
             [2] North Quad Dining — reviews and the stir-fry station (forum_thread, sim 0.63)
           ▸ Retrieved context (4 chunks)   ← expandable
```

---

## Evaluation Report

Run with `python evaluate.py`. The framework measures two things automatically:
**Retrieval Recall@4** (did the expected source document appear in the top-4 retrieved
chunks?) and **answer keyword coverage** (what fraction of the ground-truth keywords
appear in the generated answer). Headline result across the 5 test questions:
**Recall@4 = 5/5 (100%)** and **mean keyword coverage = 100%**.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Wait times at Hillside Commons during lunch? | ~15–20 min lines during the noon rush; go before 11:30 or after 1:00 | Reported the 15–20 min lunch-rush line, the 12–1 peak, the before-11:30/after-1:00 advice, and the side-entrance swipe-station tip; cited [1][2][4] | Relevant (3 of top-4 from expected doc) | Accurate |
| 2 | Which dining hall is best for vegan options? | North Quad — stir-fry/tofu station, most reliable hot vegan meal | "North Quad Dining is the best… make-to-order stir-fry/wok station with pressed tofu… most reliable hot vegan meal"; cited [1][2][4] | Relevant (vegan guide + North Quad reviews) | Accurate |
| 3 | Unlimited vs. block meal plan — worth it? | Unlimited only if you eat 2–3 hall meals/day or graze constantly; otherwise Block 175 is cheaper | Captured both sides: ~10–12 swipes/week = Block 175 sweet spot saving ~$650, "tax on optimism," plus the grazing-frequency counterpoint and the commuter recommendation; cited [2][3][4] | Relevant (4 of top-4 from expected doc) | Accurate |
| 4 | Best quiet place to study late at night? | Tewell Library 3rd–4th (quiet) floors; 24-hr Engineering lounge as fallback | "Tewell Library, 3rd and 4th floors… silence enforced… 4th floor quietest on campus" + the 24-hr Engineering lounge; cited [1][4] | Relevant (best-spots + library docs) | Accurate |
| 5 | Late-night food after the dining halls close? | North Quad till midnight; Marketplace grab-and-go; union convenience store; off-campus Moonlight Diner / Slice Pizza | Listed North Quad till midnight, Marketplace fridge, the ~1am convenience store, and off-campus Moonlight Diner / Slice / food trucks; cited [1][2][3][4] | Relevant (3 of top-4 from expected doc) | Accurate |

**Aggregate — Retrieval quality:** Relevant (5/5).  
**Aggregate — Response accuracy:** Accurate (5/5), all answers grounded with inline citations.

The 5 designed questions all passed, so to stress-test honestly I ran additional probe
questions (`quietest dining hall`, `unlimited plan cost`, `kosher kitchen location`,
plus the off-topic `football schedule` / `housing lottery`). The off-topic ones correctly
hit the low-relevance guard and returned "not enough information." One probe exposed a
real failure, analyzed below.

---

## Failure Case Analysis

**Question that failed:** "How much does the unlimited meal plan cost per semester?"
(ground truth: **~$2,950**; Block 175 is the cheaper ~$2,300 plan).

**What the system returned:** *"The unlimited meal plan costs ~$2,300/semester [1] or
~$2,950/semester [2]…"* — it presented the **Block 175 price ($2,300) as if it could be
the unlimited price**, conflating two different plans.

**Root cause (chunking + retrieval stages).** The source document lists the three plans
as a labeled bullet list, fully intact in **chunk 0** (`Unlimited … ~$2,950`, `Block 175
… ~$2,300`, `Commuter 80 … ~$1,150`). But the 100-character **overlap tail** that seeds
**chunk 1** begins *mid-list* — `"ek), ~$2,300/semester. - Commuter 80…"` — so chunk 1
contains the **$2,300 figure detached from its "Block 175" label** (the label was sliced
off by the fixed-length overlap). For this query, retrieval returns chunks 0 and 1 as the
top two results (scores 0.756 and 0.709). The model now sees two price numbers, one of
them an orphaned `$2,300` with no plan name attached, and binds it to "unlimited."
Ironically, the **overlap mechanism — intended to prevent information loss at boundaries —
is what severed the price from its label** by cutting at a fixed character count instead
of a semantic boundary.

**What I would change to fix it.** Make chunking *structure-aware* so a labeled list (or
a `label: value` line) is never split across a boundary, and start the overlap window at
the nearest line/sentence boundary rather than a fixed character offset, so a price always
travels with its plan name. A cheaper mitigation is prepending the document title/section
to each chunk so the model has more binding context. The **Chunking Strategy Comparison**
stretch feature below empirically confirms this: switching to 1000/150 chunks fixes the
case (0/3 → 3/3 correct end-to-end), because the larger chunk keeps the labeled price list
whole instead of leaking an orphaned figure into a separate retrievable chunk.

---

## Spec Reflection

**One way the spec helped during implementation.** Writing `planning.md` first — the
chunking math in particular — forced the 256-token MiniLM cap into the open *before*
any code existed. Because I'd already reasoned that 700 chars ≈ 150 tokens stays under
that cap, `config.py` and `chunk.py` were written once with the right numbers instead
of being debugged after discovering silent truncation. The architecture diagram also
made the module boundaries (ingest → chunk → embed → retrieve → generate) obvious, so
each file had a single clear responsibility.

**One way the implementation diverged from the spec.** The spec didn't originally
include a relevance threshold; I added the `MIN_RELEVANCE_SCORE` low-relevance guard in
`generate.py` during implementation. Once I saw that semantic search *always* returns
top-k chunks — even for a question with no home document — it was clear the grounding
prompt alone could still be undermined by confidently-wrong nearby chunks. Failing
closed before the LLM call was a more robust mechanism than relying on instructions, so
I updated the Anticipated Challenges section to record it.

---

## AI Usage

**Instance 1 — chunking implementation**
- *What I gave the AI:* the Chunking Strategy section of `planning.md` (700-char size,
  100-char overlap, paragraph-aware, the MiniLM 256-token rationale) and the document
  header format.
- *What it produced:* `load_documents()` with `---` header parsing + markdown cleaning,
  and a paragraph-aware `chunk_text()` that packs paragraphs and only hard-splits
  oversized ones.
- *What I changed or overrode:* directed it to keep paragraphs intact rather than do a
  blind fixed-character split, and to seed each new chunk with the previous chunk's
  overlap tail so a thought spanning a boundary isn't cut in half.

**Instance 2 — grounded generation prompt**
- *What I gave the AI:* the Grounded Generation design (numbered + source-titled
  context, the strict "only use the context / cite [n] / say not-enough-info" rules,
  the low-relevance cutoff).
- *What it produced:* the `SYSTEM_PROMPT`, `build_context()` numbering, and the
  `answer_question()` retrieve→guard→generate flow.
- *What I changed or overrode:* added the explicit instruction to *report disagreement
  across student opinions and cite each side* (the corpus deliberately contains
  conflicting reviews), and lowered temperature to 0.2 for faithfulness.

---

## Stretch Features

Beyond the required pipeline. Each was planned in `planning.md` before implementation.

### 1. Hybrid Search (semantic + BM25)

Dense embedding search captures meaning but can under-rank exact-term matches (proper
nouns, plan names, prices). `src/hybrid.py` adds a BM25 keyword index (`rank-bm25`) over
the same chunks and fuses the two rankings with **Reciprocal Rank Fusion** (RRF,
`score = Σ 1/(60 + rank)`), which combines by rank and so needs no normalization between
the cosine and BM25 score scales. The Streamlit app has a **Semantic / Hybrid** toggle,
and `answer_question()` accepts a pluggable `retriever`. (The off-topic guard always
judges relevance on a semantic cosine score, since RRF scores aren't on that scale.)

**Comparison vs. semantic-only** (`python compare_retrieval.py`, over the 5 eval
questions + the failure-case probe):

| Metric | Semantic-only | Hybrid |
|---|---|---|
| Recall@4 (expected doc retrieved) | 6/6 | 6/6 |
| Avg rank of expected doc (lower is better) | 1.50 | **1.33** |
| Per-question winner | — | ties 5/6, **wins Q2** (vegan: rank 4 → 3) |

**Honest finding.** On this small, clean corpus hybrid helps modestly: it lifts the
ambiguous vegan question (where the dedicated North Quad *reviews* doc was out-ranked by
the vegan *guide*) from rank 4 to rank 3, and never regresses. Notably, hybrid does **not**
fix the meal-plan price failure case — I verified that both retrievers surface the same
chunks there (including the chunk with the orphaned `$2,300`), so both answers conflate
the prices across repeated runs. That's the right result to report: the failure is a
*chunking-boundary* problem, not a ranking problem, so a better retriever can't solve it —
which motivates the chunking comparison below.

### 2. Chunking Strategy Comparison

`compare_chunking.py` holds everything fixed (same docs, embedding model, query set)
and varies only the chunker, building each strategy into an isolated **in-memory**
ChromaDB collection. It reports Recall@4 and average expected-doc rank over the 5 eval
questions, plus an **end-to-end** test of the documented failure case: it generates the
unlimited-cost answer 3× per strategy and counts how often it gives `$2,950` without
conflating the `$2,300` Block-175 price.

| Strategy | #chunks | Recall@4 | Avg rank | Failure-case answer correct |
|---|---|---|---|---|
| paragraph **700/100** (baseline, production) | 50 | 5/5 | 1.60 | **0/3** |
| paragraph 400/80 (smaller) | 85 | 5/5 | 1.40 | 3/3 |
| paragraph **1000/150** (larger) | 32 | 5/5 | **1.40** | **3/3** |
| naive fixed 700/100 | 41 | 5/5 | 1.60 | 3/3 |

**What this shows.** Document-level retrieval (Recall@4) is saturated at 5/5 for every
strategy — the corpus is small and topically separated, so *which* chunking you pick
barely affects whether the right document is found. The interesting signal is the
failure case: the **baseline 700/100 is uniquely broken (0/3)** because that specific
boundary slices the labeled price list so an orphaned `$2,300` fragment becomes its own
retrievable chunk that competes with the intact list. Every alternative — smaller,
larger, or even naive-fixed — avoids that pathological cut and answers correctly (3/3).

**Recommendation.** **1000/150** is the best overall: it ties for the best average rank
(1.40), uses the fewest chunks (32, so cheapest to embed/store), keeps chunks under the
256-token cap (~215 tokens), and resolves the failure case. The baseline is kept as the
production default here only so the documented failure case remains reproducible; adopting
1000/150 (edit `CHUNK_SIZE`/`CHUNK_OVERLAP` in `src/config.py`, then rerun
`build_index.py`) is the one-line fix.

### 3. Metadata Filtering

Each chunk stores `source_type` metadata (`forum_thread`, `review`, `guide`, `discord`),
so retrieval can be scoped to a subset of the corpus — useful when a user trusts one kind
of source over another. `retrieve()` and `hybrid_retrieve()` take an optional
`source_types` list; the semantic path uses a ChromaDB `where` clause
(`{"source_type": {"$in": [...]}}`), the hybrid path post-filters the fused candidates.
The Streamlit sidebar exposes a **"Filter by source type"** multiselect (empty = all).

Observed behavior:

| Filter | Query | Result |
|---|---|---|
| `guide` | "best vegan dining hall" | Returns only the Vegan & Vegetarian Guide chunks; answer cites the guide |
| `discord` | "late-night food after halls close" | Returns only the `#food` Discord thread (`08-late-night-food.md`) |
| `discord` | "best vegan dining hall" (over-narrow) | System **refuses** — "not enough information" — because no Discord chunk answers it |

The last row matters: filtering can't produce a confident wrong answer. The low-relevance
guard catches most over-narrow filters, and even when it passes, the grounding prompt makes
the model refuse rather than stretch an irrelevant chunk — two independent safety nets.

### 4. Conversational Memory

The app is a multi-turn **chat** (`st.chat_input` / `st.chat_message`, history in
`st.session_state`, plus a "Clear chat" button). Follow-up questions are resolved with
**history-aware query rewriting**: before retrieval, `rewrite_followup(history, query)`
(in `src/generate.py`) asks the LLM to expand a context-dependent question into a
standalone one, then retrieval + grounded generation run on the rewrite. The app shows the
rewritten query ("🔎 searched for: …") so the resolution is visible.

Worked example (real output):

```
Turn 1 — user: "Which dining hall is best for vegan options?"
         assistant: "North Quad Dining is the best for vegans… stir-fry/tofu station…" [cites guide + North Quad]
Turn 2 — user: "Is it open late?"
         🔎 searched for: "Is North Quad Dining open late?"
         assistant: "Yes, North Quad Dining is open late, until midnight on weeknights [1][2].
                     However, the stir-fry station closes about 30 minutes before the rest
                     of the hall, around 11:30pm [1][4]."
```

The pronoun "it" was resolved to North Quad from turn 1, so retrieval found the late-hours
content instead of generic hours. Crucially, **memory only changes the search query** —
grounding, citations, and the off-topic guard are untouched, so an off-topic follow-up
still returns "not enough information." (Stuffing raw history into the generation prompt
was deliberately avoided, since it would tempt the model to answer from conversation
rather than from retrieved documents.)
