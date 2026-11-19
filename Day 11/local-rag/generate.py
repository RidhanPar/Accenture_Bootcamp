import time

from openai import OpenAI

import config


def build_context_blocks(chunks: list[dict]) -> list[str]:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        first, last = chunk.get("page_range") or (chunk.get("page"), chunk.get("page"))
        pages = f"p. {first}" if first == last else f"pp. {first}-{last}"
        blocks.append(
            f"--- Context {i} | {chunk['source']} | {pages} | dated {chunk.get('date', 'unknown')} ---\n"
            f"{chunk['content'].strip()}"
        )
    return blocks


def generate_answer(query: str, chunks: list[dict]) -> dict:
    client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)
    context_blocks = build_context_blocks(chunks)
    context = "\n\n".join(context_blocks)

    start = time.time()
    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": config.SYSTEM_PROMPT.format(context=context)},
            {"role": "user", "content": query},
        ],
        temperature=float(config.TEMPERATURE),
        reasoning_effort=config.REASONING_EFFORT,
        **{config.TOKEN_LIMIT_PARAM: config.MAX_TOKENS},
    )
    elapsed_ms = round((time.time() - start) * 1000)

    choice = response.choices[0]
    answer = choice.message.content or ""
    usage = response.usage

    if not answer.strip():
        print(f"WARNING: empty answer for '{query}' | finish_reason={choice.finish_reason}")

    return {
        "query": query,
        "answer": answer,
        "context_used": context_blocks,
        "model": config.LLM_MODEL,
        "thinking": config.REASONING_EFFORT != "none",
        "finish_reason": choice.finish_reason,
        "generation_time_ms": elapsed_ms,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "tokens_generated": usage.completion_tokens if usage else None,
    }


if __name__ == "__main__":
    import json
    from retrieve import retrieve_chunks

    question = input("Question: ")
    retrieval = retrieve_chunks(question)
    result = generate_answer(question, retrieval["retrieved_chunks"])
    print(json.dumps(result, indent=2, ensure_ascii=False))