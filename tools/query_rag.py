"""
End-to-end query handler for the Civic Manual RAG bot.

Given a user question:
  1. Embed the query with Gemini Embedding 2
  2. Retrieve top-5 chunks from Pinecone
  3. Load page PNGs for the retrieved pages
  4. Call Gemini Flash 2.5 with text + images
  5. Return structured JSON response

Can be run standalone for local testing:
  python tools/query_rag.py "What is the torque spec for the front wheel bearing?"

Expects:
  GEMINI_API_KEY and PINECONE_API_KEY in .env
  .tmp/pages/page_NNNN.png  (from parse_pdf.py)  OR  /civic-pages/  (Modal volume)
"""

import base64
import json
import os
import sys
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv(Path(__file__).parent.parent / ".env")

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]

EMBEDDING_MODEL = "gemini-embedding-2"
GENERATION_MODEL = "meta/llama-4-maverick-17b-128e-instruct"
OUTPUT_DIM = 768
INDEX_NAME = "civic-manual"
TOP_K = 5
MAX_PAGES = 5  # caps images sent to Gemini (max 16 per request)

# Page images location — prefer Modal volume, fall back to .tmp/pages/
MODAL_PAGES_DIR = Path("/civic-pages")
LOCAL_PAGES_DIR = Path(__file__).parent.parent / ".tmp" / "pages"


SYSTEM_PROMPT = """You are "Your Honda Civic's AI Mechanic", an expert assistant for the Honda Civic service manual.
Answer ONLY from the provided manual excerpts and page images. Do not use outside knowledge.

You MUST return a single valid JSON object with exactly this schema — no markdown fences, no extra text:
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
- Split the answer into logical sentences/paragraphs as separate answer_sections.
- tooltip_text must be a verbatim quote from the supplied context, not a paraphrase.
- citations must list every page referenced in any answer_section.
- suggested_questions must be 3 concise, relevant follow-up questions.
- If page images show diagrams, describe what they depict in the relevant answer_section.
- If the manual does not contain the answer, return a single answer_section with text "I could not find that information in the Civic service manual." and empty citations."""


def pages_dir() -> Path:
    if MODAL_PAGES_DIR.exists():
        return MODAL_PAGES_DIR
    return LOCAL_PAGES_DIR


def load_page_image_b64(page_num: int) -> str | None:
    path = pages_dir() / f"page_{page_num:04d}.png"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def embed_query(query: str) -> list[float]:
    result = genai.embed_content(
        model=f"models/{EMBEDDING_MODEL}",
        content=query,
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=OUTPUT_DIM,
    )
    return result["embedding"]


def retrieve_chunks(index, query_vector: list[float]) -> list[dict]:
    resp = index.query(vector=query_vector, top_k=TOP_K, include_metadata=True)
    return resp["matches"]


def build_request(query: str, matches: list[dict]) -> list:
    """Build OpenAI-format user content: text context + page images + question."""
    seen_pages = []
    for m in matches:
        pg = m["metadata"].get("page")
        if pg and pg not in seen_pages:
            seen_pages.append(pg)
        if len(seen_pages) >= MAX_PAGES:
            break

    context_text = "## Manual excerpts\n\n"
    for m in matches:
        md = m["metadata"]
        context_text += f"[Page {md.get('page')} — {md.get('section')}]\n{md.get('text', '')}\n\n"

    user_content: list = [{"type": "text", "text": context_text}]

    for pg in seen_pages:
        b64 = load_page_image_b64(pg)
        if b64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

    user_content.append({"type": "text", "text": f"\n## Question\n{query}"})
    return user_content


def query(question: str) -> dict:
    genai.configure(api_key=GEMINI_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)

    query_vector = embed_query(question)
    matches = retrieve_chunks(index, query_vector)

    if not matches:
        return {
            "answer_sections": [{"text": "No relevant content found in the manual.", "tooltip_text": "", "page_refs": []}],
            "citations": [],
            "suggested_questions": [],
        }

    user_content = build_request(question, matches)

    nvidia = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY,
    )
    response = nvidia.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
        max_tokens=2048,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw)
    return result


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the oil capacity for the 1.5L turbo engine?"
    print(f"Query: {question}\n")
    result = query(question)
    print(json.dumps(result, indent=2))
