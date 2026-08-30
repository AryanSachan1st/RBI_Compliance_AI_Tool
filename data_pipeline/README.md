# data_pipeline

Offline tooling used to build the RBI/IRDAI regulatory corpus that the main
backend's RAG retrieval eventually queries. This is **not** imported by the
running FastAPI app — everything here is run by hand, once in a while, to
(re)produce a local Chroma collection. It was moved into this repo as one
self-contained unit; nothing was rewritten or re-split, so every script
still runs exactly as it did standalone (see "Why it's flat" below).

IRDAI documents are not done yet — everything below has only been run
against RBI so far.

## Actual pipeline (what was really used)

Automated discovery (`scraper.py` / `scraper2.py`) was tried and scrapped
as too time-consuming. The corpus was built manually from here on:

1. **Manually download PDFs** for whichever RBI Master Directions you want,
   and manually build/update `matched_directions.json` with one entry per
   document (`title`, `detail_page_url`, `pdf_url`, `matched_topics`).
   → `download.py` then fetches each `pdf_url` into `raw_pdfs/`, hashing
   the content into `raw_pdfs/{sha256}.pdf` and writing `local_path` +
   `sha256` back into `matched_directions.json` in place.
   → `check_pdf.py` / `inspect_bad_pdf.py` are debugging aids for when a
   downloaded "PDF" turns out to be an HTML error page or similar.

2. **PDF → Markdown**: `datalab_extractor.py` sends each file in
   `raw_pdfs/` through the Datalab API and writes converted Markdown into
   `extracted_pdf_contents/`. (`extractor.py`, a pdfplumber-based
   alternative, was written but not the path actually used — kept in case
   Datalab access ever goes away.)

3. **Markdown → structured JSON**: `structure_document.py` sends one `.md`
   file through an LLM with a JSON-schema-constrained response
   (`clause_schema.py`'s `ExtractedDocument`) and writes
   `structured_docs/{doc_id}.json` — a flat, ordered list of clauses/
   tables/annexures. `batch_runner.py` runs this over an entire folder of
   `.md` files and automatically applies step 4 after each one.
   `doc_id` here is whatever you choose when you name the `.md` file /
   invoke the script — there's no enforced link to `matched_directions.json`
   at this point, which is exactly why step 5 exists.

4. **Clean-up pass**: `merge_duplicate_clauses.py` fixes the specific
   failure mode where a table/annexure interrupts a clause's sub-items and
   the LLM splits it into two top-level items with the same
   `(chapter, clause_number)`. `validate_structured.py` is a separate,
   read-only sanity check for the same class of extraction problems —
   run it after structuring to eyeball item-type counts and catch
   obviously wrong output before it feeds into chunking.

5. **Manifest linking**: `automate_manifests.py` reads `doc_manifest.json`
   (see "Two manifests" below) and, matching by sorted filename order
   against `structured_docs/*.json`, writes `doc_id` and `local_path` back
   into each entry in place. This is order-dependent and manual — it
   assumes `doc_manifest.json`'s entries are already in the same order you
   structured the corresponding `.md` files in. Worth double-checking by
   hand after running it, not something to fully trust blind.

6. **Chunking**: `chunk_documents.py` reads every `structured_docs/*.json`
   plus `doc_manifest.json` (for titles/topics) and writes a single flat
   `chunks.jsonl` — one chunk per line, each with a citation string built
   from the manifest title + chapter + clause number. Short clauses (≤3
   sub-items) stay whole; long ones (e.g. Definitions) are split one
   sub-item per chunk. See the docstring in the script for the exact rule.

7. **Embedding + storage**: `embed_and_store.py` reads `chunks.jsonl`,
   embeds everything with `text-embedding-3-small`, and upserts into a
   local persistent Chroma collection named `rbi_irdai_clauses` at
   `./chroma_db`.

## Two manifests — don't confuse them

- **`matched_directions.json`** (committed, present in this folder) —
  produced by the scraper/manual-matching stage. Keyed by nothing in
  particular (a plain list); links a downloaded PDF's `sha256`/
  `local_path` to its scraped `title`, source URLs, and `matched_topics`.
  This is the manifest you'd extend if you add more PDFs later.

- **`doc_manifest.json`** (gitignored, **not included in this copy** —
  needs to be dropped back into this folder before running step 5/6/7
  above) — the manifest that actually drives chunking. It's the same
  shape as `matched_directions.json` plus `doc_id` (added by
  `automate_manifests.py` once documents are structured), and is what
  `chunk_documents.py` uses to attach a human-readable title/topics to
  every chunk's citation. Keep this one around after rebuilding — it's
  also what you'll want for manually fact-checking a clause's citation
  back to its source document.

## Data directories (gitignored, not shipped with this move)

None of these were included when this folder was moved into the backend
repo — drop them back in here before re-running anything downstream of
the step that produces them:

| Path                      | Produced by                                 | Consumed by                                                                                           |
| ------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `raw_pdfs/`               | `download.py`                               | `datalab_extractor.py`, `extractor.py`                                                                |
| `extracted_pdf_contents/` | `datalab_extractor.py`                      | `structure_document.py` (input path is passed manually per-file)                                      |
| `structured_docs/`        | `structure_document.py` / `batch_runner.py` | `merge_duplicate_clauses.py`, `validate_structured.py`, `automate_manifests.py`, `chunk_documents.py` |
| `doc_manifest.json`       | manual + `automate_manifests.py`            | `chunk_documents.py`                                                                                  |
| `chunks.jsonl`            | `chunk_documents.py`                        | `embed_and_store.py`                                                                                  |
| `chroma_db/`              | `embed_and_store.py`                        | not yet wired into the backend — see below                                                            |

## Why it's flat

Every script here uses cwd-relative paths (`Path("structured_docs")`,
`Path("chunks.jsonl")`, etc.) and flat sibling imports
(`batch_runner.py` does `from structure_document import ...`,
`structure_document.py` does `from clause_schema import ...`). Splitting
these into per-stage subfolders would require rewriting those paths and
imports — a behavior change. So this folder stays flat, and every command
below is run with `data_pipeline/` as the working directory:

```bash
cd data_pipeline
python download.py
python datalab_extractor.py
python structure_document.py <doc_id> path/to/document.md
# or, for a whole folder of already-converted markdown:
python batch_runner.py path/to/md_folder/
python validate_structured.py structured_docs/<doc_id>.json
python automate_manifests.py
python chunk_documents.py
python embed_and_store.py
```

This folder has its own `pyproject.toml` / `uv.lock` (deps like
`datalab-python-sdk`, `pdfplumber`, `beautifulsoup4` that the running
backend server doesn't need). Run it in its own environment
(`uv sync` from inside `data_pipeline/`), separate from the backend's own
`requirements.txt`.

## Not yet wired into the backend

The FastAPI app's own ingestion (`services/rbi_ingestion_service.py` +
`services/text_preprocessing.py`) is currently a separate, much simpler
placeholder: it chunks one dummy PDF naively and stores it at
`storage/vector_db` under collections `rbi_source_documents` /
`user_documents` — a different Chroma path and different collection name
than what `embed_and_store.py` produces here (`data_pipeline/chroma_db`,
collection `rbi_irdai_clauses`). Pointing the backend's retrieval at the
real corpus this pipeline produces is a separate task, not done as part
of this move.
