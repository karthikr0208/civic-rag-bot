"""
Embed text chunks with Gemini Embedding 2 and upsert to Pinecone.

Prerequisites:
  - .tmp/chunks.json must exist (run parse_pdf.py first)
  - GEMINI_API_KEY and PINECONE_API_KEY set in .env

Rate limits (free tier):
  Gemini Embedding 2: 100 RPM, 1K RPD, 30K TPM
  Strategy: batch 100 chunks per API call (~68 calls total), 1s sleep between batches.

Run: python tools/embed_and_index.py
"""

import json
import os
import sys
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv(Path(__file__).parent.parent / ".env")

CHUNKS_PATH = Path(__file__).parent.parent / ".tmp" / "chunks.json"

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]

EMBEDDING_MODEL = "gemini-embedding-2"
OUTPUT_DIM = 768
BATCH_SIZE = 100
SLEEP_BETWEEN_BATCHES = 1.0  # seconds — keeps us well under 100 RPM

INDEX_NAME = "civic-manual"
INDEX_CLOUD = "aws"
INDEX_REGION = "us-east-1"


def get_or_create_index(pc: Pinecone) -> object:
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"Creating Pinecone index '{INDEX_NAME}' (dim={OUTPUT_DIM}, cosine)...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=OUTPUT_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud=INDEX_CLOUD, region=INDEX_REGION),
        )
        # Wait for index to be ready
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            time.sleep(2)
        print("  Index ready.")
    else:
        print(f"Using existing Pinecone index '{INDEX_NAME}'.")
    return pc.Index(INDEX_NAME)


def embed_batch(texts: list[str]) -> list[list[float]]:
    result = genai.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        content=texts,
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=OUTPUT_DIM,
    )
    # embed_content returns a dict with "embedding" (single) or list when batched
    embeddings = result.get("embedding") or result.get("embeddings")
    if isinstance(embeddings[0], float):
        # Single embedding returned as flat list — wrap it
        embeddings = [embeddings]
    return embeddings


def main():
    if not CHUNKS_PATH.exists():
        print(f"ERROR: {CHUNKS_PATH} not found. Run parse_pdf.py first.", file=sys.stderr)
        sys.exit(1)

    genai.configure(api_key=GEMINI_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = get_or_create_index(pc)

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Loaded {len(chunks)} chunks. Embedding in batches of {BATCH_SIZE}...")

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    upserted = 0

    for batch_num in range(total_batches):
        batch = chunks[batch_num * BATCH_SIZE : (batch_num + 1) * BATCH_SIZE]
        texts = [c["text"] for c in batch]

        try:
            embeddings = embed_batch(texts)
        except Exception as e:
            import re as _re
            match = _re.search(r"retry[^\d]+(\d+)", str(e))
            wait = int(match.group(1)) + 2 if match else 60
            print(f"  ERROR on batch {batch_num + 1}: rate limited. Waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
            embeddings = embed_batch(texts)

        vectors = [
            {
                "id": chunk["id"],
                "values": emb,
                "metadata": {
                    "page": chunk["page"],
                    "section": chunk["section"],
                    "text": chunk["text"][:1000],  # Pinecone metadata cap
                },
            }
            for chunk, emb in zip(batch, embeddings)
        ]

        index.upsert(vectors=vectors)
        upserted += len(vectors)

        print(f"  Batch {batch_num + 1}/{total_batches} - {upserted}/{len(chunks)} upserted")
        time.sleep(SLEEP_BETWEEN_BATCHES)

    stats = index.describe_index_stats()
    print(f"\nDone. Pinecone index '{INDEX_NAME}' now has {stats['total_vector_count']} vectors.")


if __name__ == "__main__":
    main()
