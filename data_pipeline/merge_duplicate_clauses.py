"""
Safety net: merges items that ended up with a duplicate (chapter, clause_number) pair --
this happens when a table/annexure interrupts a clause's sub-items and the model
incorrectly splits it into two top-level items instead of one. Run this on every
structured_docs/{doc_id}.json right after extraction, before it's considered final.

Usage:
    python merge_duplicate_clauses.py structured_docs/sample2.json
(overwrites the file in place after printing what it merged; back up first if unsure)
"""

import json
import sys


def merge_duplicates(items: list[dict]) -> list[dict]:
    merged = []
    seen_at = {}  # (chapter, clause_number) -> index in `merged`

    for item in items:
        if item["item_type"] != "clause" or not item["clause_number"]:
            merged.append(item)
            continue

        key = (item["chapter"], item["clause_number"])
        if key in seen_at:
            target = merged[seen_at[key]]
            print(
                f"Merging duplicate clause {key}: "
                f"appending {len(item['sub_items'])} sub_item(s) into existing entry"
            )
            # keep the first non-empty chapeau_text, append all sub_items in order
            if not target["chapeau_text"].strip() and item["chapeau_text"].strip():
                target["chapeau_text"] = item["chapeau_text"]
            target["sub_items"].extend(item["sub_items"])
        else:
            seen_at[key] = len(merged)
            merged.append(item)

    return merged


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python merge_duplicate_clauses.py structured_docs/{doc_id}.json")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    before = len(data["items"])
    data["items"] = merge_duplicates(data["items"])
    after = len(data["items"])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n{before} items -> {after} items after merging.")
