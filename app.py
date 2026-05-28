"""
Civic Manual RAG Bot — Modal deployment.

Components:
  - Modal Volume  : stores 675 page PNGs + the PDF
  - ingest()      : one-shot function to parse PDF, embed, index, upload images
  - web_app       : FastAPI + Gradio UI served via @modal.asgi_app()

Deploy  : modal deploy app.py
Ingest  : modal run app.py::ingest
Dev     : modal serve app.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

import modal

# ---------------------------------------------------------------------------
# Modal infrastructure
# ---------------------------------------------------------------------------

VOLUME_NAME = "civic-pages"
APP_NAME = "civic-rag"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "pymupdf",
        "pillow",
        "google-generativeai",
        "pinecone",
        "fastapi",
        "aiofiles",
        "uvicorn",
        "python-dotenv",
    )
    .add_local_dir("frontend/dist", remote_path="/frontend/dist")
)

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App(APP_NAME, image=image)

SECRETS = modal.Secret.from_name("civic-rag-secrets")  # set via: modal secret create civic-rag-secrets GEMINI_API_KEY=... PINECONE_API_KEY=...
VOLUME_MOUNT = "/civic-pages"
PDF_FILENAME = "Civic Manual.pdf"


# ---------------------------------------------------------------------------
# Ingestion (run once: modal run app.py::ingest)
# ---------------------------------------------------------------------------

@app.function(
    volumes={VOLUME_MOUNT: vol},
    secrets=[SECRETS],
    timeout=3600,
    memory=4096,
)
def ingest():
    """Parse the PDF, embed all chunks, upsert to Pinecone, save page PNGs to volume."""
    import shutil
    import subprocess

    vol_path = Path(VOLUME_MOUNT)

    # The PDF must be uploaded to the volume before running ingest.
    # Upload it with: modal volume put civic-pages "Civic Manual.pdf" /civic-pages/
    pdf_in_volume = vol_path / PDF_FILENAME
    if not pdf_in_volume.exists():
        raise FileNotFoundError(
            f"{PDF_FILENAME} not found in Modal volume. "
            "Upload it first: modal volume put civic-pages 'Civic Manual.pdf' /civic-pages/"
        )

    # Run parse_pdf inline (avoids subprocess path issues in Modal)
    import fitz
    import re

    pages_dir = vol_path / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = vol_path / "chunks.json"

    doc = fitz.open(str(pdf_in_volume))
    total_pages = len(doc)
    print(f"Parsing {total_pages} pages...")

    all_chunks = []

    def detect_section(page):
        blocks = page.get_text("dict")["blocks"]
        best_size, best_text = 0, ""
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()
                    if size > best_size and len(text) > 3:
                        best_size, best_text = size, text
        return best_text or "General"

    CHARS_PER_CHUNK = 1600  # ~400 tokens
    OVERLAP_CHARS = 200     # ~50 tokens

    for page_num in range(total_pages):
        page = doc[page_num]
        page_1idx = page_num + 1
        text = page.get_text().strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        section = detect_section(page)

        start, chunk_idx = 0, 0
        while start < len(text):
            chunk = text[start : start + CHARS_PER_CHUNK].strip()
            if chunk:
                all_chunks.append({
                    "id": f"p{page_1idx:04d}_c{chunk_idx:03d}",
                    "page": page_1idx,
                    "section": section,
                    "text": chunk,
                })
                chunk_idx += 1
            start += CHARS_PER_CHUNK - OVERLAP_CHARS

        png_path = pages_dir / f"page_{page_1idx:04d}.png"
        if not png_path.exists():
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            pix.save(str(png_path))

        if page_1idx % 100 == 0:
            print(f"  {page_1idx}/{total_pages} — {len(all_chunks)} chunks")

    doc.close()
    with open(chunks_path, "w") as f:
        json.dump(all_chunks, f)
    print(f"Saved {len(all_chunks)} chunks and {total_pages} PNGs.")
    vol.commit()

    # Embed and index
    import google.generativeai as genai
    from pinecone import Pinecone, ServerlessSpec

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    INDEX_NAME = "civic-manual"
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"Creating Pinecone index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            time.sleep(2)

    index = pc.Index(INDEX_NAME)
    BATCH = 100

    print(f"Embedding {len(all_chunks)} chunks in batches of {BATCH}...")
    total_batches = (len(all_chunks) + BATCH - 1) // BATCH

    for b in range(total_batches):
        batch = all_chunks[b * BATCH : (b + 1) * BATCH]
        texts = [c["text"] for c in batch]

        result = genai.embed_content(
            model="models/gemini-embedding-2",
            content=texts,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        )
        embeddings = result.get("embedding") or result.get("embeddings")
        if isinstance(embeddings[0], float):
            embeddings = [embeddings]

        vectors = [
            {
                "id": c["id"],
                "values": emb,
                "metadata": {"page": c["page"], "section": c["section"], "text": c["text"][:1000]},
            }
            for c, emb in zip(batch, embeddings)
        ]
        index.upsert(vectors=vectors)
        print(f"  Batch {b + 1}/{total_batches} upserted")
        time.sleep(1)

    stats = index.describe_index_stats()
    print(f"Ingestion complete. Pinecone: {stats['total_vector_count']} vectors.")


# ---------------------------------------------------------------------------
# Query logic (runs inside the web app container)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are "Your Honda Civic's AI Mechanic", an expert assistant for the Honda Civic service manual.
Answer ONLY from the provided manual excerpts and page images. Do not use outside knowledge.

Return a single valid JSON object — no markdown fences, no extra text:
{
  "answer_sections": [
    {
      "text": "A sentence or short paragraph of the answer.",
      "tooltip_text": "Verbatim snippet (max 200 chars) from the source material that directly supports this sentence.",
      "page_refs": [<page numbers as integers>]
    }
  ],
  "citations": [
    {"page": <int>, "section": "<section title>", "label": "Page <N> — <section title>"}
  ],
  "suggested_questions": [
    "<follow-up question 1>",
    "<follow-up question 2>",
    "<follow-up question 3>"
  ]
}

Rules:
- Split the answer into logical sentences or paragraphs as separate answer_sections.
- tooltip_text must be a verbatim quote from the supplied context, not a paraphrase.
- citations must list every page referenced in answer_sections.
- suggested_questions must be exactly 3 concise, relevant follow-up questions.
- If page images show diagrams, describe what they depict in the answer.
- If the manual does not contain the answer, return one answer_section: "I could not find that information in the Civic service manual." with empty citations."""


