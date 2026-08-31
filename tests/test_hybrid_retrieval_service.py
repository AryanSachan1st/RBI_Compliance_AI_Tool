from services.hybrid_retrieval_service import HybridRegulatoryRetriever, RegulatoryChunk


def _retriever():
    return HybridRegulatoryRetriever([
        RegulatoryChunk("rbi-apr", "The regulated entity shall disclose annual percentage rate to borrower.", "RBI Digital Lending Directions", 4),
        RegulatoryChunk("irdai-disclosure", "The insurer shall disclose policy terms and exclusions clearly.", "IRDAI Policyholder Directions", 8),
        RegulatoryChunk("rbi-fee", "All loan charges must be disclosed in the key fact statement.", "RBI Digital Lending Directions", 5),
    ])


def test_lexical_search_returns_traceable_source_metadata():
    result = _retriever().lexical_search("annual percentage rate", limit=1)
    assert result[0].chunk_id == "rbi-apr"
    assert result[0].source_title == "RBI Digital Lending Directions"


def test_rrf_fusion_promotes_match_found_by_both_retrievers():
    results = _retriever().fuse([
        {"chunk_id": "rbi-apr", "text_content": "APR disclosure", "source_title": "RBI Digital Lending Directions", "page_number": 4},
        {"chunk_id": "irdai-disclosure", "text_content": "Policy disclosure", "source_title": "IRDAI Policyholder Directions", "page_number": 8},
    ], "annual percentage rate", limit=2)
    assert results[0]["chunk_id"] == "rbi-apr"
    assert results[0]["retrieval_confidence"] == 1.0


def test_empty_corpus_does_not_invent_lexical_results():
    assert HybridRegulatoryRetriever([]).fuse([], "APR") == []
import json

from services.hybrid_retrieval_service import load_regulatory_corpus


def test_load_regulatory_corpus_preserves_citation_metadata(tmp_path):
    path = tmp_path / "regulatory_chunks.json"
    path.write_text(json.dumps([{
        "chunk_id": "rbi-1",
        "text_content": "APR must be disclosed.",
        "source_title": "RBI Digital Lending Directions",
        "page_number": 4,
    }]), encoding="utf-8")
    corpus = load_regulatory_corpus(path)
    assert corpus[0].source_title == "RBI Digital Lending Directions"
    assert corpus[0].page_number == 4
