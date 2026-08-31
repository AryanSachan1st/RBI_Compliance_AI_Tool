import json

import pytest

from services.rbi_ingestion_service import build_regulatory_chunks, ingest_regulatory_corpus


def test_build_regulatory_chunks_preserves_title_and_page(tmp_path):
    source_file = tmp_path / "rbi.pdf"
    source_file.write_bytes(b"placeholder")
    chunks = build_regulatory_chunks(
        [{"source_title": "RBI Digital Lending Directions", "regulator": "RBI", "local_filename": "rbi.pdf"}],
        tmp_path,
        page_extractor=lambda _: ["APR must be disclosed.", "Fees must be disclosed."],
    )
    assert chunks[0]["source_title"] == "RBI Digital Lending Directions"
    assert chunks[0]["page_number"] == 1
    assert chunks[1]["page_number"] == 2
    assert chunks[0]["chunk_id"].startswith("rbi-rbi-p1")


def test_ingestion_skips_without_approved_manifest(tmp_path):
    result = ingest_regulatory_corpus(tmp_path / "missing.json", tmp_path, tmp_path / "chunks.json")
    assert result["status"] == "skipped"


def test_ingestion_writes_derived_corpus(tmp_path):
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps([{"source_title": "IRDAI Circular", "regulator": "IRDAI", "local_filename": "irdai.pdf"}]), encoding="utf-8")
    (tmp_path / "irdai.pdf").write_bytes(b"placeholder")
    output = tmp_path / "regulatory_chunks.json"
    result = ingest_regulatory_corpus(manifest, tmp_path, output, page_extractor=lambda _: ["Policy exclusions must be disclosed."])
    assert result["status"] == "complete"
    assert json.loads(output.read_text(encoding="utf-8"))[0]["source_title"] == "IRDAI Circular"


def test_build_rejects_unapproved_source_shape(tmp_path):
    with pytest.raises(ValueError):
        build_regulatory_chunks([{"regulator": "RBI"}], tmp_path)
