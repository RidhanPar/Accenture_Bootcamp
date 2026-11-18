# Local Document Q&A (Day 11 Capstone)

A retrieval-augmented generation (RAG) pipeline that answers questions about a set of internal company documents. Everything runs locally through Ollama, so no document content is sent to a cloud AI provider.

## Models

| Role | Model | Notes |
|---|---|---|
| LLM | `qwen3.5:2b-q4_K_M` | Thinking turned off (`reasoning_effort="none"`) |
| Embeddings | `nomic-embed-text` | 768 dimensions |
| Comparison model (benchmark) | `qwen3.5:4b-q4_K_M` | See `benchmark_results.json` |

The reasons for these choices are in `decision_log.md`.

## Requirements

- Windows, macOS or Linux, with Ollama installed natively
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- About 4 GB of free RAM for the LLM and embedding model

## Setup

1. Pull the models:
   ```bash
   ollama pull qwen3.5:2b-q4_K_M
   ollama pull qwen3.5:4b-q4_K_M
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
   - Parents are document sections, split at headings, capped at 2500 characters.
   - Children are 400-character chunks with 50 characters of overlap, prefixed with their section heading.
   - Only children are embedded. Parents are stored in `parents.json`.
3. **Retrieval:** search the top 20 children, map them to their parent sections, remove duplicates, and keep the top 4 sections.
4. **Generation:** the sections are passed to the LLM as context, each labelled with its source, pages and document date. The system prompt requires answers grounded in the context, separates proposals from decisions, and asks the model to report conflicting sources.

Chunk sizes are in characters, not tokens.

## Project Structure

```
local-rag/
├── config.py                  # All settings: models, chunking, retrieval, prompt
├── ingest.py                  # Extract, chunk, embed, store
├── retrieve.py                # Query children, return parent sections
├── generate.py                # Build context, call the LLM
├── pipeline.py                # Run all test questions, write pipeline_outputs.json
├── benchmark.py               # Compare models on speed and quality
├── test_api.py                # Check that Ollama responds
├── test_questions.json        # 18 test questions with expected answers
├── benchmark_results.json     # Benchmark results with my ratings
├── pipeline_outputs_v1.json   # V1 run (fixed-size chunks), kept for comparison
├── pipeline_outputs.json      # V2 run (parent-child), evaluated on Day 12
├── decision_log.md            # My decisions and reasoning
└── documents/                 # The five source PDFs
```

## Results

All numbers come from files written by the code:
- Model speed and quality: `benchmark_results.json`
- Answer quality per question: `pipeline_outputs.json` (V2) and `pipeline_outputs_v1.json` (V1)

The `quality_rating`, `passed` and `rating_note` fields were filled in by hand after reading each answer. The analysis and V1 vs V2 comparison are in `decision_log.md`.

## AI Assistance

- **Tool:** Claude (Anthropic), model: [model name]
- **Used for:** generating parts of the code, drafting test questions (each one verified by me against the PDFs), comparing answers against expected answers to spot the main differences, and generating this README.
- **Not AI-generated:** `decision_log.md` was written by me. All ratings in the output files are my own judgement.
- The LLM inside the pipeline runs locally through Ollama. No cloud model is used for answering.