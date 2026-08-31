"""Build a traceable local RAG corpus from approved RBI/IRDAI PDFs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST_PATH = PROJECT_ROOT / "storage" / "regulatory_sources.json"
SOURCE_DIRECTORY = PROJECT_ROOT / "storage" / "regulatory_sources"
OUTPUT_PATH = PROJECT_ROOT / "storage" / "regulatory_chunks.json"


def extract_pdf_pages(path: str | Path) -> list[str]:
    reader = PdfReader(str(path))
    return [(page.extract_text() or "").strip() for page in reader.pages]


def build_regulatory_chunks(
    sources: list[dict],
    source_directory: str | Path,
    page_extractor: Callable[[str | Path], list[str]] = extract_pdf_pages,
) -> list[dict]:
    """Chunk each source page without losing its document and page provenance."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks: list[dict] = []
    for source in sources:
        required = {"source_title", "regulator", "local_filename"}
        missing = required - source.keys()
        if missing:
            raise ValueError(f"Regulatory source is missing fields: {sorted(missing)}")
        pdf_path = Path(source_directory) / source["local_filename"]
        if not pdf_path.exists():
            raise FileNotFoundError(f"Approved regulatory PDF is missing: {pdf_path}")
        for page_number, page_text in enumerate(page_extractor(pdf_path), start=1):
            for sequence, chunk_text in enumerate(splitter.split_text(page_text), start=1):
                chunks.append({
                    "chunk_id": f"{source['regulator'].lower()}-{pdf_path.stem}-p{page_number}-c{sequence}",
                    "text_content": chunk_text,
                    "source_title": source["source_title"],
                    "page_number": page_number,
                })
    return chunks


def ingest_regulatory_corpus(
    manifest_path: str | Path = SOURCE_MANIFEST_PATH,
    source_directory: str | Path = SOURCE_DIRECTORY,
    output_path: str | Path = OUTPUT_PATH,
    page_extractor: Callable[[str | Path], list[str]] = extract_pdf_pages,
) -> dict:
    """Generate corpus JSON. Skips safely until the approved manifest is present."""
    manifest = Path(manifest_path)
    if not manifest.exists():
        return {"status": "skipped", "message": f"No approved source manifest at {manifest}.", "chunk_count": 0}
    sources = json.loads(manifest.read_text(encoding="utf-8"))
    chunks = build_regulatory_chunks(sources, source_directory, page_extractor=page_extractor)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "complete", "message": f"Ingested {len(chunks)} traceable regulatory chunks.", "chunk_count": len(chunks)}
