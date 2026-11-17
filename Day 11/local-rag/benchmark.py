import json
import time
from openai import OpenAI

MODELS = ["qwen3.5:4b-q4_K_M", "qwen3.5:2b-q4_K_M"]
BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
REASONING_EFFORT = "none"

PROMPTS = [
    {"category": "factual",
     "prompt": "What causes tides on Earth? Answer in 2-3 sentences."},

    {"category": "reasoning",
     "prompt": "If a train travels 120km in 1.5 hours, and then 80km in 1 hour, what is the average speed for the entire journey? Show your working."},

    {"category": "summarization",
     "prompt": (
         "Summarize the following paragraph in one sentence:\n\n"
         "Employees may work from home up to three days per week, provided their manager "
         "approves a written schedule at the start of each quarter. Remote days cannot be "
         "carried over to the next week. Staff working remotely must use a company laptop "
         "and connect through the corporate VPN at all times. Any security incident on a "
         "remote day must be reported to the IT helpdesk within one hour."
     )},

    {"category": "structured",
     "prompt": 'List 3 European capitals. Respond ONLY with valid JSON: [{"city": ..., "country": ...}]'},

    {"category": "code",
     "prompt": "Write a Python function `average(numbers)` that returns the mean of a list of numbers and returns 0.0 for an empty list. Return only the code."},

    {"category": "instruction_following",
     "prompt": "Give exactly 3 tips for writing a good email. Rules: use bullet points, start each bullet with a verb, keep each bullet under 10 words, and write nothing before or after the bullets."},

    {"category": "rag_grounded",
     "prompt": (
         "Use ONLY the context to answer. If the answer is not in the context, say "
         "\"I cannot find this information in the provided documents.\"\n\n"
         "Context: Customers can return hardware within 30 days of purchase with a receipt. "
         "Software licences are non-refundable once activated.\n\n"
         "Question: How long do customers have to return hardware?"
     )},

    {"category": "rag_unanswerable",
     "prompt": (
         "Use ONLY the context to answer. If the answer is not in the context, say "
         "\"I cannot find this information in the provided documents.\"\n\n"
         "Context: Customers can return hardware within 30 days of purchase with a receipt. "
         "Software licences are non-refundable once activated.\n\n"
         "Question: How long is the hardware warranty?"
     )},
]

def run_benchmark(model: str, prompt_item: dict) -> dict:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_item["prompt"]}],
        temperature=0.7,
        reasoning_effort=REASONING_EFFORT,
        max_tokens=1024,
    )
    elapsed = time.time() - start
    choice = response.choices[0]
    usage = response.usage

    return {
        "model": model,
        "category": prompt_item["category"],
        "prompt": prompt_item["prompt"],
        "response": choice.message.content,
        "thinking": REASONING_EFFORT != "none",
        "finish_reason": choice.finish_reason,
        "time_seconds": round(elapsed, 2),
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "tokens_per_second": round(usage.completion_tokens / elapsed, 1) if usage and usage.completion_tokens else None,
        "quality_rating": None,
        "rating_note": "",
    }

# TODO: loop over MODELS and PROMPTS, collect results, write benchmark_results.json
# with open("benchmark_results.json", "w", encoding="utf-8").
# Print a visible warning when a response is empty.

benchmark_resutls = []
for model in MODELS:
    print(f"{model} is running its itteration")
    for prompt in PROMPTS:
        result = run_benchmark(model,prompt)
        if result["response"] in [None,""]:
            print(f"This prompt category [{prompt["category"]}] under [{model}] provided a empty ouput and finish reason is [{result["finish_reason"]}]")
        benchmark_resutls.append(result)

with open("benchmark_results.json", "w", encoding="utf-8") as f:
    json.dump(benchmark_resutls, f, indent=2, ensure_ascii=False)

