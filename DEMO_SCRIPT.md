# 🎬 The Unofficial Guide — Demo Video Script

**Target length:** 3–5 minutes (this runs ~4:30 at a calm pace).
**Audience:** stakeholders — lead with *what it does* and *why it's trustworthy*.
**Domain:** real University of Michigan campus-dining sources (Michigan Daily, M|Dining, dining guides).

---

## Before you hit record (setup)

1. Venv active, index built:
   ```
   source .venv/bin/activate
   python build_index.py        # 13 docs -> 17 chunks
   ```
2. App running, browser ready:
   ```
   streamlit run app.py         # http://localhost:8501
   ```
3. Second terminal tab ready for `python evaluate.py`.
4. Sidebar at defaults: Retrieval mode = Semantic, top-k = 4, no source filter.
5. Every query below is verified to behave as described. Paste queries instead of typing.

---

## SCENE 1 — What this is (0:00 – 0:30)

**On screen:** the app title and sidebar.

> "This is **The Unofficial Guide** — a question-answering system over the *real* knowledge
> students share about University of Michigan dining: Michigan Daily reviews and opinion
> columns, dining guides, allergy guides. You ask a plain-language question and it gives a
> **grounded, cited answer** — drawn only from those collected documents, with links back to
> the originals — instead of a confident guess from a chatbot's training data. Under the hood
> it's a retrieval pipeline: 13 real-source documents, local embeddings, ChromaDB, and a
> Llama-3.3 model for the answer."

---

## SCENE 2 — Query 1: works well, with citations (0:30 – 1:25)

**Action:** type **"Which U-M dining hall has the only kosher kitchen on campus?"**

**On screen:** answer naming **South Quad**, the **Sources** list (with clickable URLs),
then expand **"🔎 Retrieved context."**

> "First question — *which dining hall has the only kosher kitchen?* It answers **South
> Quad**, and crucially it **cites where that came from**: the M-Dining religious-observance
> guide and the South Quad review — both real, both linked. If I expand the retrieved
> context, you can see the actual chunks it used and their similarity scores; the top match
> is a distance of about 0.30, a strong hit. Notice the question never said 'South Quad' —
> semantic search matched on *meaning*, and two independent sources agree, so the answer is
> fully traceable."

---

## SCENE 3 — Query 2: a second cited answer (1:25 – 2:00)

**Action:** type **"What is the Mosher-Jordan (Mojo) dining hall known for?"**

> "Second — *what is Mojo known for?* It answers: the desserts, especially the famous Mojo
> cookie — and it quotes the review directly, 'a chocolate-chip masterpiece undercooked to
> the perfect degree of gooeyness,' cited to the Michigan Daily. Every claim carries a
> citation back to a real article."

---

## SCENE 4 — Conversational memory (2:00 – 2:50)

**Action:** ask **"Why do students criticize the Bursley dining hall?"**, let it answer, then
ask the follow-up **"Is it good for vegans?"** Point to the "🔎 searched for:" line.

> "Now watch conversational memory. I ask why students criticize **Bursley** — it explains
> it's overcrowded, only four food stations versus up to ten elsewhere, all cited. Then I ask
> a vague follow-up: *'is it good for vegans?'* The system **rewrites** that into *'Is Bursley
> good for vegans?'* — you can see it on screen — and answers from the vegan-options document
> that Bursley runs a dedicated vegan station called 24 Carrots. It remembered what 'it' meant."

---

## SCENE 5 — Where it FAILS (the honest failure) (2:50 – 3:45)

**Action:** type **"What is the best dining hall on North Campus?"** Pause on the answer.

> "Now the most important part — where it **fails**. I ask for the best dining hall on **North
> Campus**. Watch the answer: it says *'North Quad is a good option on North Campus.'* That's
> **wrong** — North Quad is on Central Campus. The only North Campus dining hall is Bursley.
> **Why does it happen?** It's an *embedding* problem. The model sees 'North **Quad**' and
> 'North **Campus**' as similar because they share the word 'North,' so it pulls the North Quad
> review into context for a North Campus question — and the language model then repeats it as
> fact. It has no map of campus; it only has word overlap. I traced this to the retrieval
> step, and I show in the README that even hybrid keyword search doesn't fix it, because the
> problem isn't ranking — it's that a look-alike document lands in the context. The fix is a
> stronger embedding model or a campus-location tag. Knowing *why* it breaks is the point."

---

## SCENE 6 — Refusing what it doesn't know (3:45 – 4:05)

**Action:** type **"What time does South Quad dining hall close?"**

> "One more — a question the documents don't cover. My sources are excerpts; they don't include
> hours. Notice the system actually *retrieved* South Quad chunks — but none of them state a
> closing time, so instead of inventing one it **refuses**: *'I don't have enough information.'*
> And it shows **no sources**, because there's nothing to cite. For a tool people should trust,
> not answering is the right answer."

---

## SCENE 7 — Evaluation report (4:05 – 4:35)

**Action:** terminal → **`python evaluate.py`** → scroll to SUMMARY.

> "Finally, evaluation. I wrote five test questions with known answers up front, and
> `evaluate.py` checks automatically: did it retrieve the right source, and did the answer
> contain the key facts. Across all five: **5 out of 5 on retrieval** and **93% keyword
> coverage** — not a suspicious 100%; one answer paraphrased instead of using the exact word.
> The result I care about most, though, is the failure you just saw — which this framework is
> built to surface. A system you can trust is one whose limits you understand. Thanks."

---

## Quick reference — queries in order

| # | Query | Highlight |
|---|-------|-----------|
| 1 | Which U-M dining hall has the only kosher kitchen on campus? | Works well, citations + context panel |
| 2 | What is the Mosher-Jordan (Mojo) dining hall known for? | Direct quote, cited |
| 3 | Why do students criticize the Bursley dining hall? → "Is it good for vegans?" | Conversational memory / rewrite |
| 4 | What is the best dining hall on North Campus? | **Failure** — North Quad ≠ North Campus (embedding confusion) |
| 5 | What time does South Quad dining hall close? | Refusal / out-of-scope |
| — | `python evaluate.py` | 5/5 Recall@4, 93% coverage |

**Requirement coverage:** 3+ queries with citations (Scenes 2–4) ✓ · one works-well query
narrated (Scene 2) ✓ · one failure narrated (Scene 5) ✓ · evaluation walkthrough (Scene 7) ✓ ·
~4:30 runtime ✓.
