import json
from pathlib import Path

INPUT_PATH = Path("structured_docs/")
MATCHED_DIRECTIONS_FILE = Path("doc_manifest.json")

with open(MATCHED_DIRECTIONS_FILE, "r") as f:
    manifest = json.load(f)

for filename, meta in zip(
    (doc.stem for doc in sorted(INPUT_PATH.glob("*.json"), key=lambda a: len(a.stem))),
    manifest,
):
    meta["local_path"] = str(Path("raw_pdfs") / f"{filename}.pdf")
    meta["doc_id"] = filename

with open(MATCHED_DIRECTIONS_FILE, "w") as f:
    json.dump(manifest, f, indent=2)
