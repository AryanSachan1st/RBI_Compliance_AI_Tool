"""
Reads every structured_docs/{doc_id}.json and produces a single flat
chunks.jsonl file -- one JSON object per line, ready to feed into an
embedding step. No vector DB yet; this is just getting clean, chunked,
citable text ready to go.

Chunking rule (pragmatic, not perfect -- good enough for a one-time job):
- Clauses with <= 3 sub_items: keep the WHOLE clause as one chunk
  (sub-items likely depend on shared context/chapeau).
- Clauses with > 3 sub_items (e.g. Definitions): split into ONE CHUNK
  PER SUB-ITEM, each carrying the clause's chapeau + citation as context,
  so it's independently meaningful and better for retrieval precision.
- Tables/annexures: one chunk each, tagged so you can decide later
  whether to even embed them.

Usage:
    python chunk_documents.py
(reads everything in structured_docs/, writes chunks.jsonl)
"""

import json
from pathlib import Path

STRUCTURED_DIR = Path("structured_docs")
OUTPUT_FILE = Path("chunks.jsonl")
MANIFEST_FILE = Path("doc_manifest.json")
SUB_ITEM_SPLIT_THRESHOLD = (
    3  # clauses with MORE sub_items than this get split per sub-item
)


def load_manifest() -> dict:
    """
    Reads doc_manifest.json, which is a LIST of entries like:
    {"title": "...", "doc_id": "sample1", "matched_topics": [...], ...}
    (this is the same format your scraper originally produced, extended with doc_id).
    Converts it into a dict keyed by doc_id for fast lookup: {doc_id: {"title":..., "topics":...}}
    """
    if not MANIFEST_FILE.exists():
        print(
            f"WARNING: {MANIFEST_FILE} not found -- citations will use raw doc_id only."
        )
        return {}

    with open(MANIFEST_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    manifest = {}
    for entry in raw:
        doc_id = entry.get("doc_id")
        if not doc_id:
            continue  # skip malformed/incomplete entries rather than crashing
        manifest[doc_id] = {
            "title": entry.get("title", doc_id),
            "topics": entry.get("matched_topics", []),
        }
    return manifest


def make_citation(
    doc_title: str, chapter: str, clause_number: str, heading: str, sub_ref: str = ""
) -> str:
    parts = [doc_title]
    if chapter:
        parts.append(chapter)
    label = f"Clause {clause_number}"
    if sub_ref:
        label += f"({sub_ref})"
    if heading:
        label += f" - {heading}"
    parts.append(label)
    return " | ".join(parts)


def render_sub_item(sub: dict) -> str:
    text = f"({sub['ref']}) {sub['text']}"
    for subsub in sub.get("sub_items", []):
        text += f"\n    ({subsub['ref']}) {subsub['text']}"
    return text


def chunk_clause_item(
    doc_id: str, doc_title: str, topics: list, item_index: int, item: dict
) -> list[dict]:
    chapter = item["chapter"]
    clause_number = item["clause_number"]
    heading = item["heading"]
    chapeau = item["chapeau_text"]
    sub_items = item["sub_items"]

    if item["item_type"] in ("table", "annexure_form"):
        return [
            {
                "chunk_id": f"{doc_id}::i{item_index:04d}::{item['item_type']}",
                "doc_id": doc_id,
                "topics": topics,
                "item_type": item["item_type"],
                "citation": make_citation(doc_title, chapter, clause_number, heading),
                "text": chapeau,
            }
        ]

    if len(sub_items) <= SUB_ITEM_SPLIT_THRESHOLD:
        # whole clause as one chunk
        parts = [chapeau] + [render_sub_item(s) for s in sub_items]
        full_text = "\n".join(p for p in parts if p)
        citation = make_citation(doc_title, chapter, clause_number, heading)
        return [
            {
                "chunk_id": f"{doc_id}::i{item_index:04d}",
                "doc_id": doc_id,
                "topics": topics,
                "item_type": "clause",
                "citation": citation,
                "text": f"[{citation}]\n{full_text}",
            }
        ]
    else:
        # one chunk per sub-item, each carrying the chapeau as shared context
        chunks = []
        for sub_pos, sub in enumerate(sub_items):
            citation = make_citation(
                doc_title, chapter, clause_number, heading, sub["ref"]
            )
            text = f"[{citation}]\n{chapeau}\n{render_sub_item(sub)}"
            chunks.append(
                {
                    "chunk_id": f"{doc_id}::i{item_index:04d}::s{sub_pos:03d}",
                    "doc_id": doc_id,
                    "topics": topics,
                    "item_type": "clause",
                    "citation": citation,
                    "text": text,
                }
            )
        return chunks


def main():
    manifest = load_manifest()
    all_chunks = []
    doc_files = sorted(STRUCTURED_DIR.glob("*.json"))
    print(f"Found {len(doc_files)} structured documents.")

    for doc_path in doc_files:
        with open(doc_path, encoding="utf-8") as f:
            data = json.load(f)
        doc_id = data["doc_id"]
        manifest_entry = manifest.get(doc_id, {})
        doc_title = manifest_entry.get("title", doc_id)  # fallback to doc_id if missing
        topics = manifest_entry.get("topics", [])

        doc_chunks = []
        for item_index, item in enumerate(data["items"]):
            doc_chunks.extend(
                chunk_clause_item(doc_id, doc_title, topics, item_index, item)
            )

        # belt-and-suspenders: verify uniqueness before writing anything out
        ids_in_doc = [c["chunk_id"] for c in doc_chunks]
        assert len(ids_in_doc) == len(set(ids_in_doc)), (
            f"Duplicate chunk_id within {doc_id}!"
        )

        print(f"{doc_id}: {len(data['items'])} items -> {len(doc_chunks)} chunks")
        all_chunks.extend(doc_chunks)

    # global uniqueness check across the whole corpus, not just per-document
    all_ids = [c["chunk_id"] for c in all_chunks]
    assert len(all_ids) == len(set(all_ids)), (
        "Duplicate chunk_id found across documents!"
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(
            json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in all_chunks
        )

    print(f"\nTotal chunks: {len(all_chunks)} -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
