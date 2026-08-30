"""
Reads a datalab-converted markdown file for one RBI/IRDAI document,
sends it to a GPT model with a JSON-schema-constrained request (OpenAI
Structured Outputs via response_format), and saves the structured result
to structured_docs/{doc_id}.json.

This ties into schema.py's RegulatoryDocument by doc_id -- run this AFTER
you've registered the document (Step 1.1/1.7), so doc_id here matches the
doc_id already sitting in your registry.

Usage:
    python structure_document.py <doc_id> path/to/document.md
"""

import json
import os
import sys
from datetime import date
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from clause_schema import ExtractedDocument

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


MODEL = "gpt-5.6-luna"  # cheap tier -- escalate to "gpt-5.6-terra" if quality is poor
OUTPUT_DIR = Path("structured_docs")
OUTPUT_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT = """You are structuring an official RBI/IRDAI regulatory document that has \
already been converted from PDF to Markdown. The markdown headings (#, ##, ###) reflect the \
document's real structure (Chapters, Sections). Tables have been converted to markdown tables.

Your job: extract every clause, paragraph, and table into a flat ordered list of items.

Rules:
1. Each numbered clause (e.g. "4. Definitions") is ONE item. Put any lead-in text before its \
   lettered sub-items into `chapeau_text`. If it has lettered sub-items like (a), (b), (c), \
   put each one as a separate entry in `sub_items`, with just that sub-item's own text (not \
   the chapeau, not other sub-items). If a sub-item itself breaks down further into (i), (ii), \
   put those in that sub-item's own `sub_items` list. If a clause has NO lettered sub-items at \
   all, put its entire text in `chapeau_text` and leave `sub_items` empty.
2. Markdown tables (rows of | col | col |) should become a single item with item_type="table", \
   with the raw markdown table content in `chapeau_text` and no sub_items.
3. Any Annexure, Format, or Schedule (usually a fillable form or table at the end of the \
   document) should be item_type="annexure_form", with its content in `chapeau_text`.
4. Chapter/Part headings on their own (no numbered content) can be item_type="chapter_heading" \
   with the heading text captured, OR you can just populate the `chapter` field on the \
   following clauses -- prefer the latter (skip creating separate chapter_heading items) unless \
   there is meaningful content attached directly to the heading itself.
5. Preserve document order.
6. Do not summarize, shorten, or paraphrase clause text -- reproduce it faithfully as it \
   appears in the markdown (formatting/whitespace normalization is fine).
7. IMPORTANT -- a table or annexure reference sometimes appears IN THE MIDDLE of a clause's \
   sub-items (e.g. clause 16(1) text, then a table, then clause 16(2) continues the SAME \
   clause 16). When this happens: (a) extract the table as its own separate item with \
   item_type="table" positioned between the sub-items in your output order, AND (b) still \
   place both sub-items (1) and (2) under the SAME clause item with clause_number="16" -- \
   do NOT create two separate items that both have clause_number="16". A clause_number must \
   never repeat across two different items in the same chapter.
"""


def structure_document(md_path: str) -> dict:
    text = Path(md_path).read_text(encoding="utf-8")

    client = OpenAI(api_key=OPENAI_API_KEY)  # reads OPENAI_API_KEY from env

    response = client.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Structure this document:\n\n{text}"},
        ],
        response_format=ExtractedDocument,
        max_completion_tokens=32000,  # raised -- 16000 was consumed entirely by reasoning
        reasoning_effort="low",  # this is extraction, not deep reasoning -- don't waste budget
    )

    message = response.choices[0].message
    if message.refusal:
        raise RuntimeError(f"Model refused: {message.refusal}")

    parsed: ExtractedDocument = message.parsed
    return parsed.model_dump()


def json_safe(obj):
    """Encoder helper for Enum and date fields from your RegulatoryDocument schema,
    in case you serialize the registry entry alongside the extracted items."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Not JSON serializable: {type(obj)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python structure_document.py <doc_id> path/to/document.md")
        sys.exit(1)

    doc_id = sys.argv[1]
    md_path = Path(sys.argv[2])

    result = structure_document(str(md_path))
    result["doc_id"] = doc_id
    result["source_md_file"] = str(md_path)
    result["extraction_model"] = MODEL

    out_path = OUTPUT_DIR / f"{doc_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=json_safe)

    print(f"Extracted {len(result['items'])} items -> {out_path}")

    from collections import Counter

    type_counts = Counter(item["item_type"] for item in result["items"])
    print("Item type breakdown:", dict(type_counts))
