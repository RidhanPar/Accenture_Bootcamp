# Local Document Q&A (Day 11 Capstone)

A retrieval-augmented generation (RAG) pipeline that answers questions about a set of internal company documents. Everything runs locally through Ollama, so no document content is sent to a cloud AI provider.

## Models

| Role | Model | Notes |
|---|---|---|
| LLM (final) | `qwen3.5:4b-q4_K_M` | Thinking turned off (`reasoning_effort="none"`) |
| Embeddings | `nomic-embed-text` | 768 dimensions |
| Comparison model | `qwen3.5:2b-q4_K_M` | Used in V1 and V2, see `benchmark_results.json` |

The reasons for these choices are in `decision_log.md`.

## Requirements

- Windows, macOS or Linux, with Ollama installed natively
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- About 5 GB of free RAM for the LLM and the embedding model

## Setup

1. Pull the models:
   ```bash
   ollama pull qwen3.5:4b-q4_K_M
   ollama pull qwen3.5:2b-q4_K_M
   ollama pull nomic-embed-text
   ```
2. Set the Ollama context window to 8192 tokens and restart Ollama.
   On Windows (PowerShell):
   ```powershell
   [Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH", "8192", "User")
   ```
   Check with `ollama ps` while a model is loaded. The CONTEXT column must show 8192.
3. Install the Python dependencies:
   ```bash
   uv sync
   ```
4. Check that the API works:
   ```bash
   uv run python test_api.py
   ```
   It should print one sentence followed by `stop`.

## How to Run

| Step | Command | Output |
|---|---|---|
| Model benchmark | `uv run python benchmark.py` | `benchmark_results.json` |
| Build the vector database | `uv run python ingest.py` | `chroma_db/` and `parents.json` |
| Run all test questions | `uv run python pipeline.py` | `pipeline_outputs.json` |
| Ask one question | `uv run python generate.py` | Answer printed as JSON |
| Inspect retrieval only | `uv run python retrieve.py` | Retrieved chunks printed as JSON |

`chroma_db/` and `parents.json` are not committed. Run `uv run python ingest.py` to rebuild them.

## Switching from Local to Cloud

All settings live in `config.py`. The LLM can be swapped through four environment variables, with no code changes. Embeddings stay local, so the same `chroma_db/` serves both runs.

```powershell
$env:LLM_BASE_URL = "https://<resource>.openai.azure.com/openai/v1/"
$env:LLM_API_KEY = $env:AZURE_OPENAI_API_KEY
$env:LLM_MODEL = "gpt-5.6-luna"
$env:TOKEN_LIMIT_PARAM = "max_completion_tokens"
```

## How the Pipeline Works

1. **Extraction:** `pypdf` with `extraction_mode="layout"`, so tables keep their columns. Empty list markers left by pypdf are removed.
2. **Chunking (parent-child):**
   - Parents are document sections, split at numbered headings and meeting headings. Sections under 300 characters are merged into the previous one, and sections over 2500 characters are split with 200 characters of overlap.
   - Children are 400-character chunks with 50 characters of overlap, each prefixed with its section heading.
   - Only children are embedded. Parents are stored in `parents.json`.
   - Each meeting section gets its own meeting date. Other sections get their document date.
3. **Retrieval:** search the top 20 children, map them to their parent sections, remove duplicates, and keep the top 4 sections.
4. **Generation:** the sections are passed to the LLM as context blocks, each labelled with its source, pages and date. The system prompt requires answers grounded in the context, treats "Decision:" lines in meeting notes as final, asks the model to report conflicting sources, and requires a citation after each sentence.

Chunk sizes are in characters, not tokens.

## Project Structure

```
local-rag/
├── config.py                  # All settings: models, chunking, retrieval, prompt
├── ingest.py                  # Extract, chunk, embed, store
├── retrieve.py                # Query children, return parent sections
├── generate.py                # Build context blocks, call the LLM
├── pipeline.py                # Run all test questions, write pipeline_outputs.json
├── benchmark.py               # Compare models on speed and quality
├── test_api.py                # Check that Ollama responds
├── test_questions.json        # 18 test questions with expected answers
├── benchmark_results.json     # Benchmark results with my ratings
├── pipeline_outputs_v1.json   # V1: fixed-size chunks, 2B model
├── pipeline_outputs_v2.json   # V2: parent-child chunks, 2B model
├── pipeline_outputs_v3.json      # V3 (final): parent-child chunks, 4B model, final prompt
├── decision_log.md            # My decisions and reasoning
└── documents/                 # The five source PDFs
```

## Results

| Version | Setup | Passed | Avg generation time |
|---|---|---|---|
| V1 | Fixed-size chunks (512 characters), 2B | 9/18 | ~27.8 s (one 23-minute outlier excluded) |
| V2 | Parent-child chunks, layout extraction, revised prompt, 2B | 12/18 | 34.8 s |
| V3 (final) | Same as V2, 4B, final prompt | 16/18 | 99.6 s |

A question passes when the core answer is correct and nothing in it contradicts the documents. V3 still fails q13 and q14, both questions where two documents give different information.

All numbers come from files written by the code:
- Model speed and quality: `benchmark_results.json`
- Answer quality per question: `pipeline_outputs_v1.json`, `pipeline_outputs_v2.json` and `pipeline_outputs_v3.json`

The `quality_rating`, `passed` and `rating_note` fields were filled in by hand after reading each answer. The analysis and the comparison between versions are in `decision_log.md`.

## AI Assistance

- **Tool:** Claude (Anthropic), model: Claude Opus 5.5
- **Used for:** generating parts of the code, drafting test questions (each one verified by me against the PDFs), comparing answers against expected answers to spot the main differences, and generating this README.
- **Not AI-generated:** `decision_log.md` was written by me. All ratings in the output files are my own judgement.
- The LLM inside the pipeline runs locally through Ollama. No cloud model is used for answering.