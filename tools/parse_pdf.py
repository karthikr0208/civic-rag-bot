"""
Parse the Civic Manual PDF into text chunks and page PNG renders.

Outputs:
  .tmp/chunks.json      — list of {id, page, section, text}
  .tmp/pages/           — page_{n:04d}.png at 150 dpi

Run: python tools/parse_pdf.py
"""

import json
import os
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

PDF_PATH = Path(__file__).parent.parent / "Civic Manual.pdf"
TMP_DIR = Path(__file__).parent.parent / ".tmp"
PAGES_DIR = TMP_DIR / "pages"
CHUNKS_PATH = TMP_DIR / "chunks.json"

CHUNK_TOKENS = 400
OVERLAP_TOKENS = 50
DPI = 150


def rough_token_count(text: str) -> int:
    # ~4 chars per token is a reasonable approximation
    return max(1, len(text) // 4)


def detect_section(page: fitz.Page) -> str:
    """Return the text of the largest-font block on the page (likely a heading)."""
    blocks = page.get_text("dict")["blocks"]
    best_size = 0
    best_text = ""
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size", 0)
                text = span.get("text", "").strip()
                if size > best_size and len(text) > 3:
                    best_size = size
                    best_text = text
    return best_text or "General"


def chunk_text(text: str, page: int, section: str) -> list[dict]:
    """Split text into overlapping chunks of ~CHUNK_TOKENS tokens."""
    words = text.split()
    if not words:
        return []

    chunks = []
    chunk_words = int(CHUNK_TOKENS * 4 / 1)  # words ≈ tokens*0.75, but keep simple
    overlap_words = int(OVERLAP_TOKENS * 4 / 1)

    # Use character-based splitting for better accuracy
    chars_per_chunk = CHUNK_TOKENS * 4
    overlap_chars = OVERLAP_TOKENS * 4

    start = 0
    chunk_index = 0
    while start < len(text):
        end = start + chars_per_chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({
                "id": f"p{page:04d}_c{chunk_index:03d}",
                "page": page,
                "section": section,
                "text": chunk,
            })
            chunk_index += 1
        start += chars_per_chunk - overlap_chars
        if start >= len(text):
            break

    return chunks


def render_page(page: fitz.Page, out_path: Path) -> None:
    mat = fitz.Matrix(DPI / 72, DPI / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    pix.save(str(out_path))


def main():
    if not PDF_PATH.exists():
        print(f"ERROR: PDF not found at {PDF_PATH}", file=sys.stderr)
        sys.exit(1)

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(PDF_PATH))
    total_pages = len(doc)
    print(f"Opened PDF: {total_pages} pages")

    all_chunks = []

    for page_num in range(total_pages):
        page = doc[page_num]
        page_1indexed = page_num + 1

        # Extract text
        text = page.get_text().strip()
        # Normalise whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        # Detect section heading
        section = detect_section(page)

        # Chunk the text
        if text:
            chunks = chunk_text(text, page_1indexed, section)
            all_chunks.extend(chunks)

        # Render page image
        png_path = PAGES_DIR / f"page_{page_1indexed:04d}.png"
        if not png_path.exists():
            render_page(page, png_path)

        if page_1indexed % 50 == 0 or page_1indexed == total_pages:
            print(f"  Processed {page_1indexed}/{total_pages} pages — {len(all_chunks)} chunks so far")

    doc.close()

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\nDone.")
    print(f"  Chunks written : {len(all_chunks)} -> {CHUNKS_PATH}")
    print(f"  Page renders   : {total_pages} PNGs -> {PAGES_DIR}")


if __name__ == "__main__":
    main()
