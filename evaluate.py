"""Evaluation framework for The Unofficial Guide.

Runs the 5 ground-truth test questions through the pipeline and measures quality
two ways instead of eyeballing:

  - Retrieval hit (Recall@k): did the expected source document appear in the
    top-k retrieved chunks?
  - Answer keyword coverage: what fraction of the expected ground-truth keywords
    show up in the generated answer? (a cheap proxy for "did it say the right thing")

Retrieval metrics need no API key, so the retrieval half always runs. The answer
half runs only if GROQ_API_KEY is set; otherwise it's skipped and reported as such.

    python evaluate.py            # retrieval + (if key set) generation
    python evaluate.py --retrieval-only
"""

from __future__ import annotations

import sys

from src import config
from src.retrieve import retrieve

# Each case: the question, the document that should answer it (expected_source,
# matched against retrieved chunk filenames), and ground-truth keywords we expect
# a correct answer to contain.
TEST_CASES = [
    {
        "question": "What do students say about wait times at Hillside Commons during lunch?",
        "expected_source": "01-hillside-commons-reviews.md",
        "expected_keywords": ["lunch", "line", "wait", "11:30"],
    },
    {
        "question": "Which dining hall is best for vegan options?",
        "expected_source": "02-north-quad-dining-reviews.md",
        "expected_keywords": ["North Quad", "stir-fry", "tofu", "vegan"],
    },
    {
        "question": "Is the unlimited meal plan worth it compared to the block plan?",
        "expected_source": "05-meal-plan-megathread.md",
        "expected_keywords": ["unlimited", "block", "swipe", "worth"],
    },
    {
        "question": "Where's the best quiet place to study late at night?",
        "expected_source": "10-best-study-spots.md",
        "expected_keywords": ["Tewell", "quiet", "floor", "Engineering"],
    },
    {
        "question": "What late-night food is available after the dining halls close?",
        "expected_source": "08-late-night-food.md",
        "expected_keywords": ["North Quad", "midnight", "Moonlight", "convenience"],
    },
]


def keyword_coverage(answer: str, keywords: list[str]) -> tuple[float, list[str]]:
    """Fraction of expected keywords present in the answer (case-insensitive)."""
    low = answer.lower()
    hits = [k for k in keywords if k.lower() in low]
    return len(hits) / len(keywords), hits


def evaluate(retrieval_only: bool = False) -> None:
    generate = bool(config.GROQ_API_KEY) and not retrieval_only
    if not generate:
        reason = "--retrieval-only" if retrieval_only else "no GROQ_API_KEY"
        print(f"(Generation metrics skipped: {reason}. Retrieval metrics below.)\n")

    answer_question = None
    if generate:
        from src.generate import answer_question  # noqa: imported lazily

    retrieval_hits = 0
    coverage_scores: list[float] = []

    for i, case in enumerate(TEST_CASES, start=1):
        q = case["question"]
        chunks = retrieve(q)
        retrieved_files = [c["filename"] for c in chunks]
        hit = case["expected_source"] in retrieved_files
        retrieval_hits += int(hit)

        print(f"{'=' * 78}")
        print(f"Q{i}: {q}")
        print(f"  expected source : {case['expected_source']}")
        print(f"  retrieved (top-{len(chunks)}):")
        for c in chunks:
            mark = "  <-- expected" if c["filename"] == case["expected_source"] else ""
            print(f"      {c['score']:.3f}  {c['filename']}{mark}")
        print(f"  RETRIEVAL: {'HIT ✓' if hit else 'MISS ✗'} (expected doc in top-k)")

        if generate:
            result = answer_question(q)
            answer = result["answer"]
            cov, found = keyword_coverage(answer, case["expected_keywords"])
            coverage_scores.append(cov)
            print(f"\n  ANSWER:\n      {answer.replace(chr(10), chr(10) + '      ')}")
            print(
                f"  KEYWORD COVERAGE: {cov:.0%} "
                f"({len(found)}/{len(case['expected_keywords'])}: {', '.join(found)})"
            )
        print()

    n = len(TEST_CASES)
    print(f"{'=' * 78}")
    print("SUMMARY")
    print(f"  Retrieval Recall@{config.TOP_K}: {retrieval_hits}/{n} "
          f"({retrieval_hits / n:.0%}) of questions retrieved their expected source")
    if coverage_scores:
        mean_cov = sum(coverage_scores) / len(coverage_scores)
        print(f"  Mean answer keyword coverage: {mean_cov:.0%}")
    print(f"{'=' * 78}")


if __name__ == "__main__":
    evaluate(retrieval_only="--retrieval-only" in sys.argv)
