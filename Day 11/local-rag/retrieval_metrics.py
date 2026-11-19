import json
import re
import sys

import config

LABEL = sys.argv[1] if len(sys.argv) > 1 else "local"
OUTPUTS_FILE = f"pipeline_outputs_{LABEL}.json"
RESULTS_FILE = f"retrieval_metrics_{LABEL}.json"

LABEL_LINE = re.compile(r"^--- Context \d+ \| (?P<source>[^|]+?) \| pp?\. (?P<first>\d+)(?:-(?P<last>\d+))? \|")


def expected_targets(question: dict) -> list[tuple[str, list[int]]]:
    sources = question.get("source_document")
    if sources is None:
        return []
    pages = question.get("source_pages", [])
    if isinstance(sources, str):
        return [(sources, pages)]
    if len(sources) == len(pages):
        return [(s, [p]) for s, p in zip(sources, pages)]
    return [(s, pages) for s in sources]


def parse_block(block: str) -> tuple[str, int, int]:
    match = LABEL_LINE.match(block)
    first = int(match["first"])
    last = int(match["last"] or first)
    return match["source"].strip(), first, last


def matches(block: tuple[str, int, int], target: tuple[str, list[int]], page_level: bool) -> bool:
    source, first, last = block
    if source != target[0]:
        return False
    return not page_level or any(first <= p <= last for p in target[1])


def score(blocks: list[tuple[str, int, int]], targets: list[tuple[str, list[int]]], page_level: bool) -> dict:
    first_rank = next(
        (i for i, b in enumerate(blocks, start=1) if any(matches(b, t, page_level) for t in targets)),
        None,
    )
    found = sum(any(matches(b, t, page_level) for b in blocks) for t in targets)
    return {
        "first_relevant_rank": first_rank,
        "reciprocal_rank": 1 / first_rank if first_rank else 0.0,
        "recall": found / len(targets),
    }


def summarise(scored: list[dict], key: str) -> dict:
    n = len(scored)
    return {
        "hit": round(sum(r[key]["first_relevant_rank"] is not None for r in scored) / n, 3),
        "mrr": round(sum(r[key]["reciprocal_rank"] for r in scored) / n, 3),
        "recall": round(sum(r[key]["recall"] for r in scored) / n, 3),
    }


def main() -> None:
    with open(config.TEST_QUESTIONS_FILE, encoding="utf-8") as f:
        questions = {q["id"]: q for q in json.load(f)}
    with open(OUTPUTS_FILE, encoding="utf-8") as f:
        rows = json.load(f)

    scored = []
    for row in rows:
        targets = expected_targets(questions[row["id"]])
        if not targets:
            continue
        blocks = [parse_block(b) for b in row["retrieved_context"]]
        scored.append({
            "id": row["id"],
            "expected": [{"source": s, "pages": p} for s, p in targets],
            "retrieved": [{"source": s, "pages": [a, b]} for s, a, b in blocks],
            "document_level": score(blocks, targets, page_level=False),
            "page_level": score(blocks, targets, page_level=True),
        })

    k = len(rows[0]["retrieved_context"])
    summary = {
        "label": LABEL,
        "k": k,
        "questions_scored": len(scored),
        "questions_skipped_unanswerable": len(rows) - len(scored),
        "document_level": summarise(scored, "document_level"),
        "page_level": summarise(scored, "page_level"),
    }
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "per_question": scored}, f, indent=2, ensure_ascii=False)

    print(f"## Retrieval metrics ({OUTPUTS_FILE}), k = {k}\n")
    print(f"Scored {len(scored)} questions, skipped {summary['questions_skipped_unanswerable']} unanswerable.\n")
    print(f"| Level | Hit@{k} | MRR | Recall |")
    print("|---|---|---|---|")
    for level in ("document_level", "page_level"):
        s = summary[level]
        print(f"| {level.replace('_', ' ')} | {s['hit']} | {s['mrr']} | {s['recall']} |")
    print("\n| id | expected (source, pages) | page-level first rank | page-level recall |")
    print("|---|---|---|---|")
    for r in scored:
        expected = "; ".join(f"{e['source']} {e['pages']}" for e in r["expected"])
        rank = r["page_level"]["first_relevant_rank"] or "miss"
        print(f"| {r['id']} | {expected} | {rank} | {r['page_level']['recall']:.2f} |")
    print(f"\nSaved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()