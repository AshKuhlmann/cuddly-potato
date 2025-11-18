# Cuddly Potato

Cuddly Potato is a local Flask-based helper that lets you upload a PDF, slice it into one-page nuggets, annotate each page with structured entries, and keep everything resumed safely inside a beautiful dark UI. You can connect over the LAN or stay on the host machine—the app keeps the history in SQLite so you can pick up anywhere.

## Features

- Upload any PDF and have the server write `data/uploads/<uuid>.pdf` plus page splits under `data/split_pages/<uuid>/page_###.pdf`.
- Track per-page metadata (author, tags, user input, output, complete/ignored/skipped flags) and log each entry for auditing; general entries live in their own table.
- Dark SPA with document selection, progress bar, skip markers, preview toggle, clipboard export, general mode, and entry snapshot controls.
- Delete a document when you’re done with the built-in ✕ control; it confirms before purging splits/metadata.
- Explicit download and preview actions mean nothing auto-downloads unless you ask for it.

## Quickstart

```bash
python -m venv .venv        # optional but keeps dependencies isolated
source .venv/bin/activate   # mac/linux
pip install -r requirements.txt
python main.py
```

By default the Flask server listens on `0.0.0.0:5050`, so access `http://localhost:5050` here or `http://<your-ip>:5050` from another LAN device.

### Upload & select

1. Use the sidebar form to upload a PDF and optionally name the session—the app writes each page to `data/split_pages/<doc-id>/page_###.pdf`.
2. The dropdown and list show every document (newest first) along with a “New document” option—choose “New document” to reveal the upload form, pick a session to load its pages, or use “None” to clear the selection so only general mode remains.
3. Hit the ✕ on a document row to delete everything associated with that session after confirming.

### Page work

1. Select a page to see a compact preview placeholder (it only expands after you click *Show preview*), the metadata form, and skip/ignore indicators.
2. Enter **Author**, **Tags** (comma-separated), **User Input**, and **Output**. Toggle **Mark complete** as needed.
3. **Save Entry** persists the row and increments the entry count. **Save & Next** does the same and moves to the next page. **New Entry** clears the text areas but keeps author/tags so you can jot multiple ideas per page.
4. **Skip Page** flags the page with a yellow badge (and the progress bar reflects skipped pages); it remains selectable if you want to revisit it later.
5. **Ignore Page** removes the page from automatic resume/next flows until you unignore it.
6. **Copy Page to Clipboard** pushes the current split page as a PDF blob to Chromium/Safari. **Download current page** (located beneath the preview toggle) opens the split PDF in a new tab only after you confirm, and **Show preview** reveals the iframe (or hides it when clicked again).

### Navigation

1. **Resume Next** jumps to the first page that is neither complete nor ignored.
2. **Next Entry** just moves to the following page in order.
3. The progress bar below the header shows how far you are (complete vs skipped).
4. The Entry Snapshot pane toggles between the latest or a random saved entry so you can glance at recent work without scrolling.

### General mode

1. When no document is selected or you hit the *General mode* button (located beside the dropdown), the document workspace collapses and the general-entry panel appears.
2. General entries capture author/tags/input/output without a page reference, and the form auto-fills with the last general author/tag you used.
3. Use general mode for process notes, follow-up tasks, or high-level summaries while still having the per-page context available when you reselect a document.

## Project layout

```
cuddly-potato/
├─ data/
│  ├─ notes.db            # SQLite storage (created at runtime)
│  ├─ uploads/            # Uploaded PDFs
│  └─ split_pages/
│     └─ <doc-id>/
│        └─ page_001.pdf ...
├─ scripts/
│  └─ generate_icon.py     # Rebuilds the UI icon
├─ src/pdfnotebook/
│  ├─ db.py                # Persistence helpers
│  ├─ pdf_processor.py     # Splitting logic
│  ├─ static/
│  │  ├─ app.css
│  │  ├─ app.js
│  │  └─ app_icon.png
│  ├─ templates/
│  │  └─ index.html
│  └─ webapp.py            # Flask app + API
├─ main.py                 # Launches Flask server
├─ README.md
├─ requirements.txt
└─ pyproject.toml
```

## Troubleshooting

- PDF upload fails? Ensure the browser posts a `.pdf` and that the file isn’t locked—PyPDF2 handles the splitting.
- Clipboard copy doesn’t work? The browser must expose `navigator.clipboard.write()` for binary blobs.
- Data looks stale or corrupt? Stop the server, delete `data/notes.db`, and restart; the splits remain so you can rebuild the metadata.
- Need to regenerate the icon? Run `python scripts/generate_icon.py`.
