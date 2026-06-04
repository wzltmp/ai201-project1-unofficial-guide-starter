# The Unofficial Guide — Project 1

**Repository:** https://github.com/wzltmp/ai201-project1-unofficial-guide-starter
(forked from the AI201 starter)
**Demo video script:** [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)

A Retrieval-Augmented Generation (RAG) system that answers plain-language questions about
**campus dining at the University of Michigan** using **real collected sources** — Michigan
Daily reviews and opinion columns, a food-allergy guide, M\|Dining info, and a campus dining
guide. Ask *"Which dining hall has the only kosher kitchen?"* and get a grounded, **cited**
answer drawn only from those documents, with links back to the originals.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then paste a free Groq key from console.groq.com
python build_index.py         # ingest -> chunk -> embed -> store (run once)

streamlit run app.py          # the query interface
python evaluate.py            # run the 5-question evaluation framework
```

Retrieval (semantic search) works without an API key; only the grounded-answer generation
step calls Groq.

## Demo Video

A complete, timed narration script (≈4:30, stakeholder-facing) is in
[`DEMO_SCRIPT.md`](DEMO_SCRIPT.md): three queries with **citations visible**, one query where
retrieval and generation both work well (narrated), the honest **failure case** narrated
live (North Campus / North Quad confusion), an **out-of-scope refusal**, and a walkthrough of
the **evaluation report**. The recorded video goes in the repo root once filmed.

## Pipeline at a glance

```
documents/ ──► ingest.py ──► chunk.py ──► embed_store.py ──► ChromaDB
 (13 real      (clean +       (700/100      (all-MiniLM        (cosine)
  excerpts)    metadata+url)  paragraph)     -L6-v2)              │
                                                                 ▼
   answer ◄── generate.py ◄── retrieve.py (top-k semantic search) ◄┘
 (cited+URLs)  (Groq, grounded prompt)
```

Code map: `src/config.py` (knobs) · `src/ingest.py` (M3) · `src/chunk.py` (M3) ·
`src/embed_store.py` (M4) · `src/retrieve.py` (M4) · `src/generate.py` (M5) · `app.py` (M5
UI) · `build_index.py` (orchestrator) · `evaluate.py` (eval framework). Stretch: `src/hybrid.py`,
`compare_retrieval.py`, `compare_chunking.py`.

---

## Domain

**Campus dining at the University of Michigan (Ann Arbor).** The system covers U-M's
residential dining halls, meal plans, and dietary options. This knowledge is valuable and
hard to find officially because the M\|Dining site lists menus, hours, and prices but won't
tell you South Quad is the consensus best hall (and the only one with a kosher kitchen), that
Bursley on North Campus feels *"busy at best and overwhelming at worst,"* that Mojo is worth
the trip for its gooey cookies, or that the Unlimited plan only pays off if you eat in the
halls daily. That candid, comparative signal lives in student reviews and opinion writing.

---

## Document Sources

13 documents from **9 distinct real sources**. To respect each source's copyright/ToS on a
public repo, each document stores an **attributed excerpt** (representative quotes + a faithful
factual summary) plus the source URL — not a full copy.

| # | Source | Type | URL |
|---|--------|------|-----|
| 1 | The Michigan Daily — dining reviews (South Quad) | review | [link](https://www.michigandaily.com/arts/campus-culture-reviews-dining-hall-edition/) |
| 2 | The Michigan Daily — dining reviews (Mosher-Jordan/Mojo) | review | [link](https://www.michigandaily.com/arts/campus-culture-reviews-dining-hall-edition/) |
| 3 | The Michigan Daily — dining reviews (Twigs at Oxford) | review | [link](https://www.michigandaily.com/arts/campus-culture-reviews-dining-hall-edition/) |
| 4 | The Michigan Daily — dining reviews Part 2 (Bursley) | review | [link](https://www.michigandaily.com/arts/campus-culture-reviews-dining-hall-edition-part-2/) |
| 5 | The Michigan Daily — dining reviews Part 2 (North Quad) | review | [link](https://www.michigandaily.com/arts/campus-culture-reviews-dining-hall-edition-part-2/) |
| 6 | The Michigan Daily — dining reviews Part 2 (East Quad) | review | [link](https://www.michigandaily.com/arts/campus-culture-reviews-dining-hall-edition-part-2/) |
| 7 | The Michigan Daily — "My beef with MDining" (opinion) | opinion | [link](https://www.michigandaily.com/opinion/columns/my-beef-with-mdining/) |
| 8 | The Michigan Daily — new meal plans / dining dollars (news) | news | [link](https://www.michigandaily.com/news/university-housing-announces-new-meal-plans-dining-dollar-expansion) |
| 9 | M\|Dining — nutrition & allergens (vegan/vegetarian) | guide | [link](https://dining.umich.edu/about-our-food/nutrition/) |
| 10 | M\|Dining — religious observance (halal/kosher) | guide | [link](https://dining.umich.edu/meal-plans-rates/religious-observance/) |
| 11 | MI Gluten Free Gal — U-M food allergy guide | guide | [link](https://miglutenfreegal.com/university-of-michigan-food-allergy/) |
| 12 | Campus Visitor Guides — U-M campus dining overview | guide | [link](https://campusvisitorguides.com/umich/campus-dining/) |
| 13 | The Michigan Daily — signature foods (cross-hall) | review | [link](https://www.michigandaily.com/arts/campus-culture-reviews-dining-hall-edition/) |

*Reddit's r/uofm was the intended fourth source type but blocks automated fetching; a
simulated first-draft corpus is preserved under `sample_documents_simulated/` as a
reproducible pipeline-test fixture.*

**Ingestion / preprocessing (`src/ingest.py`).** Each document opens with a `---` header
(`title`, `source_type`, `source`, `url`). Ingestion (1) parses the header into attribution
metadata (including the URL) carried through to citations; (2) **strips HTML tags and decodes
entities** (`&amp;`, `&#39;`) then strips markdown markers — so a real scraped/HTML drop-in
cleans properly; (3) normalizes bullets and collapses blank lines; (4) drops empty files.

