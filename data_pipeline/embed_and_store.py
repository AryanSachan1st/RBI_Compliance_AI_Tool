"""
Reads chunks.jsonl, embeds every chunk with OpenAI's text-embedding-3-small,
and stores everything in a local, persistent Chroma collection.

This is deliberately simple: no batching sophistication, no retry framework --
matches the "get it working now" priority. 4,250 chunks at this size will
embed in well under a minute and cost a few cents.

Usage:
    python embed_and_store.py
(reads chunks.jsonl, writes/updates ./chroma_db/ on disk)
"""

import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CHUNKS_FILE = Path("chunks.jsonl")
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "rbi_irdai_clauses"
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs per embeddings call; 100 is a safe, simple batch size


def load_chunks() -> list[dict]:
    chunks = []
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def main():
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks from {CHUNKS_FILE}")

    client = OpenAI(api_key=OPENAI_API_KEY)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        embeddings = embed_batch(client, texts)

        collection.upsert(
            ids=[c["chunk_id"] for c in batch],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "doc_id": c["doc_id"],
                    "citation": c["citation"],
                    "item_type": c["item_type"],
                    # Chroma metadata values must be str/int/float/bool -- join list to a string
                    "topics": ",".join(c.get("topics", [])),
                }
                for c in batch
            ],
        )
        print(f"Embedded and stored {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)}")

    print(
        f"\nDone. Collection '{COLLECTION_NAME}' has {collection.count()} items in {CHROMA_DIR}"
    )


if __name__ == "__main__":
    main()
