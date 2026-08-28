import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys
from uuid import uuid4

# Ensure backend root is on python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.rag.embeddings.embedder import get_embedding_provider
from app.rag.evaluation.evaluator import BenchmarkSummary, QueryEvaluationResult, RAGEvaluator
from app.rag.generation.engine import RAGEngine
from app.rag.generation.llm import MockLLMProvider
from app.rag.ingestion.chunker import ProcessedChunk
from app.rag.retrieval.retriever import RAGRetriever
from app.rag.vectorstore.chroma import ChromaVectorStore, get_vector_store


def seed_evaluation_corpus(vector_store: ChromaVectorStore) -> None:
    """Seed synthetic institutional knowledge base for standalone reproducible benchmarks."""
    vector_store.reset()

    sample_specs = [
        (
            "Academic Regulations 2026. Section 4.1: Attendance Requirements. "
            "Students must maintain a minimum attendance of 75% in all lectures, practicals, "
            "and tutorials in each registered course to be eligible to appear for the end-semester examinations. "
            "A condonation of up to 10% on medical grounds may be granted by the Dean of Academic Affairs.",
            {
                "document_name": "Academic Regulations 2026",
                "page_number": 1,
                "chunk_index": 0,
                "section": "Section 4.1 Attendance Requirements",
                "department": "Academic Affairs",
                "academic_year": "2025-2026",
                "semester": "All",
            },
        ),
        (
            "Academic Regulations 2026. Section 4.2: Graduation Requirements. "
            "A student must secure a minimum Cumulative Grade Point Average (CGPA) of 5.00 for the award of undergraduate degree. "
            "All core credits and elective requirements must be cleared with passing grades.",
            {
                "document_name": "Academic Regulations 2026",
                "page_number": 1,
                "chunk_index": 1,
                "section": "Section 4.2 Graduation Requirements",
                "department": "Academic Affairs",
                "academic_year": "2025-2026",
                "semester": "All",
            },
        ),
        (
            "Fee Regulations 2026. Section 2: Tuition Deadlines. "
            "Semester tuition fees must be cleared within 14 calendar days from the date of semester registration. "
            "A late fine of 500 currency units per week applies after the due date.",
            {
                "document_name": "Fee Regulations 2026",
                "page_number": 1,
                "chunk_index": 0,
                "section": "Section 2 Tuition Deadlines",
                "department": "Finance Office",
                "academic_year": "2025-2026",
                "semester": "All",
            },
        ),
    ]

    embedder = get_embedding_provider()
    chunks: list[ProcessedChunk] = []
    texts: list[str] = []

    doc_id = uuid4()
    for text, meta in sample_specs:
        chunk = ProcessedChunk(
            id=uuid4(),
            document_id=doc_id,
            chunk_index=meta["chunk_index"],
            page_number=meta["page_number"],
            section=meta.get("section"),
            text=text,
            token_count=len(text.split()),
            metadata=meta,
        )
        chunks.append(chunk)
        texts.append(text)

    embeddings = embedder.embed_documents(texts)
    vector_store.add_chunks(chunks=chunks, embeddings=embeddings)


async def run_evaluation(
    dataset_path: Path,
    seed_corpus: bool = True,
) -> BenchmarkSummary:
    """Execute evaluation benchmark across dataset queries."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    vector_store = get_vector_store()
    if seed_corpus:
        seed_evaluation_corpus(vector_store)

    retriever = RAGRetriever(vector_store=vector_store)
    engine = RAGEngine(retriever=retriever, llm_provider=MockLLMProvider())

    results: list[QueryEvaluationResult] = []

    for query_spec in queries:
        question = query_spec["question"]

        # 1. Retrieve
        retrieved_chunks = retriever.retrieve(question, top_k=5, min_relevance_score=0.50)
        retrieved_doc_names = [c.document_name for c in retrieved_chunks]
        context_text = "\n".join([c.text for c in retrieved_chunks])

        # 2. Generate
        rag_res = await engine.generate_answer(question=question, min_relevance_score=0.50)

        # 3. Evaluate
        cited = [
            {"document": {"title": s.document_name}, "chunk": {"page_number": s.page_number}}
            for s in rag_res.sources
        ]
        eval_item = RAGEvaluator.evaluate_query(
            query_spec=query_spec,
            retrieved_documents=retrieved_doc_names,
            retrieved_context_text=context_text,
            actual_answer=rag_res.answer,
            actual_answer_mode=rag_res.answer_mode,
            cited_sources=cited,
        )
        results.append(eval_item)

    return RAGEvaluator.aggregate_benchmark(results)


def print_scorecard(summary: BenchmarkSummary) -> None:
    """Print formatted markdown benchmark scorecard."""
    print("\n" + "=" * 68)
    print("🎓 COLLEGE RAG ASSISTANT — EVALUATION BENCHMARK SCORECARD")
    print("=" * 68)
    print(f"Total Queries Evaluated : {summary.total_queries}")
    print(f"Answerable Queries      : {summary.answerable_queries}")
    print(f"Unanswerable Queries    : {summary.unanswerable_queries}")
    print("-" * 68)
    print("RETRIEVAL QUALITY METRICS:")
    print(f"  • Recall@1            : {summary.mean_recall_at_1 * 100:.1f}%")
    print(f"  • Recall@3            : {summary.mean_recall_at_3 * 100:.1f}%")
    print(f"  • Recall@5 (Target: 80%): {summary.mean_recall_at_5 * 100:.1f}%  " + ("✅ PASS" if summary.mean_recall_at_5 >= 0.80 else "❌ BELOW TARGET"))
    print(f"  • MRR                 : {summary.mean_mrr:.4f}")
    print(f"  • Hit Rate            : {summary.mean_hit_rate * 100:.1f}%")
    print(f"  • Keyword Coverage    : {summary.mean_keyword_coverage * 100:.1f}%")
    print("-" * 68)
    print("GENERATION & GROUNDING METRICS:")
    print(f"  • Faithfulness Score  : {summary.mean_faithfulness * 100:.1f}%")
    print(f"  • Unknown Rejection   : {summary.unknown_rejection_accuracy * 100:.1f}% (Anti-hallucination)")
    print(f"  • Overall RAG Score   : {summary.overall_score * 100:.1f} / 100")
    print("-" * 68)
    print("CATEGORY BREAKDOWN:")
    for cat, scores in summary.category_scores.items():
        print(f"  [{cat.upper()}] (n={scores['count']}): Recall@5={scores['recall@5']*100:.0f}%, MRR={scores['mrr']:.2f}, Faithfulness={scores['faithfulness']*100:.0f}%")
    print("=" * 68 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG Evaluation Benchmark")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).resolve().parents[4] / "tests" / "evaluation" / "questions.json"),
        help="Path to questions.json dataset",
    )
    args = parser.parse_args()

    summary = asyncio.run(run_evaluation(Path(args.dataset)))
    print_scorecard(summary)


if __name__ == "__main__":
    main()

