import os
from pathlib import Path

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5:4b-q4_K_M")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_API_KEY = os.getenv("EMBED_API_KEY", "ollama")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434/v1")


CHILD_CHUNK_SIZE = 400
CHILD_CHUNK_OVERLAP = 50
PARENT_MAX_CHARS = 2500
PARENT_OVERLAP = 200
PARENT_MIN_CHARS = 300
CHILD_CANDIDATES = 20
TOP_K = 4

DOCUMENT_DATES = {
    "company_handbook.pdf": "2026-01-15",
    "product_guide.pdf": "2026-01",
    "security_policy.pdf": "2025-01-15",
    "quarterly_report_q1_2026.pdf": "2026-04-14",
    "meeting_notes.pdf": "2026-01-15",
}

SYSTEM_PROMPT = """You answer questions about NovaTech's internal documents. Use only the context blocks below. Each block starts with a label showing its source file, pages and date.

How to answer:
1. Use ONLY facts from the context. If the context does not answer the question, reply exactly "I cannot find this information in the provided documents." and nothing else.
2. Keep the answer short: 2 to 5 sentences, or a short list if the question asks for several items. Leave out anything the question did not ask about.
3. Copy numbers, dates, names and qualifying words exactly as written, for example "in addition to", "year-over-year" or "effective immediately". Do not reword them.
4. Attach each fact only to the person, document, country or tier it belongs to in the context. Never combine facts from different blocks into a new statement.
5. Decisions: in meeting notes, a line starting with "Decision:" is final. If a decision changes a rule from an older document, state the decision first as the current rule, with the date from its block label, then mention the older rule. A proposal is only a proposal if no Decision line confirms it.
6. Conflicts: if two blocks give different values for the same fact, such as two different dates for the same event, you must say the documents disagree and give both values with their sources. Do not choose one.
7. Tables: first find the column for the tier named in the question, then find the row whose range contains the given value. Ignore cells marked "—".
8. Cite after each sentence or list item. Copy the file name and pages from the label of the block the fact came from, in this format: [file name, p. N]. Never cite a block you did not use. Do not invent section numbers.

Context:
{context}
"""

TEMPERATURE = 0.3
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "none")
MAX_TOKENS = 1024
TOKEN_LIMIT_PARAM = os.getenv("TOKEN_LIMIT_PARAM", "max_tokens")

DOCUMENTS_DIR = Path("documents")

EMBED_BATCH_SIZE = 32

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "corpus_v2"
PARENTS_FILE = "parents.json"

TEST_QUESTIONS_FILE = "test_questions.json"
OUTPUT_FILE = "pipeline_outputs.json"