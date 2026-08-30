"""
Runs structure_document.py's logic over every .md file in a folder,
using the filename (minus extension) as doc_id, and auto-applies the
duplicate-clause merge safety net right after each extraction.

Usage:
    python batch_structure.py path/to/md_folder/
"""

import json
import sys
from pathlib import Path

from merge_duplicate_clauses import merge_duplicates
from structure_document import json_safe, structure_document

OUTPUT_DIR = Path("structured_docs")
OUTPUT_DIR.mkdir(exist_ok=True)


def main(md_folder: str):
    md_files = sorted(Path(md_folder).glob("*.md"))
    print(f"Found {len(md_files)} markdown files.\n")

    for md_path in md_files:
        doc_id = md_path.stem
        out_path = OUTPUT_DIR / f"{doc_id}.json"

        if out_path.exists():
            print(f"SKIP (already exists): {doc_id}")
            continue

        print(f"Processing: {doc_id} ...")
        try:
            result = structure_document(md_path)
        except Exception as e:
            print(f"  FAILED: {e}\n")
            continue

        result["doc_id"] = doc_id
        result["source_md_file"] = str(md_path)
        result["extraction_model"] = "gpt-5.6-luna"

        # apply the merge safety net immediately
        before = len(result["items"])
        result["items"] = merge_duplicates(result["items"])
        after = len(result["items"])
        if before != after:
            print(f"  merged {before - after} duplicate clause split(s)")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=json_safe)

        print(f"  -> {after} items saved to {out_path}\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python batch_structure.py path/to/md_folder/")
        sys.exit(1)
    main(sys.argv[1])
