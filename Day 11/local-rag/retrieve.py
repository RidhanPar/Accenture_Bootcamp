import json
import time

import chromadb
from openai import OpenAI

import config

_collection = None
_parents = None


def get_collection():
    global _collection
    if _collection is None:
        db = chromadb.PersistentClient(path=config.CHROMA_DIR)
        _collection = db.get_collection(config.COLLECTION_NAME)
    return _collection


def get_parents() -> dict:
    global _parents
    if _parents is None:
        with open(config.PARENTS_FILE, encoding="utf-8") as f:
            _parents = json.load(f)
    return _parents


def embed_query(query: str) -> list[float]:
    client = OpenAI(base_url=config.EMBEDDING_BASE_URL, api_key=config.EMBEDDING_API_KEY)
    response = client.embeddings.create(model=config.EMBEDDING_MODEL, input=[query])
    return response.data[0].embedding


def retrieve_chunks(query: str, top_k: int = config.TOP_K) -> dict:
    start = time.time()
    result = get_collection().query(
        query_embeddings=[embed_query(query)],
        n_results=config.CHILD_CANDIDATES,
        include=["documents", "metadatas", "distances"],
    )

    parents = get_parents()
    retrieved_chunks = []
    seen = set()
    for child_id, child_text, meta, distance in zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        parent_id = meta["parent_id"]
        if parent_id in seen:
            continue
        seen.add(parent_id)
        parent = parents[parent_id]
        retrieved_chunks.append({
            "chunk_id": parent_id,
            "content": parent["text"],
            "source": parent["source"],
            "page": meta["page"],
            "page_range": [parent["page_start"], parent["page_end"]],
            "section": parent["heading"],
            "date": parent["date"],
            "relevance_score": round(1 - distance, 4),
            "matched_child_id": child_id,
            "matched_child": child_text,
        })
        if len(retrieved_chunks) == top_k:
            break

    return {
        "query": query,
        "retrieved_chunks": retrieved_chunks,
        "top_k": top_k,
        "child_candidates": config.CHILD_CANDIDATES,
        "retrieval_time_ms": round((time.time() - start) * 1000),
        "embedding_model": config.EMBEDDING_MODEL,
    }


if __name__ == "__main__":
    question = input("Question: ")
    print(json.dumps(retrieve_chunks(question), indent=2, ensure_ascii=False))