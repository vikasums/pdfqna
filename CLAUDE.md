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

---

## Pre-Commit Checklist — 3 Mandatory Passes

Before every commit, run through all three passes. Do not skip. Do not merge on a partial pass.

### Pass 1 — Fix Correctness
For each issue being fixed:
- [ ] Is the fix logically correct in isolation?
- [ ] Does it handle the error/edge case it was meant to address?
- [ ] Are new constants/env vars documented in the table below?

### Pass 2 — End-to-End Flow Trace
Trace the full user journey step by step:
1. `POST /upload`: file present? → extension valid? → filename safe? → save inside try → extract → cleanup in finally → text not empty? → return `{ text }`
2. `POST /query`: JSON valid? → keys present? → truncate text → call OpenAI → guard choices → return `{ answer }`

For each step ask: **does my change affect this step directly or indirectly?**

### Pass 3 — New Issues Introduced?
For each change made:
- [ ] Does it alter the return type or signature of any shared function?
- [ ] Does it change what any caller receives?
- [ ] Does it introduce new unhandled exceptions?
- [ ] Does it add new state (files, globals, caches) that other code depends on?
- [ ] If you cannot answer "no" to all of the above — flag it before committing.

---

## Rules Before Making Any Change

### 1. Map All Consumers First
Before changing a function or endpoint, identify **every caller**:
- Which routes call this function?
- What does each caller expect in return?
- What data does each caller pass in?

Example: before changing `extract_text_from_pdf`, check both `/upload` and any future route that might call it.

### 2. No Implicit State Between Requests
This app is stateless. Do not introduce file persistence between requests unless explicitly asked.
If a fix requires persisting state, flag it and discuss the design first.

### 3. `file.save()` Must Be Inside `try`
So the `finally` cleanup block always runs, even on save failure:
```python
try:
    file.save(filepath)
    text = extract_text_from_pdf(filepath)
except ...:
    ...
finally:
    if os.path.exists(filepath):
        os.remove(filepath)
```

### 4. Always Check for Empty Extracted Text
Image-only PDFs extract to `''`. Always validate after extraction:
```python
if not text.strip():
    return jsonify({'error': 'No text could be extracted...'}), 422
```

### 5. Guard `response.choices` Before Indexing
```python
if not response.choices:
    return jsonify({'error': 'No response received from OpenAI'}), 502
answer = response.choices[0].message.content.strip()
```

### 6. Truncate Text Before Sending to OpenAI
Large PDFs can exceed the model's context window. Always truncate:
```python
text = data['text'][:MAX_TEXT_CHARS]
```

### 7. Validate `secure_filename` Output
`secure_filename()` can return an empty string. Always check:
```python
filename = secure_filename(raw_name)
if not filename:
    return jsonify({'error': 'Invalid filename'}), 400
```

### 8. Error Handling Hierarchy in `extract_text_from_pdf`
Re-raise `FileNotFoundError` separately so callers return 404, not 422.
Never swallow `FileNotFoundError` in a broad `except Exception`.

---

## What NOT To Do
- Do not delete files in `/upload` if `/query` still reads from disk — check the flow first
- Do not add `debug=True` hardcoded — use `FLASK_DEBUG` env var
- Do not hardcode model names, token limits, or folder paths — use env vars / constants
- Do not use `request.json` directly — use `request.get_json(silent=True)` and null-check
- Do not index `response.choices[0]` without first checking `response.choices` is non-empty

---

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
| `MAX_TEXT_CHARS` | `48000` | Max chars of PDF text sent to OpenAI (~12k tokens) |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