---

## Chunking Strategy

**Chunk size:** 700 characters (~150 tokens). **Overlap:** 100 characters.

**Why these choices fit the documents.** The documents are short, single-topic **attributed
excerpts** (~80–160 words), so each is essentially one self-contained, citable thought about a
single hall or topic. At 700 chars / ~150 tokens, the paragraph-aware chunker keeps each
excerpt **whole in one chunk** while staying under `all-MiniLM-L6-v2`'s 256-token cap. The
overlap and paragraph-packing matter only for the few longer excerpts.

**Final chunk count:** **17 chunks across 13 documents** (sizes 72–780 chars, avg ~496). This
is below the 50-chunk rule of thumb — a deliberate consequence of storing *excerpts* rather
than full articles (ToS/copyright), **not** of over-large chunks. The chunking-strategy
comparison (below) confirms chunk size barely affects retrieval on this excerpt corpus.

---

## Sample Chunks

Five real chunks from the index, each labeled with its source document.

**1 — `08-meal-plans-blue-bucks.md`** (The Michigan Daily / M\|Dining)
> U-M offers tiered residential meal plans. The 125-Block plan includes about 28 dining-hall
> entrances and $55.56 in Blue Bucks each month. The Unlimited Basic plan costs roughly $575
> per month across the nine fall and winter months — about $19 per day…

**2 — `05-north-quad-review.md`** (The Michigan Daily)
> North Quad is compact and convenient for a quick meal, but limited: "Compared to the other
> dining halls, North Quad can feel small and limited in variety." Breakfast was rated better
> than lunch…

**3 — `06-east-quad-review.md`** (The Michigan Daily)
> East Quad is much smaller than South Quad — "This dining hall was ¼ the size of South Quad…"
> The payoff is intimacy and service: "There was an intimacy that came with being at a smaller
> dining hall — I noticed the extra care put into everything."

**4 — `10-halal-kosher.md`** (M\|Dining)
> South Quad houses the only kosher kitchen on campus and also has a halal station. Bursley
> features a Halal station serving composed halal entrées. Across all dining halls, menu items
> are flagged with halal and kosher icons…

**5 — `13-signature-foods.md`** (The Michigan Daily)
> The most famous is the Mojo cookie at Mosher-Jordan — "a chocolate-chip masterpiece
> undercooked to the perfect degree of gooeyness." South Quad's self-serve ice cream machine
> and fried pita chips are favorites…

---

## Retrieval Test Results

Queries run through semantic retrieval (`python -m src.retrieve` / the app), top-k=4.
ChromaDB uses **cosine distance** (lower = more similar); `retrieve()` also reports
`similarity = 1 − distance`. Distance < 0.5 is a strong match; > 0.6–0.7 is weak.

**Query 1: "Which U-M dining hall has the only kosher kitchen on campus?"**

