import hashlib
import json
from pathlib import Path

import requests

Path("raw_pdfs").mkdir(exist_ok=True)

with open("matched_directions.json") as f:
    docs = json.load(f)

for doc in docs:
    if not doc["pdf_url"]:
        continue
    try:
        resp = requests.get(
            doc["pdf_url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=60
        )
        resp.raise_for_status()
        file_hash = hashlib.sha256(resp.content).hexdigest()[:12]
        path = Path("raw_pdfs") / f"{file_hash}.pdf"
        path.write_bytes(resp.content)
        doc["local_path"] = str(path)
        doc["sha256"] = file_hash
        print(f"Downloaded: {doc['title']} -> {path}")
    except Exception as e:
        print(f"FAILED: {doc['title']}: {e}")

with open("matched_directions.json", "w") as f:
    json.dump(docs, f, indent=2)