LOCAL_PAGES_DIR = Path(__file__).parent / ".tmp" / "pages"
LOCAL_PDF_PATH = Path(__file__).parent / "Civic Manual.pdf"


def _pages_dir() -> Path:
    modal_path = Path(VOLUME_MOUNT) / "pages"
    return modal_path if modal_path.exists() else LOCAL_PAGES_DIR


def _pdf_path() -> Path:
    modal_path = Path(VOLUME_MOUNT) / PDF_FILENAME
    return modal_path if modal_path.exists() else LOCAL_PDF_PATH


def _load_page_b64(page_num: int) -> str | None:
    path = _pages_dir() / f"page_{page_num:04d}.png"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def run_query(question: str, base_url: str) -> dict:
    import google.generativeai as genai
    from pinecone import Pinecone

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index("civic-manual")

    # Embed query
    qvec = genai.embed_content(
        model="models/gemini-embedding-2",
        content=question,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768,
    )["embedding"]

    # Retrieve
    matches = index.query(vector=qvec, top_k=5, include_metadata=True)["matches"]
    if not matches:
        return {
            "answer_sections": [{"text": "No relevant content found.", "tooltip_text": "", "page_refs": []}],
            "citations": [],
            "suggested_questions": [],
        }

    # Collect unique pages (max 5)
    seen_pages: list[int] = []
    for m in matches:
        pg = m["metadata"].get("page")
        if pg and pg not in seen_pages:
            seen_pages.append(pg)
        if len(seen_pages) >= 5:
            break

    # Build content
    ctx = "## Manual excerpts\n\n"
    for m in matches:
        md = m["metadata"]
        ctx += f"[Page {md.get('page')} — {md.get('section')}]\n{md.get('text', '')}\n\n"

    user_content: list = [{"type": "text", "text": ctx}]
    for pg in seen_pages:
        b64 = _load_page_b64(pg)
        if b64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })
    user_content.append({"type": "text", "text": f"\n## Question\n{question}"})

    from openai import OpenAI
    nvidia = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"],
    )
    response = nvidia.chat.completions.create(
        model="meta/llama-4-maverick-17b-128e-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
        max_tokens=2048,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    result = json.loads(raw)

    # Inject clickable PDF URLs into citations
    for cite in result.get("citations", []):
        cite["url"] = f"{base_url}/pdf#page={cite['page']}"

    return result


# ---------------------------------------------------------------------------
# FastAPI + React frontend web app
# ---------------------------------------------------------------------------


@app.function(
    volumes={VOLUME_MOUNT: vol},
    secrets=[SECRETS],
    memory=2048,
    min_containers=1,
    timeout=300,
)
@modal.asgi_app()
def web_app():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, Response
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel

    fastapi_app = FastAPI()

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    BASE_URL = os.environ.get("MODAL_APP_URL", "")

    class QueryRequest(BaseModel):
        question: str

    @fastapi_app.get("/health")
    def health():
        return {"status": "ok"}

    @fastapi_app.get("/pdf")
    def serve_pdf():
        pdf_path = _pdf_path()
        if not pdf_path.exists():
            return Response(content="PDF not found", status_code=404)
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    @fastapi_app.post("/query")
    def query_endpoint(body: QueryRequest):
        return run_query(body.question, BASE_URL)

    fastapi_app.mount("/", StaticFiles(directory="/frontend/dist", html=True), name="static")

    return fastapi_app
