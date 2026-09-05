# NoteDistill — Smart Notes from your PDFs

A full-stack website where students sign up, upload a PDF of their notes,
and get back a condensed "Smart Notes" PDF that highlights important topics
and key terms — no AI API key required (uses heading + keyword-frequency
detection).

## Features
- User accounts (sign up / log in) with hashed passwords
- Upload any text-based PDF of notes
- Automatic detection of headings/sections
- Important-topic and keyword extraction (frequency + heuristics)
- Auto-generated, highlighted "Smart Notes" PDF for download
- Per-user history of everything you've uploaded, stored in SQLite

## Tech stack
- **Backend:** Python, Flask
- **Database:** SQLite (file-based, zero setup)
- **PDF reading:** pdfplumber
- **PDF generation:** reportlab
- **Frontend:** server-rendered HTML/CSS (Jinja2 templates), no build step

## Project structure
study-notes-app/
├── app.py # Flask routes (auth, upload, dashboard, download)
├── db.py # SQLite connection + schema
├── extractor.py # PDF text extraction + topic/summary logic
├── pdf_generator.py # Builds the output "Smart Notes" PDF
├── templates/ # HTML pages
├── static/style.css # Styling
├── uploads/ # Temp storage for incoming PDFs (auto-cleared)
├── generated/ # Generated Smart Notes PDFs (served to users)
├── instance/ # SQLite database file lives here (auto-created)
└── requirements.txt

## Setup & run locally

1. **Install Python 3.10+** if you don't have it.
2. Create a virtual environment and install dependencies:
```bash
   cd study-notes-app
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
```
3. Run the app:
```bash
   python app.py
```
4. Open **http://localhost:5000** in your browser, sign up, and start
   uploading PDFs.

The SQLite database (`instance/app.db`) is created automatically on first run.

## How the "important topics" detection works (no AI needed)

1. **Extract text** from each page with `pdfplumber`.
2. **Detect headings** using heuristics: numbered lines ("1.2 ..."),
   ALL-CAPS lines, "Chapter/Unit/Section ..." lines, and short Title-Case
   lines.
3. **Group text into sections** under each detected heading.
4. **Score keywords** by frequency across the document (common stopwords
   removed), with a boost for words that are Capitalized mid-sentence
   (usually technical terms or proper nouns, e.g. "Chloroplast", "Newton").
5. **Build a short summary per section** by picking the first few sentences
   plus the longest (usually most information-dense) sentence.
6. **Generate the output PDF** with an "Important Topics" bullet list up top,
   followed by condensed per-section notes with key terms bolded in orange.

This is intentionally dependency-free (no external AI API), so it works
instantly and offline. If you later want smarter, more accurate summaries,
swap the logic in `extractor.py`'s `process_pdf()` for a call to an LLM API
(e.g. the Anthropic API) — the rest of the app (auth, DB, PDF generation,
UI) doesn't need to change.

## Deploying so students can access it online

This is a standard Flask app, so it deploys anywhere that runs Python:
- **Render** or **Railway** — easiest, free tiers available, connect your
  GitHub repo and it auto-detects `requirements.txt` + `app.py`.
- **PythonAnywhere** — good for quick, always-on free hosting.
- **Your own VPS** — run with `gunicorn app:app` behind Nginx.

Before deploying:
- Set a real `SECRET_KEY` environment variable (don't use the dev default).
- For multiple users at scale, consider swapping SQLite for Postgres
  (the `db.py` queries are plain SQL and port over easily).
- Make sure `uploads/` and `generated/` are on persistent storage (or
  swap to S3/cloud storage) if your host uses ephemeral disks.

## Notes & limitations
- Works on **text-based PDFs**. Scanned/image-only PDFs won't have
  extractable text (would need OCR — see the OCR snippet in
  `/mnt/skills/public/pdf/SKILL.md` if you want to add that later).
- The "important topics" logic is heuristic-based (fast, free, no API key),
  not true AI summarization — good enough for headings/keywords, but not
  as smart as an LLM-based summary.
- Upload size capped at 20 MB (edit `MAX_CONTENT_LENGTH` in `app.py` to change).
