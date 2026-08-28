from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryEvaluationResult:
    query_id: str
    category: str
    question: str
    is_unanswerable: bool
    expected_answer_mode: str
    actual_answer_mode: str
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    hit_rate: float
    keyword_coverage: float
    faithfulness_score: float
    citation_correct: bool
    unknown_accuracy: float
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BenchmarkSummary:
    total_queries: int
    answerable_queries: int
    unanswerable_queries: int
    mean_recall_at_1: float
    mean_recall_at_3: float
    mean_recall_at_5: float
    mean_mrr: float
    mean_hit_rate: float
    mean_keyword_coverage: float
    mean_faithfulness: float
    unknown_rejection_accuracy: float
    overall_score: float
    category_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    query_results: list[QueryEvaluationResult] = field(default_factory=list)


class RAGEvaluator:
    """Quantitative evaluation engine for RAG retrieval and generation quality."""

    @staticmethod
    def calculate_recall_at_k(
        retrieved_identifiers: list[str],
        expected_identifiers: list[str],
        k: int = 5,
    ) -> float:
        """Calculate Recall@K: 1.0 if any expected target is in top-K retrieved, else 0.0."""
        if not expected_identifiers:
            return 1.0 if not retrieved_identifiers else 0.0

        top_k = retrieved_identifiers[:k]
        for expected in expected_identifiers:
            for retrieved in top_k:
                if expected.lower() in retrieved.lower() or retrieved.lower() in expected.lower():
                    return 1.0
        return 0.0

    @staticmethod
    def calculate_mrr(
        retrieved_identifiers: list[str],
        expected_identifiers: list[str],
    ) -> float:
        """Calculate Mean Reciprocal Rank (MRR): 1 / rank of first relevant match."""
        if not expected_identifiers:
            return 1.0 if not retrieved_identifiers else 0.0

        for rank, retrieved in enumerate(retrieved_identifiers, start=1):
            for expected in expected_identifiers:
                if expected.lower() in retrieved.lower() or retrieved.lower() in expected.lower():
                    return 1.0 / rank
        return 0.0

    @staticmethod
    def calculate_hit_rate(
        retrieved_identifiers: list[str],
        expected_identifiers: list[str],
    ) -> float:
        """Calculate Hit Rate: 1.0 if at least one expected match found, else 0.0."""
        if not expected_identifiers:
            return 1.0 if not retrieved_identifiers else 0.0

        for expected in expected_identifiers:
            for retrieved in retrieved_identifiers:
                if expected.lower() in retrieved.lower() or retrieved.lower() in expected.lower():
                    return 1.0
        return 0.0

    @staticmethod
    def calculate_keyword_coverage(text: str, expected_keywords: list[str]) -> float:
        """Calculate percentage of expected key terms present in text."""
        if not expected_keywords:
            return 1.0
        if not text:
            return 0.0

        text_lower = text.lower()
        matched = sum(1 for kw in expected_keywords if kw.lower() in text_lower)
        return matched / len(expected_keywords)

    @staticmethod
    def calculate_faithfulness(answer: str, context_text: str) -> float:
        """Calculate simple lexical grounding faithfulness score."""
        if not answer:
            return 0.0
        if "I couldn't find reliable information" in answer:
            return 1.0  # Safe rejection is completely faithful

        if not context_text:
            return 0.0

        # Check proportion of significant answer words present in context
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
            "of", "by", "from", "up", "about", "into", "through", "after", "is", "are",
            "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "shall", "should", "can", "could", "may", "might", "must",
            "it", "this", "that", "these", "those", "based", "institutional", "documents",
            "verified", "provided", "sources", "information", "requested", "college"
        }
        answer_words = [
            w.strip(".,!?:;\"'()[]{}")
            for w in answer.lower().split()
            if len(w.strip(".,!?:;\"'()[]{}")) > 2
        ]
        significant_words = [w for w in answer_words if w not in stopwords]
        if not significant_words:
            return 1.0

        context_lower = context_text.lower()
        matched = sum(1 for w in significant_words if w in context_lower)
        return min(1.0, matched / len(significant_words))

    @classmethod
    def evaluate_query(
        cls,
        query_spec: dict[str, Any],
        retrieved_documents: list[str],
        retrieved_context_text: str,
        actual_answer: str,
        actual_answer_mode: str,
        cited_sources: list[dict[str, Any]] | None = None,
    ) -> QueryEvaluationResult:
        """Evaluate a single query execution against expected ground truth."""
        query_id = query_spec.get("id", "unknown")
        category = query_spec.get("category", "general")
        question = query_spec.get("question", "")
        is_unanswerable = query_spec.get("is_unanswerable", False)
        expected_doc = query_spec.get("expected_document")
        expected_keywords = query_spec.get("expected_keywords", [])
        expected_mode = query_spec.get("expected_answer_mode", "grounded")

        expected_docs = [expected_doc] if expected_doc else []

        if is_unanswerable:
            # For unanswerable queries, success means unknown mode and 0 hallucinated context
            unknown_acc = 1.0 if actual_answer_mode == "unknown" else 0.0
            return QueryEvaluationResult(
                query_id=query_id,
                category=category,
                question=question,
                is_unanswerable=True,
                expected_answer_mode="unknown",
                actual_answer_mode=actual_answer_mode,
                recall_at_1=1.0 if actual_answer_mode == "unknown" else 0.0,
                recall_at_3=1.0 if actual_answer_mode == "unknown" else 0.0,
                recall_at_5=1.0 if actual_answer_mode == "unknown" else 0.0,
                mrr=1.0 if actual_answer_mode == "unknown" else 0.0,
                hit_rate=1.0 if actual_answer_mode == "unknown" else 0.0,
                keyword_coverage=1.0,
                faithfulness_score=1.0 if actual_answer_mode == "unknown" else 0.0,
                citation_correct=len(cited_sources or []) == 0,
                unknown_accuracy=unknown_acc,
                answer=actual_answer,
                sources=cited_sources or [],
            )

        # Answerable query
        r1 = cls.calculate_recall_at_k(retrieved_documents, expected_docs, k=1)
        r3 = cls.calculate_recall_at_k(retrieved_documents, expected_docs, k=3)
        r5 = cls.calculate_recall_at_k(retrieved_documents, expected_docs, k=5)
        mrr = cls.calculate_mrr(retrieved_documents, expected_docs)
        hit_rate = cls.calculate_hit_rate(retrieved_documents, expected_docs)
        kw_cov = cls.calculate_keyword_coverage(
            f"{retrieved_context_text} {actual_answer}", expected_keywords
        )
        faithfulness = cls.calculate_faithfulness(actual_answer, retrieved_context_text)
        unknown_acc = 1.0 if actual_answer_mode == "grounded" else 0.0
        citation_correct = len(cited_sources or []) > 0 if expected_doc else True

        return QueryEvaluationResult(
            query_id=query_id,
            category=category,
            question=question,
            is_unanswerable=False,
            expected_answer_mode=expected_mode,
            actual_answer_mode=actual_answer_mode,
            recall_at_1=r1,
            recall_at_3=r3,
            recall_at_5=r5,
            mrr=mrr,
            hit_rate=hit_rate,
            keyword_coverage=kw_cov,
            faithfulness_score=faithfulness,
            citation_correct=citation_correct,
            unknown_accuracy=unknown_acc,
            answer=actual_answer,
            sources=cited_sources or [],
        )

    @classmethod
    def aggregate_benchmark(
        cls,
        results: list[QueryEvaluationResult],
    ) -> BenchmarkSummary:
        """Aggregate individual query results into complete benchmark summary."""
        if not results:
            return BenchmarkSummary(
                total_queries=0,
                answerable_queries=0,
                unanswerable_queries=0,
                mean_recall_at_1=0.0,
                mean_recall_at_3=0.0,
                mean_recall_at_5=0.0,
                mean_mrr=0.0,
                mean_hit_rate=0.0,
                mean_keyword_coverage=0.0,
                mean_faithfulness=0.0,
                unknown_rejection_accuracy=0.0,
                overall_score=0.0,
                category_scores={},
                query_results=[],
            )

        total = len(results)
        answerable = [r for r in results if not r.is_unanswerable]
        unanswerable = [r for r in results if r.is_unanswerable]

        mean_r1 = sum(r.recall_at_1 for r in results) / total
        mean_r3 = sum(r.recall_at_3 for r in results) / total
        mean_r5 = sum(r.recall_at_5 for r in results) / total
        mean_mrr = sum(r.mrr for r in results) / total
        mean_hit = sum(r.hit_rate for r in results) / total
        mean_kw = sum(r.keyword_coverage for r in results) / total
        mean_faith = sum(r.faithfulness_score for r in results) / total

        unk_acc = (
            sum(r.unknown_accuracy for r in unanswerable) / len(unanswerable)
            if unanswerable
            else 1.0
        )

        overall = (mean_r5 * 0.3) + (mean_mrr * 0.2) + (mean_faith * 0.25) + (unk_acc * 0.25)

        # Categorical breakdown
        categories: dict[str, list[QueryEvaluationResult]] = {}
        for r in results:
            categories.setdefault(r.category, []).append(r)

        cat_scores: dict[str, dict[str, float]] = {}
        for cat_name, cat_items in categories.items():
            cat_len = len(cat_items)
            cat_scores[cat_name] = {
                "count": cat_len,
                "recall@5": sum(x.recall_at_5 for x in cat_items) / cat_len,
                "mrr": sum(x.mrr for x in cat_items) / cat_len,
                "faithfulness": sum(x.faithfulness_score for x in cat_items) / cat_len,
            }

        return BenchmarkSummary(
            total_queries=total,
            answerable_queries=len(answerable),
            unanswerable_queries=len(unanswerable),
            mean_recall_at_1=round(mean_r1, 4),
            mean_recall_at_3=round(mean_r3, 4),
            mean_recall_at_5=round(mean_r5, 4),
            mean_mrr=round(mean_mrr, 4),
            mean_hit_rate=round(mean_hit, 4),
            mean_keyword_coverage=round(mean_kw, 4),
            mean_faithfulness=round(mean_faith, 4),
            unknown_rejection_accuracy=round(unk_acc, 4),
            overall_score=round(overall, 4),
            category_scores=cat_scores,
            query_results=results,
        )