| Distance | Similarity | Source document |
|---|---|---|
| **0.302** | 0.698 | `10-halal-kosher.md` |
| 0.394 | 0.606 | `01-south-quad-review.md` |
| 0.413 | 0.587 | `12-campus-dining-overview.md` |
| 0.442 | 0.558 | `12-campus-dining-overview.md` |

*Why relevant:* the top two are exactly the documents that state South Quad has the only
kosher kitchen — the dedicated halal/kosher guide and the South Quad review corroborate each
other. Semantic search matched "kosher kitchen" to both even though the question never names
South Quad.

**Query 2: "Why do students criticize the Bursley dining hall?"**

| Distance | Similarity | Source document |
|---|---|---|
| **0.313** | 0.687 | `04-bursley-review.md` |
| 0.429 | 0.571 | `07-mdining-too-expensive.md` |
| 0.502 | 0.498 | `10-halal-kosher.md` |
| 0.527 | 0.473 | `12-campus-dining-overview.md` |

*Why relevant:* the top hit is the Bursley review itself (the criticism source), and #2 is the
opinion column arguing MDining is overpriced and unfair to North-Campus (Bursley) students —
together they explain the complaint. The lower-scored halal/kosher and overview chunks are
weak tails that don't affect the answer.

**Query 3: "Where can students find gluten-free options in U-M dining halls?"**

| Distance | Similarity | Source document |
|---|---|---|
| **0.296** | 0.704 | `11-gluten-free-allergies.md` |
| 0.310 | 0.690 | `12-campus-dining-overview.md` |
| 0.313 | 0.687 | `11-gluten-free-allergies.md` |
| 0.427 | 0.573 | `12-campus-dining-overview.md` |

The detailed gluten-free guide and the overview ("gluten-free pantries in every dining hall")
both surface; the answer draws on the specific guide.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` — 384-dim, local (no API cost
or latency), fast, strong on short text, which is exactly this excerpt corpus. Vectors are
stored in persistent **ChromaDB** with **cosine** distance.

**Production tradeoff reflection.** With cost no object I'd weigh a larger hosted embedding
model (OpenAI `text-embedding-3-large`, Voyage, Cohere). **Domain accuracy** is the key issue
here: a small general model conflates similar proper nouns — it scores "North **Quad**" as
near "North **Campus**" on the shared token, which directly caused my documented failure case;
a stronger or lightly fine-tuned model would separate campus place-names. **Context length**
would let me embed whole articles instead of excerpts. **Multilingual** support would help an
international student body. Against all that, local MiniLM is free and instant while a hosted
model adds per-query latency and indexing cost — for a class project the local model wins; for
production I'd A/B and measure whether the accuracy gain justifies the cost.

---

## Grounded Generation

**System prompt grounding instruction (`src/generate.py`).** The model is told to answer using
**only** the numbered context and never prior knowledge; to cite every claim inline with `[n]`
numbers matching the context items; to report the range of views when sources disagree; and to
reply with the exact sentence *"I don't have enough information in the collected documents to
answer that."* when the context doesn't cover the question. Temperature is 0.2 for faithfulness.

**Structural grounding.** (1) Context is a **numbered list, each item prefixed with its source
title**, giving the model explicit citable units; (2) a **low-relevance guard** — if the top
chunk's cosine similarity is below `MIN_RELEVANCE_SCORE` (0.25), the system returns the
not-enough-info answer *without calling the LLM*, so out-of-corpus questions fail closed.

**How source attribution is surfaced.** Attribution is **programmatically guaranteed**, not
left to the LLM: `_format_sources()` builds the **Sources** list from the retrieved chunks
(title, source type, **source URL**, similarity score), grouping chunks by document and keeping
the full list of citation numbers per source so **every inline `[n]` resolves** even when one
document supplied multiple cited chunks. Citations link back to the real source URL.

---

## Example Responses

Real, unedited system output (`python -m src.generate "<question>"` / the app).

**Example 1 — "Which U-M dining hall has the only kosher kitchen on campus?"**
> South Quad has the only kosher kitchen on campus [1, 2].
>
> **Sources:** [1] Halal and kosher dining at U-M (dining.umich.edu/.../religious-observance) ·
> [2] South Quad dining hall review (michigandaily.com/.../dining-hall-edition)

**Example 2 — "What is the Mosher-Jordan (Mojo) dining hall known for?"**
> Mosher-Jordan (Mojo) dining hall is known for its desserts, particularly the signature "Mojo
> cookie, a chocolate-chip masterpiece undercooked to the perfect degree of gooeyness" [1][2].
>
> **Sources:** [1] Mosher-Jordan (Mojo) dining hall review (michigandaily.com) · [2] Signature
> foods worth trying across U-M dining (michigandaily.com)

**Out-of-coverage query (refusal) — "What time does South Quad dining hall close?"**
> I don't have enough information in the collected documents to answer that.

The excerpts don't include operating hours, so rather than invent a closing time the system
refuses — even though it retrieved on-topic South Quad chunks, none contain hours.

---

## Query Interface

A **Streamlit chat app** (`streamlit run app.py`).

**Input fields:** chat box (`st.chat_input`, supports multi-turn follow-ups); sidebar **top-k**
slider; **Retrieval mode** (Semantic / Hybrid); **Filter by source type** (review / opinion /
news / guide); **Clear chat**.

**Output fields (per answer):** the grounded answer with inline `[n]` citations; a **Sources**
list (citation numbers, title, source type, **clickable source URL**, similarity); a
collapsible **Retrieved context** panel showing each chunk with its score; for follow-ups, a
"🔎 searched for: …" line showing the rewritten query.

**Sample interaction transcript:**
```
User:      Which U-M dining hall has the only kosher kitchen on campus?
Assistant: South Quad has the only kosher kitchen on campus [1, 2].
           Sources:
             [1] Halal and kosher dining at U-M — guide, dining.umich.edu (similarity 0.70)
             [2] South Quad dining hall review — review, michigandaily.com (similarity 0.61)
           ▸ Retrieved context (4 chunks)   ← expandable
