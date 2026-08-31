# Regulatory corpus setup

The hybrid retriever expects a derived `storage/regulatory_chunks.json` file.
Do not manually author regulatory excerpts: build it only from project-approved,
public RBI/IRDAI source documents. The source manifest template is
`storage/regulatory_sources.example.json`.

Each derived chunk must use this JSON shape:

```json
{
  "chunk_id": "rbi-digital-lending-2025-p4-c1",
  "text_content": "Exact extracted source text...",
  "source_title": "Reserve Bank of India (Digital Lending) Directions, 2025",
  "page_number": 4
}
```

The title and page number are mandatory so every downstream clause verdict can
show a traceable citation. Until approved documents are ingested, the system
must retain an `UNCERTAIN_MANUAL_REVIEW` outcome rather than treating the old
dummy rulebook as authoritative regulatory evidence.
