"""Compare hybrid (semantic + BM25) retrieval against semantic-only.

For each evaluation question we report, for both retrievers, whether the expected
source document was retrieved and at what rank (lower rank = better). This makes the
"does hybrid help?" question concrete instead of hand-wavy.

    python compare_retrieval.py
"""

from __future__ import annotations

from evaluate import TEST_CASES
from src import config
from src.hybrid import hybrid_retrieve
from src.retrieve import retrieve

# An extra keyword-heavy probe: this is the documented failure case, where the clean
# labeled price list lives in one specific chunk that dense search doesn't always rank top.
EXTRA = [
    {
        "question": "How much does the unlimited meal plan cost per semester?",
        "expected_source": "05-meal-plan-megathread.md",
    }
]


def _rank_of(results: list[dict], expected_source: str) -> int | None:
    """1-based rank of the first chunk from expected_source, or None if absent."""
    for r in results:
        if r["filename"] == expected_source:
            return r["rank"]
    return None


def _fmt(rank: int | None) -> str:
    return f"rank {rank}" if rank else "MISS"


def main() -> None:
    cases = TEST_CASES + EXTRA
    pool_k = config.TOP_K

    sem_hits = hyb_hits = 0
    sem_rank_sum = hyb_rank_sum = 0
    counted = 0

    print(f"Comparing retrieval over {len(cases)} questions (top-{pool_k})\n")
    print(f"{'Q':<3}{'expected doc':<34}{'semantic':<14}{'hybrid':<14}{'winner'}")
    print("-" * 78)

    for i, case in enumerate(cases, start=1):
        exp = case["expected_source"]
        sem = _rank_of(retrieve(case["question"], top_k=pool_k), exp)
        hyb = _rank_of(hybrid_retrieve(case["question"], top_k=pool_k), exp)

        sem_hits += int(sem is not None)
        hyb_hits += int(hyb is not None)
        if sem and hyb:
            counted += 1
            sem_rank_sum += sem
            hyb_rank_sum += hyb

        if (hyb or 99) < (sem or 99):
            winner = "hybrid"
        elif (sem or 99) < (hyb or 99):
            winner = "semantic"
        else:
            winner = "tie"

        print(f"{i:<3}{exp:<34}{_fmt(sem):<14}{_fmt(hyb):<14}{winner}")

    n = len(cases)
    print("-" * 78)
    print(f"Recall@{pool_k}:  semantic {sem_hits}/{n}   hybrid {hyb_hits}/{n}")
    if counted:
        print(
            f"Avg rank of expected doc (lower=better, on the {counted} both found): "
            f"semantic {sem_rank_sum / counted:.2f}   hybrid {hyb_rank_sum / counted:.2f}"
        )


if __name__ == "__main__":
    main()
