# Claude Guidelines for pdfqna

## Project Overview
Flask API that accepts PDF uploads, extracts text, and answers questions via OpenAI.
The API is **stateless**: `/upload` extracts and returns text; `/query` accepts that text directly.

## Architecture — API Flow
```
Client → POST /upload (multipart PDF)
       ← { text: "..." }

Client → POST /query (JSON: { text, query })
       ← { answer: "..." }
```
Files are deleted from disk immediately after text extraction in `/upload`.
`/query` never reads from disk — it receives text in the request body.

## Rules Before Making Any Change

### 1. Map All Consumers First
Before changing a function or endpoint, identify **every caller**:
- Which routes call this function?
- What does each caller expect in return?
- What data does each caller pass in?

Example: before changing `extract_text_from_pdf`, check both `/upload` and any future route that might call it.

### 2. End-to-End Flow Check
After every fix, mentally trace the full user journey:
1. User uploads PDF → `/upload` saves, extracts, deletes file, returns `{ text }`
2. User asks question → `/query` receives `{ text, query }`, calls OpenAI, returns `{ answer }`

Ask: **does my change break any step in this flow?**

### 3. No Implicit State Between Requests
This app is stateless. Do not introduce file persistence between requests unless explicitly asked.
If a fix requires persisting state, flag it and discuss the design first.

### 4. Test Each Fix in Isolation
For every bug fix:
- Write or describe a test case that would have caught the bug
- Confirm the fix passes that test
- Confirm no existing behaviour changes

### 5. After Batch Fixes — Regression Check
When fixing multiple issues at once:
- List every change made
- For each change, explicitly state: "This cannot break X because..."
- If you cannot confidently make that statement, flag it as a risk

### 6. Validate `secure_filename` Output
`secure_filename()` can return an empty string. Always check:
```python
filename = secure_filename(raw_name)
if not filename:
    return jsonify({'error': 'Invalid filename'}), 400
```

### 7. Error Handling Hierarchy
In `extract_text_from_pdf`, re-raise `FileNotFoundError` separately so callers
can return a 404 instead of 422. Never swallow `FileNotFoundError` in a broad `except Exception`.

## What NOT To Do
- Do not delete files in `/upload` if `/query` still reads from disk (check the flow first)
- Do not add `debug=True` hardcoded — use `FLASK_DEBUG` env var
- Do not hardcode model names, token limits, or folder paths — use env vars / constants
- Do not use `request.json` directly — use `request.get_json(silent=True)` and null-check

## Running Locally
```bash
pip install -r requirements.txt
OPENAI_API_KEY=sk-... python upload_and_extract.py
```

## Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | required | OpenAI authentication |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Model to use |
| `OPENAI_MAX_TOKENS` | `500` | Max tokens in response |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
