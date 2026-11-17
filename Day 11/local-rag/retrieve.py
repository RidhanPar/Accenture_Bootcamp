import time

import chromadb
from openai import OpenAI

import config

_collection = None


def get_collection():
    global _collection
    if _collection is None:
        db = chromadb.PersistentClient(path=config.CHROMA_DIR)
        _collection = db.get_collection(config.COLLECTION_NAME)
    return _collection


def embed_query(query: str) -> list[float]:
    client = OpenAI(base_url=config.EMBEDDING_BASE_URL, api_key=config.EMBEDDING_API_KEY)
    response = client.embeddings.create(model=config.EMBEDDING_MODEL, input=[query])
    return response.data[0].embedding


def retrieve_chunks(query: str, top_k: int = config.TOP_K) -> dict:
    start = time.time()
    query_embedding = embed_query(query)

    result = get_collection().query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved_chunks = []
    for chunk_id, text, meta, distance in zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        retrieved_chunks.append({
            "chunk_id": chunk_id,
            "content": text,
            "source": meta["source"],
            "page": meta["page"],
            "relevance_score": round(1 - distance, 4),
        })

    return {
        "query": query,
        "retrieved_chunks": retrieved_chunks,
        "top_k": top_k,
        "retrieval_time_ms": round((time.time() - start) * 1000),
        "embedding_model": config.EMBEDDING_MODEL,
    }


if __name__ == "__main__":
    import json
    question = input("Question: ")
    print(json.dumps(retrieve_chunks(question), indent=2, ensure_ascii=False))