"""
Local development server — FastAPI backend + React UI.

Serves:
  - POST /query  — RAG query endpoint
  - GET  /pdf    — serves the Civic Manual PDF inline
  - GET  /       — serves the React build from frontend/dist/

Run: python run_local.py
Then open: http://localhost:7860
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

assert os.environ.get("GEMINI_API_KEY"), "GEMINI_API_KEY missing from .env"
assert os.environ.get("PINECONE_API_KEY"), "PINECONE_API_KEY missing from .env"
assert os.environ.get("NVIDIA_API_KEY"), "NVIDIA_API_KEY missing from .env"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from app import run_query, _pdf_path

BASE_URL = "http://localhost:7860"
DIST_DIR = Path(__file__).parent / "frontend" / "dist"

fastapi_app = FastAPI()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


if DIST_DIR.exists():
    fastapi_app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")
else:
    print(f"WARNING: {DIST_DIR} not found — run 'cd frontend && npm run build' first")


if __name__ == "__main__":
    print(f"Starting server at {BASE_URL}")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=7860)
