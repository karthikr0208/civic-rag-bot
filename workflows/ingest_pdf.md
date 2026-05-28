# Workflow: Ingest PDF into Pinecone

## Objective
Parse the Civic Manual PDF into text chunks and page images, embed the chunks with Gemini Embedding 2, and store them in Pinecone. This only needs to be run once (or re-run if the PDF changes).

## Required Inputs
- `Civic Manual.pdf` — placed in the project root
- `GEMINI_API_KEY` — Gemini API key with Gemini Embedding 2 access
- `PINECONE_API_KEY` — Pinecone API key (free tier, starter plan)
- Modal CLI authenticated (`modal token new`)
- Modal secret created (see Step 1)

## Expected Outputs
- `.tmp/chunks.json` — ~6,500–7,500 text chunks with page/section metadata
- `.tmp/pages/page_NNNN.png` — 675 PNG renders of every page at 150 dpi
- Pinecone index `civic-manual` — ~6,750 vectors (dim=768, cosine)
- Modal Volume `civic-pages` — page PNGs + the PDF file

## Steps

### Step 1 — Create Modal secret (once)
```bash
modal secret create civic-rag-secrets \
  GEMINI_API_KEY=<your-key> \
  PINECONE_API_KEY=<your-key>
```

### Step 2 — Install dependencies locally (for local dev/testing)
```bash
pip install -r requirements.txt
```

### Step 3 — (Optional) Parse and embed locally first to validate
Run these locally to confirm chunking and embedding work before pushing to Modal:
```bash
python tools/parse_pdf.py
# Expected: .tmp/chunks.json created, .tmp/pages/ has 675 PNGs

python tools/embed_and_index.py
# Expected: Pinecone index created, ~6,750 vectors upserted
# Duration: ~5–10 min (1s sleep per batch × ~68 batches)
```

### Step 4 — Upload PDF to Modal Volume
```bash
modal volume put civic-pages "Civic Manual.pdf" /civic-pages/
```

### Step 5 — Run ingestion on Modal
```bash
modal run app.py::ingest
```
This runs parse + embed + index inside Modal with full CPU and the volume mounted.
Expect ~15–20 minutes total.

### Step 6 — Verify
- Open Pinecone dashboard → `civic-manual` index should show ~6,750 vectors
- Run a local test query:
  ```bash
  python tools/query_rag.py "What is the engine oil capacity?"
  ```
  Expect: JSON response with answer_sections, citations (page numbers), suggested_questions

## Rate Limit Notes
- Gemini Embedding 2 free tier: **1K requests/day, 100 RPM**
- The tool batches 100 chunks per API call → ~68 total requests for 6,750 chunks
- With 1s sleep between batches, total embedding time ≈ 7–10 minutes
- If you hit a 429 error, the script parses the API's suggested retry delay and waits exactly that long before retrying once. If the retry also fails, the script crashes — wait for the minute window to reset and re-run (it will skip already-upserted vectors if you re-create the index, or just re-run as-is since Pinecone upserts are idempotent by ID).

## Re-ingestion (if PDF changes)
1. Delete the Pinecone index from the dashboard (or via SDK)
2. Delete `.tmp/chunks.json` and `.tmp/pages/`
3. Re-upload the new PDF: `modal volume put civic-pages "Civic Manual.pdf" /civic-pages/`
4. Re-run Step 5

## Known Constraints
- Pinecone free tier: 1 index maximum. Do not create additional indexes.
- Metadata stored per vector is capped at 1000 chars of `text`. Full chunk text lives only in `.tmp/chunks.json` locally; the volume copy is the authoritative source on Modal.
- Page PNGs at 150 dpi are ~200–400 KB each → ~135–270 MB total. Modal volume handles this.