```

---

## Evaluation Report

Run with `python evaluate.py`. The framework measures **Retrieval Recall@4** (did the expected
source appear in the top-4?) and **answer keyword coverage**. Headline across the 5 test
questions: **Recall@4 = 5/5 (100%)** and **mean keyword coverage = 93%**.

| # | Question | Expected answer | System response (summarized) | Retrieval | Accuracy |
|---|----------|-----------------|------------------------------|-----------|----------|
| 1 | Which hall has the only kosher kitchen? | South Quad | "South Quad has the only kosher kitchen on campus [1,2]" | Relevant | Accurate |
| 2 | Why do students criticize Bursley? | Overcrowded/"overwhelming"; only ~4 stations vs up to 10; small plates | Reported it's overcrowded with only four food stations vs up to ten elsewhere, on North Campus; cited the Bursley review | Relevant (rank 1) | Accurate (paraphrased "overwhelming", so 2/3 keywords) |
| 3 | What is Mojo known for? | Desserts — the gooey Mojo cookie | "known for its desserts, particularly the signature Mojo cookie… undercooked to the perfect degree of gooeyness" [1][2] | Relevant | Accurate |
| 4 | Single dinner cost; is Unlimited worth it? | ~$15.25/dinner; Unlimited ~$575/mo (~$19/day), worth it only if you eat daily | Gave $15.25 single lunch/dinner and the Unlimited ~$575/month, worth it if you eat in the halls daily | Relevant (rank 1) | Accurate |
| 5 | Where are gluten-free options? | Dedicated GF rooms at South Quad & Bursley; GF pasta all halls | Described the dedicated gluten-free rooms at South Quad and Bursley and GF pasta across halls | Relevant | Accurate |

**Aggregate — Retrieval:** Relevant (5/5). **Accuracy:** Accurate (5/5). The 5 designed
questions all passed, so I stress-probed further (vegan-best, hours, South-vs-East,
North-Campus) — one probe exposed a real failure, below.

---

## Failure Case Analysis

**Question that failed:** "What is the best dining hall on North Campus?"

**What the system returned:** *"Some students say North Quad is a good option … on North
Campus … while others criticize Bursley, the main dining hall on North Campus…"* — it presents
**North Quad as a North Campus dining hall**, which is **wrong**: North Quad is on Central
Campus; Bursley is the North Campus hall. Reproduced 3/3 runs.

**Root cause (embedding/retrieval → generation).** The embedding model scores "North **Quad**"
as highly similar to "North **Campus**" because they share the salient token "North," so the
North Quad review chunk is pulled into the top-k context (rank 2) for a North Campus query —
even though Bursley (the correct hall) is correctly retrieved at rank 1. Generation then trusts
the retrieved North Quad chunk and incorrectly places it "on North Campus." This is a classic
out-of-vocabulary/proper-noun confusion: the model has no geographic knowledge that "North
Quad" ≠ "North Campus," only token overlap. Hybrid (BM25) retrieval does **not** fix it,
because the issue isn't ranking (Bursley is already #1) — it's that the lexically-similar North
Quad chunk co-occurs in context and the LLM propagates it.

**What I would change to fix it.** (1) A stronger or domain-fine-tuned embedding model that
separates campus place-names; (2) add a one-line geographic fact to the system prompt or a
small metadata field (`campus: North/Central`) so generation can disambiguate; (3) tighten the
grounding prompt to not assert a location a source doesn't explicitly state for that hall.

---

## Spec Reflection

**One way the spec helped.** Writing the Chunking Strategy in `planning.md` first surfaced the
`all-MiniLM-L6-v2` 256-token cap before any code, so `config.py` shipped with sized-right
chunks the first time. The architecture diagram made the module boundaries
(ingest→chunk→embed→retrieve→generate) obvious, so each file had one responsibility — which is
exactly why swapping the entire corpus from simulated to real data required **zero pipeline
changes**.

**One way the implementation diverged.** The corpus itself diverged most: the first build used
realistic *simulated* documents, but the project calls for real collected sources, so I
re-collected from real U-M dining sources (Michigan Daily, M\|Dining, allergy/dining guides)
and updated `planning.md` and every evidence section to match. The pipeline carried over
untouched; only the documents and the numbers describing them changed — and the **failure
case changed with the data**: the simulated corpus failed on a chunk-boundary price
conflation, while the real corpus fails on the North Quad / North Campus embedding confusion.

---

## AI Usage

**Instance 1 — collecting and structuring the real corpus**
- *What I directed the AI to do:* fetch real public U-M dining sources (Michigan Daily reviews,
  meal-plan reporting, M\|Dining dietary info, a gluten-free guide) and turn them into
  attributed-excerpt documents with `title/source_type/source/url` headers.
- *What it produced:* the fetched quotes/claims and 13 excerpt documents.
- *What I changed/overrode:* required **excerpts + URLs** rather than full copies (ToS/privacy
  on a public repo), skipped Reddit (bot-blocked), and kept the simulated set as a test fixture
  instead of deleting it.

**Instance 2 — grounded generation + source attribution**
- *What I directed the AI to do:* implement the grounding prompt, numbered context, and a
  programmatic Sources list.
- *What it produced:* `SYSTEM_PROMPT`, `build_context()`, `_format_sources()`, `answer_question()`.
- *What I changed/overrode:* a review caught that inline `[n]` citations didn't all resolve to
  the Sources list, so I made `_format_sources` group by document while keeping every citation
  number, and threaded the **source URL** through so citations link to the original article.

---

## Stretch Features

Beyond the required pipeline. Each was planned in `planning.md` before implementation.

### 1. Hybrid Search (semantic + BM25)
`src/hybrid.py` fuses dense and BM25 rankings with Reciprocal Rank Fusion; the app has a
Semantic/Hybrid toggle. **Comparison** (`python compare_retrieval.py`, 5 eval questions + the
North-Campus failure probe): semantic and hybrid both get **Recall@4 6/6** with identical
average expected-doc rank (1.17) — on this small, clean excerpt corpus they tie, and hybrid
does **not** rescue the failure case (an embedding-context issue, not a ranking one). An honest
null result worth reporting.

### 2. Chunking Strategy Comparison
`python compare_chunking.py` varies only the chunker over the eval set:

| Strategy | #chunks | Recall@4 | Avg rank |
|---|---|---|---|
| paragraph 700/100 (baseline) | 17 | 5/5 | 1.20 |
| paragraph 400/80 (smaller) | 37 | 5/5 | **1.00** |
| paragraph 1000/150 (larger) | 13 | 5/5 | 1.20 |
| naive fixed 700/100 | 20 | 5/5 | 1.20 |

Because each excerpt is ~one chunk, chunk size barely moves retrieval; smaller chunks edge out
a marginally better average rank. The honest takeaway: on a short-excerpt corpus, chunking is
not the lever — corpus size and the embedding model are.

### 3. Metadata Filtering
Each chunk carries `source_type` (review / opinion / news / guide). `retrieve()` and
`hybrid_retrieve()` accept a `source_types` filter (ChromaDB `where` clause); the sidebar
exposes it. E.g. filtering to `guide` restricts answers to the official/guide docs; an
over-narrow filter still triggers the not-enough-info guard rather than a wrong answer.

### 4. Conversational Memory
The app is a multi-turn chat; `rewrite_followup()` rewrites a context-dependent follow-up into
a standalone query using prior turns before retrieval (e.g. "is it good for vegans?" → "Is
Bursley good for vegans?"), shown as "🔎 searched for: …". Grounding, citations, and the
off-topic guard are unchanged — memory only affects the search query.
