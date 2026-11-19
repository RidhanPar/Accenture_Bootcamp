import json
import math
import os
import statistics as st
import sys

LABELS = ("local", "cloud")
METRICS = ("Contextual Relevancy", "Contextual Recall", "Contextual Precision", "Faithfulness", "Answer Relevancy")
GENERATION_METRICS = ("Faithfulness", "Answer Relevancy")
THRESHOLD = 0.7
REFUSAL = "cannot find this information"
OUTPUT_FILE = "compare_output.md"

PRICE_INPUT_PER_1M = os.getenv("PRICE_INPUT_PER_1M")
PRICE_OUTPUT_PER_1M = os.getenv("PRICE_OUTPUT_PER_1M")


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return {row["id"]: row for row in json.load(f)}


def mean_2se(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        return (values[0] if values else math.nan), math.nan
    return st.mean(values), 2 * st.stdev(values) / math.sqrt(len(values))


def fmt(mean: float, err: float) -> str:
    return f"{mean:.2f} ± {err:.2f}"


def metric_table(evals: dict) -> list[str]:
    lines = [
        "| Metric | n | Local | Cloud | Cloud − local (per question) | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for metric in METRICS:
        ids = [
            qid for qid in evals["local"]
            if qid in evals["cloud"]
            and evals["local"][qid]["metrics"].get(metric, {}).get("score") is not None
            and evals["cloud"][qid]["metrics"].get(metric, {}).get("score") is not None
        ]
        local = [evals["local"][q]["metrics"][metric]["score"] for q in ids]
        cloud = [evals["cloud"][q]["metrics"][metric]["score"] for q in ids]
        diff = [c - l for c, l in zip(cloud, local)]
        d_mean, d_err = mean_2se(diff)
        if d_mean - d_err <= 0 <= d_mean + d_err:
            verdict = "no clear difference"
        else:
            verdict = "cloud higher" if d_mean > 0 else "local higher"
        lines.append(
            f"| {metric} | {len(ids)} | {fmt(*mean_2se(local))} | {fmt(*mean_2se(cloud))} "
            f"| {fmt(d_mean, d_err)} | {verdict} |"
        )
    return lines


def cost_text(rows: list[dict]) -> str:
    if not (PRICE_INPUT_PER_1M and PRICE_OUTPUT_PER_1M):
        return "not set"
    price_in, price_out = float(PRICE_INPUT_PER_1M), float(PRICE_OUTPUT_PER_1M)
    costs = [
        (r["prompt_tokens"] or 0) * price_in / 1e6 + (r["tokens_generated"] or 0) * price_out / 1e6
        for r in rows
    ]
    return f"{st.mean(costs):.5f} per question, {sum(costs):.4f} for all {len(costs)}"


def run_table(outputs: dict) -> list[str]:
    lines = [
        "| Run | Model | Median generation (s) | Slowest generation (s) | Avg prompt tokens | "
        "Avg completion tokens | Empty or failed answers | Cost (list price) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label in LABELS:
        rows = list(outputs[label].values())
        times = [r["generation_time_ms"] for r in rows]
        note = ""
        if label == "local":
            times = times[1:]
            note = " (first call dropped: model load)"
        failed = [
            r["id"] for r in rows
            if not (r["actual_answer"] or "").strip() or r.get("finish_reason") not in ("stop",)
        ]
        lines.append(
            f"| {label}{note} | {rows[0]['model']} | {st.median(times) / 1000:.1f} | {max(times) / 1000:.1f} "
            f"| {st.mean(r['prompt_tokens'] or 0 for r in rows):.0f} "
            f"| {st.mean(r['tokens_generated'] or 0 for r in rows):.0f} "
            f"| {len(failed)}{' (' + ', '.join(failed) + ')' if failed else ''} "
            f"| {cost_text(rows) if label == 'cloud' else 'local hardware, no per-token cost'} |"
        )
    return lines


def refusal_table(outputs: dict, questions: dict) -> list[str]:
    unanswerable = [q for q, meta in questions.items() if meta.get("type") == "unanswerable"]
    lines = [
        f"Unanswerable questions, string check for \"{REFUSAL}\":",
        "",
        "| Run | Refused with the exact sentence | Questions |",
        "|---|---|---|",
    ]
    for label in LABELS:
        hits = [q for q in unanswerable if REFUSAL in (outputs[label][q]["actual_answer"] or "").lower()]
        lines.append(f"| {label} | {len(hits)} of {len(unanswerable)} | {', '.join(hits) or 'none'} |")
    return lines


def judge_vs_hand(outputs: dict, evals: dict) -> list[str]:
    lines = [
        f"Judge vs hand rating. Judge pass = {' and '.join(GENERATION_METRICS)} both >= {THRESHOLD}. "
        "Hand pass = `passed` in pipeline_outputs_<label>.json.",
        "",
        "| Run | Both pass | Both fail | Judge passes, I failed | Judge fails, I passed |",
        "|---|---|---|---|---|",
    ]
    for label in LABELS:
        cases = {"both_pass": [], "both_fail": [], "judge_only": [], "hand_only": []}
        for qid, row in outputs[label].items():
            metrics = evals[label][qid]["metrics"]
            judge = all((metrics.get(m, {}).get("score") or 0) >= THRESHOLD for m in GENERATION_METRICS)
            hand = bool(row.get("passed"))
            key = {(True, True): "both_pass", (False, False): "both_fail",
                   (True, False): "judge_only", (False, True): "hand_only"}[(judge, hand)]
            cases[key].append(qid)
        cell = lambda ids: f"{len(ids)}{' (' + ', '.join(sorted(ids)) + ')' if ids else ''}"
        lines.append(
            f"| {label} | {cell(cases['both_pass'])} | {cell(cases['both_fail'])} "
            f"| {cell(cases['judge_only'])} | {cell(cases['hand_only'])} |"
        )
    return lines


def hand_table(outputs: dict) -> list[str]:
    lines = ["| Run | Passed by hand | Failed by hand |", "|---|---|---|"]
    for label in LABELS:
        failed = sorted(q for q, r in outputs[label].items() if not r.get("passed"))
        lines.append(f"| {label} | {len(outputs[label]) - len(failed)} of {len(outputs[label])} "
                     f"| {', '.join(failed) or 'none'} |")
    return lines


def main() -> None:
    evals = {label: load(f"eval_results_{label}.json") for label in LABELS}
    outputs = {label: load(f"pipeline_outputs_{label}.json") for label in LABELS}
    with open("test_questions.json", encoding="utf-8") as f:
        questions = {q["id"]: q for q in json.load(f)}

    report = [
        "## Local vs cloud",
        "",
        "Sources: eval_results_local.json, eval_results_cloud.json, pipeline_outputs_local.json, "
        "pipeline_outputs_cloud.json. Mean ± 2 × SE, SE = standard deviation / √n.",
        "",
        *metric_table(evals),
        "",
        *run_table(outputs),
        "",
        *refusal_table(outputs, questions),
        "",
        *hand_table(outputs),
        "",
        *judge_vs_hand(outputs, evals),
    ]
    text = "\n".join(report)
    print(text)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\nSaved to {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()