import time
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pypdf import PdfReader
import chromadb
from chromadb.errors import NotFoundError
import config

# Extracting the text file name form the pdf's
def extract_documents(folder: Path = config.DOCUMENTS_DIR) -> list[dict]:
    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {folder.resolve()}")

    documents = []
    for pdf_path in pdf_files:
        reader = PdfReader(pdf_path)
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                print(f"WARNING: no text on {pdf_path.name} page {page_number}")
                continue
            pages.append({"page": page_number, "text": text})

        full_text = "\n".join(p["text"] for p in pages)
        documents.append({
            "source": pdf_path.name,
            "pages": pages,
            "text": full_text,
            "word_count": len(full_text.split()),
        })
    return documents

# chunking documents
def chunk_documents(documents: list[dict]) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        add_start_index=True,
    )

    chunks = []
    for doc in documents:
        page_ranges = []
        offset = 0
        for page in doc["pages"]:
            page_ranges.append({"page": page["page"], "start": offset})
            offset += len(page["text"]) + 1

        pieces = splitter.create_documents([doc["text"]])
        for chunk_index, piece in enumerate(pieces):
            start = piece.metadata["start_index"]

            page_number = page_ranges[0]["page"]
            for page_range in page_ranges:
                if page_range["start"] <= start:
                    page_number = page_range["page"]
                else:
                    break

            chunks.append({
                "id": f"{doc['source']}::c{chunk_index}",
                "text": piece.page_content,
                "metadata": {
                    "source": doc["source"],
                    "page": page_number,
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "char_count": len(piece.page_content),
                },
            })
    return chunks

# embedding the chunks
def embed_texts(texts: list[str]) -> list[list[float]]:
    client = OpenAI(base_url=config.EMBEDDING_BASE_URL, api_key=config.EMBEDDING_API_KEY)
    embeddings = []
    for start in range(0, len(texts), config.EMBED_BATCH_SIZE):
        batch = texts[start:start + config.EMBED_BATCH_SIZE]
        response = client.embeddings.create(model=config.EMBEDDING_MODEL, input=batch)
        embeddings.extend(item.embedding for item in response.data)
    return embeddings

# storing chunks
def store_chunks(chunks: list[dict], embeddings: list[list[float]]) -> chromadb.Collection:
    db = chromadb.PersistentClient(path=config.CHROMA_DIR)

    try:
        db.delete_collection(config.COLLECTION_NAME)
    except NotFoundError:
        pass

    collection = db.create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
        embeddings=embeddings,
    )
    return collection

def main() -> None:
    start = time.time()

    documents = extract_documents()
    for doc in documents:
        print(f"{doc['source']}: {len(doc['pages'])} pages, {doc['word_count']} words")

    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks (chunk size {config.CHUNK_SIZE} characters, "
          f"overlap {config.CHUNK_OVERLAP} characters)")

    embeddings = embed_texts([c["text"] for c in chunks])
    print(f"Embedded with {config.EMBEDDING_MODEL}: {len(embeddings[0])} dimensions")

    collection = store_chunks(chunks, embeddings)
    print(f"Stored {collection.count()} chunks in collection '{config.COLLECTION_NAME}'")
    print(f"Done in {time.time() - start:.1f} s")


if __name__ == "__main__":
    main()