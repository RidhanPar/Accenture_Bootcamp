import json
import time

import config
from generate import generate_answer
from retrieve import retrieve_chunks




def answer_question(query: str) -> dict:
    retrieval_result = retrieve_chunks(query)
    generation_result = generate_answer(
        query=query,
        chunks=retrieval_result["retrieved_chunks"],
    )
    return {
        **generation_result,
        "retrieval": retrieval_result,
    }


def to_output_row(question: dict, result: dict) -> dict:
    chunks = result["retrieval"]["retrieved_chunks"]
    return {
        "id": question["id"],
        "question": question["question"],
        "expected_answer": question["expected_answer"],
        "actual_answer": result["answer"],
        "retrieved_context": result["context_used"],
        "context_sources": [
            {"source": c["source"], "page": c["page"], "score": c["relevance_score"]}
            for c in chunks
        ],
        "model": result["model"],
        "thinking": result["thinking"],
        "finish_reason": result["finish_reason"],
        "embedding_model": result["retrieval"]["embedding_model"],
        "prompt_tokens": result["prompt_tokens"],
        "tokens_generated": result["tokens_generated"],
        "retrieval_time_ms": result["retrieval"]["retrieval_time_ms"],
        "generation_time_ms": result["generation_time_ms"],
        "passed": None,
        "rating_note": "",
    }


def save(rows: list[dict]) -> None:
    with open(config.OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


def main() -> None:
    with open(config.TEST_QUESTIONS_FILE, encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Running {len(questions)} questions with {config.LLM_MODEL}, top_k={config.TOP_K}")
    start = time.time()
    rows = []

    for number, question in enumerate(questions, start=1):
        print(f"[{number}/{len(questions)}] {question['id']}: {question['question']}")
        result = answer_question(question["question"])
        rows.append(to_output_row(question, result))
        save(rows)
        print(f"    finish_reason={result['finish_reason']} | "
              f"{result['generation_time_ms']} ms | {result['answer'][:80]!r}")

    print(f"Done in {time.time() - start:.0f} s. Saved {len(rows)} rows to {config.OUTPUT_FILE}")


if __name__ == "__main__":
    main()