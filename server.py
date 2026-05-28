"""
Civic Manual RAG Bot — Render/standalone deployment (no Modal).

Start: uvicorn server:app --host 0.0.0.0 --port $PORT
Local: uvicorn server:app --reload
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

PDF_URL = os.environ.get(
    "PDF_URL",
    "https://drive.google.com/file/d/1WP24NxeHs7hlGbP_4s4xDVe9xWzfIOx6/view",
)

SYSTEM_PROMPT = """You are "Your Honda Civic's AI Mechanic", an expert assistant for the Honda Civic owner's manual.
Answer ONLY from the provided manual excerpts. Do not use outside knowledge.

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
- If the manual does not contain the answer, return one answer_section: "I could not find that information in the Civic owner's manual." with empty citations."""


def run_query(question: str) -> dict:
    import google.generativeai as genai
    from openai import OpenAI
    from pinecone import Pinecone

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index("civic-manual")

    # Embed query with Gemini
    qvec = genai.embed_content(
        model="models/gemini-embedding-2",
        content=question,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768,
    )["embedding"]

    # Retrieve top-5 chunks from Pinecone
    matches = index.query(vector=qvec, top_k=5, include_metadata=True)["matches"]
    if not matches:
        return {
            "answer_sections": [{"text": "No relevant content found.", "tooltip_text": "", "page_refs": []}],
            "citations": [],
            "suggested_questions": [],
        }

    # Build text-only context
    ctx = "## Manual excerpts\n\n"
    for m in matches:
        md = m["metadata"]
        ctx += f"[Page {md.get('page')} — {md.get('section')}]\n{md.get('text', '')}\n\n"

    user_content = [
        {"type": "text", "text": ctx},
        {"type": "text", "text": f"\n## Question\n{question}"},
    ]

    # Generate answer with NVIDIA Llama 4 Maverick
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

    # Point all citation links to the Google Drive PDF
    for cite in result.get("citations", []):
        cite["url"] = PDF_URL

    return result


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/pdf")
def serve_pdf():
    return RedirectResponse(url=PDF_URL)


@app.post("/query")
def query_endpoint(body: QueryRequest):
    return run_query(body.question)


DIST_DIR = Path(__file__).parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")
