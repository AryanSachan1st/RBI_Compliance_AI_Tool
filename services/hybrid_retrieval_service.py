"""Hybrid regulatory retrieval: lexical BM25-style ranking fused with semantic search."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


@dataclass(frozen=True)
class RegulatoryChunk:
    chunk_id: str
    text_content: str
    source_title: str
    page_number: int | None = None

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "RegulatoryChunk":
        return cls(
            chunk_id=str(item["chunk_id"]),
            text_content=str(item["text_content"]),
            source_title=str(item["source_title"]),
            page_number=item.get("page_number"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text_content": self.text_content,
            "source_title": self.source_title,
            "page_number": self.page_number,
        }


class HybridRegulatoryRetriever:
    """Fuses supplied semantic matches and a local lexical corpus via RRF."""

    def __init__(self, chunks: list[RegulatoryChunk], rrf_k: int = 60):
        self.chunks = chunks
        self.rrf_k = rrf_k
        self._documents = [_tokens(chunk.text_content) for chunk in chunks]
        self._document_frequency = Counter(token for tokens in self._documents for token in set(tokens))
        self._average_length = sum(map(len, self._documents)) / len(self._documents) if self._documents else 0

    def lexical_search(self, query: str, limit: int = 3) -> list[RegulatoryChunk]:
        query_tokens = _tokens(query)
        if not query_tokens or not self.chunks:
            return []
        total_documents = len(self._documents)
        scored: list[tuple[float, RegulatoryChunk]] = []
        for chunk, document in zip(self.chunks, self._documents):
            counts = Counter(document)
            score = 0.0
            for token in query_tokens:
                if not counts[token]:
                    continue
                idf = math.log(1 + (total_documents - self._document_frequency[token] + 0.5) / (self._document_frequency[token] + 0.5))
                denominator = counts[token] + 1.5 * (1 - 0.75 + 0.75 * len(document) / self._average_length)
                score += idf * counts[token] * 2.5 / denominator
            if score > 0:
                scored.append((score, chunk))
        return [chunk for _, chunk in sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]]

    def fuse(self, semantic_matches: list[dict[str, Any]], query: str, limit: int = 3) -> list[dict[str, Any]]:
        lexical_matches = self.lexical_search(query, limit=limit)
        merged: dict[str, dict[str, Any]] = {}
        for rank, match in enumerate(semantic_matches, start=1):
            item = dict(match)
            item.setdefault("chunk_id", item.get("id") or f"semantic-{rank}")
            item.setdefault("source_title", "Unknown regulatory source")
            item.setdefault("page_number", None)
            item["_rrf_score"] = item.get("_rrf_score", 0.0) + 1 / (self.rrf_k + rank)
            merged[item["chunk_id"]] = item
        for rank, chunk in enumerate(lexical_matches, start=1):
            item = merged.setdefault(chunk.chunk_id, chunk.as_dict())
            item["_rrf_score"] = item.get("_rrf_score", 0.0) + 1 / (self.rrf_k + rank)
        ranked = sorted(merged.values(), key=lambda item: item["_rrf_score"], reverse=True)[:limit]
        maximum = ranked[0]["_rrf_score"] if ranked else 0.0
        for item in ranked:
            item["retrieval_confidence"] = round(item.pop("_rrf_score") / maximum, 4) if maximum else 0.0
        return ranked


def load_regulatory_corpus(path: str | Path) -> list[RegulatoryChunk]:
    corpus_path = Path(path)
    if not corpus_path.exists():
        return []
    return [RegulatoryChunk.from_dict(item) for item in json.loads(corpus_path.read_text(encoding="utf-8"))]
