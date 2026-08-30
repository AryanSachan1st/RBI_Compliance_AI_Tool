"""
Sanity-checks a structured_docs/{doc_id}.json output for common failure patterns
we've already seen with regex-based extraction, to confirm the LLM-based approach
actually avoids them.

Usage:
    python validate_structured.py structured_docs/RBI-MD-OMBUDSMAN-2023.json
"""

import json
import sys
from collections import Counter
from pathlib import Path


def validate(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    items = data["items"]
    print(f"Total items: {len(items)}")

    type_counts = Counter(item["item_type"] for item in items)
    print(f"Item types: {dict(type_counts)}\n")

    # 1. Duplicate clause numbers within the same chapter (the old regex's worst bug)
    seen = {}
    dupes = []
    for i, item in enumerate(items):
        if item["item_type"] != "clause" or not item["clause_number"]:
            continue
        key = (item["chapter"], item["clause_number"])
        if key in seen:
            dupes.append((key, seen[key], i))
        else:
            seen[key] = i
    if dupes:
        print(f"WARNING: {len(dupes)} duplicate (chapter, clause_number) pairs found:")
        for key, first_idx, dup_idx in dupes:
            print(f"  {key} appears at items[{first_idx}] and items[{dup_idx}]")
    else:
        print("OK: no duplicate clause numbers within any chapter.")

    # 2. Empty clauses (no chapeau_text AND no sub_items -- likely extraction failure)
    empty = [
        i
        for i, item in enumerate(items)
        if item["item_type"] == "clause"
        and not item["chapeau_text"].strip()
        and not item["sub_items"]
    ]
    if empty:
        print(
            f"\nWARNING: {len(empty)} clauses have NEITHER chapeau_text NOR sub_items (likely extraction gap):"
        )
        for i in empty:
            print(
                f"  items[{i}]: clause {items[i]['clause_number']} - {items[i]['heading']}"
            )
    else:
        print("OK: every clause has either chapeau_text or sub_items.")

    # 3. Duplicate refs within the same clause's sub_items
    ref_issues = []
    for i, item in enumerate(items):
        refs = [s["ref"] for s in item.get("sub_items", [])]
        if len(refs) != len(set(refs)):
            ref_issues.append(i)
    if ref_issues:
        print(
            f"\nWARNING: {len(ref_issues)} clauses have duplicate sub_item refs: items {ref_issues}"
        )
    else:
        print("OK: no duplicate sub_item refs within any single clause.")

    # 4. Print full_text() reconstruction for a couple of clauses so you can eyeball quality
    print(
        "\n--- Sample reconstructed full_text() for first 2 clauses with sub_items ---"
    )
    shown = 0
    for item in items:
        if item["item_type"] == "clause" and item["sub_items"]:
            print(f"\nClause {item['clause_number']} - {item['heading']}:")
            parts = [item["chapeau_text"]]
            for sub in item["sub_items"]:
                parts.append(f"({sub['ref']}) {sub['text']}")
                for subsub in sub.get("sub_items", []):
                    parts.append(f"    ({subsub['ref']}) {subsub['text']}")
            print("\n".join(p for p in parts if p))
            shown += 1
            if shown >= 2:
                break


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_structured.py structured_docs/{doc_id}.json")
        sys.exit(1)
    validate(sys.argv[1])
