from pathlib import Path
import pytest

from app.rag.evaluation.evaluator import RAGEvaluator
from app.rag.evaluation.run_eval import run_evaluation


def test_evaluator_recall_at_k() -> None:
    # Match in top-1
    assert RAGEvaluator.calculate_recall_at_k(["Academic Regulations 2026", "Fee Rules"], ["Academic Regulations 2026"], k=1) == 1.0
    # Match in top-3 but not top-1
    assert RAGEvaluator.calculate_recall_at_k(["Other Doc", "Academic Regulations 2026"], ["Academic Regulations 2026"], k=1) == 0.0
    assert RAGEvaluator.calculate_recall_at_k(["Other Doc", "Academic Regulations 2026"], ["Academic Regulations 2026"], k=3) == 1.0
    # No match
    assert RAGEvaluator.calculate_recall_at_k(["Doc A", "Doc B"], ["Academic Regulations 2026"], k=5) == 0.0
    # Empty expected
    assert RAGEvaluator.calculate_recall_at_k([], [], k=5) == 1.0


def test_evaluator_mrr() -> None:
    # First rank match: MRR = 1.0
    assert RAGEvaluator.calculate_mrr(["Target Doc", "Doc B"], ["Target Doc"]) == 1.0
    # Second rank match: MRR = 0.5
    assert RAGEvaluator.calculate_mrr(["Doc A", "Target Doc"], ["Target Doc"]) == 0.5
    # Third rank match: MRR = 1/3 ~= 0.3333
    assert round(RAGEvaluator.calculate_mrr(["Doc A", "Doc B", "Target Doc"], ["Target Doc"]), 4) == 0.3333
    # No match: MRR = 0.0
    assert RAGEvaluator.calculate_mrr(["Doc A", "Doc B"], ["Target Doc"]) == 0.0


def test_evaluator_hit_rate() -> None:
    assert RAGEvaluator.calculate_hit_rate(["Doc A", "Target Doc"], ["Target Doc"]) == 1.0
    assert RAGEvaluator.calculate_hit_rate(["Doc A", "Doc B"], ["Target Doc"]) == 0.0


def test_evaluator_keyword_coverage() -> None:
    text = "Students must maintain minimum 75% attendance in lectures."
    assert RAGEvaluator.calculate_keyword_coverage(text, ["75%", "attendance"]) == 1.0
    assert RAGEvaluator.calculate_keyword_coverage(text, ["75%", "parking"]) == 0.5
    assert RAGEvaluator.calculate_keyword_coverage(text, []) == 1.0


def test_evaluator_faithfulness() -> None:
    context = "Undergraduate regulations state attendance must be at least 75 percent."
    grounded_answer = "Based on institutional documents, regulations state attendance must be 75 percent."
    hallucinated_answer = "The campus swimming pool is open 24 hours daily with free access."
    unknown_answer = "I couldn't find reliable information about this in the college knowledge base."

    # Grounded answer has high faithfulness
    assert RAGEvaluator.calculate_faithfulness(grounded_answer, context) >= 0.70
    # Hallucinated answer has low faithfulness
    assert RAGEvaluator.calculate_faithfulness(hallucinated_answer, context) == 0.0
    # Safe refusal is faithful
    assert RAGEvaluator.calculate_faithfulness(unknown_answer, context) == 1.0


@pytest.mark.anyio
async def test_end_to_end_benchmark_run() -> None:
    dataset_path = Path(__file__).resolve().parents[2] / "tests" / "evaluation" / "questions.json"
    assert dataset_path.exists(), "Benchmark dataset must exist"

    summary = await run_evaluation(dataset_path, seed_corpus=True)

    assert summary.total_queries == 8
    assert summary.mean_recall_at_5 >= 0.80, f"Recall@5 should meet >= 0.80 target, got {summary.mean_recall_at_5}"
    assert summary.mean_mrr >= 0.70, f"MRR should be >= 0.70, got {summary.mean_mrr}"
    assert summary.unknown_rejection_accuracy == 1.0, "Unanswerable questions must be safely refused"
    assert summary.overall_score >= 0.80, f"Overall RAG score should be >= 0.80, got {summary.overall_score}"

