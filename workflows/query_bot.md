# Workflow: Query the Civic Manual RAG Bot

## Objective
Accept a user question, retrieve the most relevant manual content (text + page images), and return a structured answer with source tooltips, clickable citations, and suggested follow-up questions.

## Required Inputs
- User question (natural language)
- Pinecone index `civic-manual` populated (run ingest workflow first)
- Modal Volume `civic-pages` with page PNGs and the PDF
- `GEMINI_API_KEY` and `PINECONE_API_KEY` available (via Modal secret or `.env`)

## Expected Output (JSON schema)
```json
{
  "answer_sections": [
    {
      "text": "Human-readable sentence or paragraph.",
      "tooltip_text": "Verbatim quote from the PDF (max 200 chars) supporting this sentence.",
      "page_refs": [312, 313]
    }
  ],
  "citations": [
    {
      "page": 312,
      "section": "Front Suspension",
      "label": "Page 312 — Front Suspension",
      "url": "https://<app-url>/pdf#page=312"
    }
  ],
  "suggested_questions": [
    "What tools are needed for wheel bearing replacement?",
    "How do I remove the front axle?",
    "What is the rear wheel bearing torque spec?"
  ]
}
```

## Query Flow

```
User question
    │
    ▼
Gemini Embedding 2 (RETRIEVAL_QUERY, dim=768)
    │
    ▼
Pinecone top-5 similarity search
    │
    ▼
Collect unique page numbers (max 5) from matches
    │
    ├─► Load page PNGs from /civic-pages/pages/
    └─► Build context text from chunk metadata
    │
    ▼
Gemini Flash 2.5
  input: system_prompt + context text + up to 5 page images + question
  output: structured JSON (response_mime_type="application/json")
    │
    ▼
Inject citation URLs  →  render as HTML  →  return to UI
```

## Retrieval Parameters
| Parameter | Value | Rationale |
|---|---|---|
| top_k | 5 | Balances recall vs. context window size |
| max_pages | 5 | Gemini Flash limit is 16 images; 5 keeps latency low |
| embedding dim | 768 | Matryoshka reduction from Gemini Embedding 2 |
| similarity metric | cosine | Standard for text embeddings |

## System Prompt Design Principles
- Instructs Gemini to return **only JSON** (no markdown fences)
- `response_mime_type="application/json"` is set in GenerationConfig as a hard constraint
- `temperature=0.1` keeps answers factual and consistent
- Requires `tooltip_text` to be a **verbatim quote**, not a paraphrase — this is critical for the hover feature
- Falls back gracefully when the manual doesn't contain the answer

## Updating the System Prompt
The system prompt lives in `app.py` as `SYSTEM_PROMPT` (used in production) and is mirrored in `tools/query_rag.py` (used for local testing). Update both if you change the prompt.

Key things NOT to change without testing:
- The JSON schema structure — the Gradio UI (`render_answer_html`) parses exact field names
- `response_mime_type="application/json"` — removing this causes the model to sometimes wrap output in markdown

## Suggested Questions Behavior
- On first load: 3 hardcoded generic questions shown as chips
- After each query: the 3 questions from `suggested_questions` in the response replace them
- Clicking a chip populates the textbox and auto-submits
- If Gemini returns fewer than 3 suggestions, the UI hides the missing buttons

## Citation Link Behavior
- Citation URLs are `{base_url}/pdf#page={N}`
- `/pdf` is a FastAPI endpoint in `app.py` that serves `Civic Manual.pdf` from the Modal volume
- The `#page=N` fragment is handled by the browser's built-in PDF viewer (Chrome/Firefox/Edge all support it)
- Links open in a new tab

## Tooltip Behavior
- Each `answer_section` wraps its `text` in `<span class="src-span" data-tip="...">` with `tooltip_text` as the data attribute
- CSS `:hover::after` renders the tooltip box — no JavaScript required
- The tooltip appears above the hovered text and is styled dark with light text for readability
- Sections with no `tooltip_text` render as plain `<p>` tags

## Local Testing
```bash
# Single query
python tools/query_rag.py "What is the torque spec for the front wheel bearing?"

# The script reads GEMINI_API_KEY and PINECONE_API_KEY from .env
# It loads page PNGs from .tmp/pages/ (falls back from /civic-pages/)
```

## Deployment
```bash
# Serve locally (hot reload)
modal serve app.py

# Deploy to production
modal deploy app.py

# Check deployed URL
modal app list
```
After deploying, set `MODAL_APP_URL` in the Modal secret if you need the citation URLs to use the production domain. Otherwise they default to relative paths.

## Known Constraints
- Gemini Flash 2.5: 1M token context window; 5 page images + 5 text chunks is well within limits
- Cold start on Modal: first query after idle may take 5–10s (keep_warm=1 is set to mitigate this)
- The JSON parser strips markdown fences if Gemini adds them despite instructions — this is a defensive fallback, not normal behavior
