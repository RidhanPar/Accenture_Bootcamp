import json
import re
import time
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pypdf import PdfReader

import config

HEADING = re.compile(r"^(?:\d{1,2}(?:\.\d{1,2})*\.?\s+[A-Z][^.]{2,45}|Meeting \d+:.{3,100})$")
JUNK_LINE = re.compile(r"^\s*(?:\d+\.|•)?\s*$")
MEETING_DATE = re.compile(r"^Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})")
WIDE_SPACES = re.compile(r" {4,}")


# removing empty list markers and extra spaces left by pypdf
def clean_page(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if JUNK_LINE.match(line):
            if lines and lines[-1] != "":
                lines.append("")
            continue
        lines.append(WIDE_SPACES.sub("   ", line.rstrip()))
    return "\n".join(lines).strip()


# extracting text page by page with layout mode, so tables keep their columns
def extract_documents(folder: Path = config.DOCUMENTS_DIR) -> list[dict]:
    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {folder.resolve()}")

    documents = []
    for pdf_path in pdf_files:
        reader = PdfReader(pdf_path)
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = clean_page(page.extract_text(extraction_mode="layout") or "")
            if not text:
                print(f"WARNING: no text on {pdf_path.name} page {page_number}")
                continue
            pages.append({"page": page_number, "text": text})

        full_text = ""
        page_starts = []
        for page in pages:
            page_starts.append((len(full_text), page["page"]))
            full_text += page["text"] + "\n\n"

        documents.append({
            "source": pdf_path.name,
            "text": full_text,
            "page_starts": page_starts,
            "word_count": len(full_text.split()),
        })
    return documents


def page_at(page_starts: list[tuple[int, int]], position: int) -> int:
    page_number = page_starts[0][1]
    for start, number in page_starts:
        if start <= position:
            page_number = number
        else:
            break
    return page_number


# splitting each document into sections at its headings (parents)
def split_sections(doc: dict) -> list[dict]:
    sections = []
    current = {"heading": "Introduction", "start": 0}
    position = 0
    for line in doc["text"].splitlines(keepends=True):
        if HEADING.match(line.rstrip("\n")) and position > current["start"]:
            current["text"] = doc["text"][current["start"]:position]
            sections.append(current)
            current = {"heading": line.strip(), "start": position}
        position += len(line)
    current["text"] = doc["text"][current["start"]:]
    sections.append(current)

    merged = []
    for section in sections:
        if merged and len(merged[-1]["text"].strip()) < config.PARENT_MIN_CHARS:
            merged[-1]["text"] += section["text"]
        else:
            merged.append(section)
    return [s for s in merged if s["text"].strip()]


# building parents (sections) and children (small chunks searched by the vector DB)
def build_parents_and_children(documents: list[dict]) -> tuple[dict, list[dict]]:
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.PARENT_MAX_CHARS,
        chunk_overlap=config.PARENT_OVERLAP,
        add_start_index=True,
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHILD_CHUNK_SIZE,
        chunk_overlap=config.CHILD_CHUNK_OVERLAP,
        add_start_index=True,
    )

    parents = {}
    children = []
    for doc in documents:
        doc_date = config.DOCUMENT_DATES.get(doc["source"], "unknown")
        parent_index = 0
        for section in split_sections(doc):
            for line in section["text"].splitlines():
                found = MEETING_DATE.match(line.strip())
                if found:
                    doc_date = datetime.strptime(found.group(1), "%B %d, %Y").strftime("%Y-%m-%d")

            parts = parent_splitter.create_documents([section["text"]])
            for part_number, part in enumerate(parts):
                text = part.page_content
                if part_number > 0:
                    text = f"{section['heading']} (continued)\n{text}"
                parent_start = section["start"] + part.metadata["start_index"]
                parent_id = f"{doc['source']}::s{parent_index}"
                parents[parent_id] = {
                    "source": doc["source"],
                    "heading": section["heading"],
                    "date": doc_date,
                    "page_start": page_at(doc["page_starts"], parent_start),
                    "page_end": page_at(doc["page_starts"], parent_start + len(part.page_content) - 1),
                    "text": text,
                }

                for child_number, child in enumerate(child_splitter.create_documents([part.page_content])):
                    child_start = parent_start + child.metadata["start_index"]
                    children.append({
                        "id": f"{parent_id}::c{child_number}",
                        "text": f"{section['heading']}\n{child.page_content}",
                        "metadata": {
                            "source": doc["source"],
                            "page": page_at(doc["page_starts"], child_start),
                            "parent_id": parent_id,
                            "char_count": len(child.page_content),
                        },
                    })
                parent_index += 1
    return parents, children


# embedding the children
def embed_texts(texts: list[str]) -> list[list[float]]:
    client = OpenAI(base_url=config.EMBEDDING_BASE_URL, api_key=config.EMBEDDING_API_KEY)
    embeddings = []
    for start in range(0, len(texts), config.EMBED_BATCH_SIZE):
        batch = texts[start:start + config.EMBED_BATCH_SIZE]
        response = client.embeddings.create(model=config.EMBEDDING_MODEL, input=batch)
        embeddings.extend(item.embedding for item in response.data)
    return embeddings


# storing children in Chroma; parents go to parents.json
def store_children(children: list[dict], embeddings: list[list[float]]) -> chromadb.Collection:
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
        ids=[c["id"] for c in children],
        documents=[c["text"] for c in children],
        metadatas=[c["metadata"] for c in children],
        embeddings=embeddings,
    )
    return collection


def main() -> None:
    start = time.time()

    documents = extract_documents()
    for doc in documents:
        print(f"{doc['source']}: {len(doc['page_starts'])} pages, {doc['word_count']} words")

    parents, children = build_parents_and_children(documents)
    sizes = [len(p["text"]) for p in parents.values()]
    print(f"Created {len(parents)} parents (max {config.PARENT_MAX_CHARS} characters, "
          f"average {sum(sizes) // len(sizes)} characters)")
    print(f"Created {len(children)} children (chunk size {config.CHILD_CHUNK_SIZE} characters, "
          f"overlap {config.CHILD_CHUNK_OVERLAP} characters)")

    with open(config.PARENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(parents, f, indent=2, ensure_ascii=False)

    embeddings = embed_texts([c["text"] for c in children])
    print(f"Embedded with {config.EMBEDDING_MODEL}: {len(embeddings[0])} dimensions")

    collection = store_children(children, embeddings)
    print(f"Stored {collection.count()} children in '{config.COLLECTION_NAME}', "
          f"parents in {config.PARENTS_FILE}")
    print(f"Done in {time.time() - start:.1f} s")


if __name__ == "__main__":
    main()