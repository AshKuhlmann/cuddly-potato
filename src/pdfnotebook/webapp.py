"""Flask-powered web interface for the Pdf Notebook Assistant."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any
from datetime import datetime

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory,
    Response,
)
from werkzeug.utils import secure_filename

from .db import DatabaseManager, GeneralEntry, PageEntry
from .pdf_processor import ensure_page_splits
import shutil

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PACKAGE_ROOT / "data"
UPLOAD_ROOT = DATA_ROOT / "uploads"
SPLIT_ROOT = DATA_ROOT / "split_pages"
DB_PATH = DATA_ROOT / "notes.db"

DATA_ROOT.mkdir(parents=True, exist_ok=True)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
SPLIT_ROOT.mkdir(parents=True, exist_ok=True)

db_manager = DatabaseManager(DB_PATH)

# Ensure global general document exists
if not db_manager.get_document("global-general"):
    db_manager.create_document(
        "global-general",
        "General Notebook",
        Path("general_notebook_dummy"),
        0
    )

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.config["JSON_SORT_KEYS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_ROOT
app.config["ATTACHMENTS_FOLDER"] = UPLOAD_ROOT / "attachments"
app.config["ATTACHMENTS_FOLDER"].mkdir(parents=True, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64MB limit


def _document_payload(doc: Any) -> dict[str, Any]:
    return {
        "id": doc.doc_id,
        "name": doc.name,
        "page_count": doc.page_count,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
        "source_path": doc.source_path,
    }


def _general_payload(entry: GeneralEntry) -> dict[str, Any]:
    return {
        "author": entry.author,
        "user_input": entry.user_input,
        "output": entry.output,
        "tags": entry.tags,
        "created_at": entry.created_at.isoformat(),
        "attachment_path": entry.attachment_path,
    }


def _page_entry_payload(entry: PageEntry) -> dict[str, Any]:
    return {
        "page_number": entry.page_number,
        "author": entry.author,
        "user_input": entry.user_input,
        "output": entry.output,
        "complete": entry.complete,
        "ignored": entry.ignored,
        "tags": entry.tags,
        "created_at": entry.created_at.isoformat(),
        "attachment_path": entry.attachment_path,
    }


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/test-ui")
def test_ui() -> str:
    return render_template("test_ui.html")


@app.route("/api/documents", methods=["GET"])
def list_documents() -> Any:
    docs = db_manager.list_documents()
    return jsonify({"documents": [_document_payload(doc) for doc in docs]})


@app.route("/attachments/<path:filename>")
def get_attachment(filename: str) -> Response:
    return send_from_directory(app.config["ATTACHMENTS_FOLDER"], filename)


@app.route("/api/documents", methods=["POST"])
def upload_document() -> Any:
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Provide a PDF file."}), 400

    doc_name = request.form.get("name") or Path(file.filename).stem
    doc_id = uuid.uuid4().hex
    destination = UPLOAD_ROOT / f"{doc_id}.pdf"
    file.save(destination)

    split_dir = SPLIT_ROOT / doc_id
    page_files = ensure_page_splits(destination, split_dir)
    db_manager.create_document(doc_id, doc_name, destination, len(page_files))
    db_manager.ensure_page_entries(doc_id, len(page_files))
    return jsonify({"doc_id": doc_id, "name": doc_name})


@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str) -> Any:
    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)
    upload_path = Path(doc.source_path)
    split_dir = SPLIT_ROOT / doc_id
    if upload_path.exists():
        try:
            upload_path.unlink()
        except Exception:
            pass
    if split_dir.exists():
        shutil.rmtree(split_dir, ignore_errors=True)
    # Also delete attachments for this doc_id
    doc_attachments_folder = app.config["ATTACHMENTS_FOLDER"] / doc_id
    if doc_attachments_folder.exists():
        shutil.rmtree(doc_attachments_folder, ignore_errors=True)
    db_manager.delete_document(doc_id)
    return jsonify({"deleted": doc_id})


@app.route("/api/pages/<doc_id>", methods=["GET"])
def get_pages(doc_id: str) -> Any:
    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)

    notes = db_manager.fetch_page_notes(doc_id)
    pages = []
    for note in notes:
        pages.append(
            {
                "page_number": note.page_number,
                "complete": note.complete,
                "ignored": note.ignored,
                "skipped": note.skipped,
                "entry_count": db_manager.get_entry_count(doc_id, note.page_number),
            }
        )

    return jsonify(
        {
            "document": _document_payload(doc),
            "pages": pages,
        }
    )


@app.route("/api/general/<doc_id>", methods=["GET"])
def list_general_entries(doc_id: str) -> Any:
    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)
    entries = db_manager.list_general_entries(doc_id)
    latest = db_manager.get_latest_general_entry(doc_id)
    return jsonify(
        {
            "entries": [_general_payload(entry) for entry in entries],
            "latest": _general_payload(latest) if latest else None,
        }
    )


@app.route("/api/general", methods=["POST"])
def add_general_entry() -> Response:
    if request.is_json:
        data = request.json
        attachment_path = None
    else:
        data = request.form
        file = request.files.get("attachment")
        attachment_path = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            doc_folder = app.config["ATTACHMENTS_FOLDER"] / data["doc_id"]
            doc_folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            save_name = f"{timestamp}_{filename}"
            file.save(doc_folder / save_name)
            attachment_path = f"{data['doc_id']}/{save_name}"

    doc_id = data.get("doc_id")
    if not doc_id:
        return jsonify({"error": "doc_id is required."}), 400

    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)

    db_manager.add_general_entry(
        doc_id=data["doc_id"],
        author=data.get("author", ""),
        user_input=data.get("user_input", ""),
        output=data.get("output", ""),
        tags=data.get("tags", ""),
        attachment_path=attachment_path,
    )
    return jsonify({"status": "ok"})


@app.route("/api/entry/latest/<doc_id>", methods=["GET"])
def latest_page_entry(doc_id: str) -> Any:
    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)
    entry = db_manager.get_latest_page_entry(doc_id)
    if not entry:
        return jsonify({"error": "No page entries yet."}), 404
    return jsonify({"entry": _page_entry_payload(entry)})


@app.route("/api/entry/random/<doc_id>", methods=["GET"])
def random_page_entry(doc_id: str) -> Any:
    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)
    entry = db_manager.get_random_page_entry(doc_id)
    if not entry:
        return jsonify({"error": "No page entries available."}), 404
    return jsonify({"entry": _page_entry_payload(entry)})


@app.route("/api/pages/<doc_id>/<int:page_number>", methods=["GET"])
def get_page(doc_id: str, page_number: int) -> Any:
    notes = db_manager.fetch_page_notes(doc_id)
    page = next((page for page in notes if page.page_number == page_number), None)
    if not page:
        abort(404)
    return jsonify(
        {
        "page": {
            "page_number": page.page_number,
            "author": page.author,
            "user_input": page.user_input,
            "output": page.output,
            "complete": page.complete,
            "ignored": page.ignored,
            "skipped": page.skipped,
            "tags": page.tags,
            "updated_at": page.updated_at.isoformat(),
            "attachment_path": page.attachment_path,
            }
        }
    )


@app.route("/api/entry", methods=["POST"])
def add_entry() -> Response:
    """Record a new entry for a page (history + current state)."""
    # Check if it's a JSON request or Multipart
    if request.is_json:
        data = request.json
        attachment_path = None
    else:
        data = request.form
        file = request.files.get("attachment")
        attachment_path = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Create doc-specific folder
            doc_folder = app.config["ATTACHMENTS_FOLDER"] / data["doc_id"]
            doc_folder.mkdir(parents=True, exist_ok=True)

            # Save file
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            save_name = f"{timestamp}_{filename}"
            file.save(doc_folder / save_name)
            attachment_path = f"{data['doc_id']}/{save_name}"

    doc_id = data.get("doc_id")
    page_number = data.get("page_number")

    if not doc_id or not page_number:
        return jsonify({"error": "doc_id and page_number are required."}), 400

    # Also update the current note state
    db_manager.upsert_page_note(
        doc_id=data["doc_id"],
        page_number=int(data["page_number"]),
        author=data.get("author", ""),
        user_input=data.get("user_input", ""),
        output=data.get("output", ""),
        complete=bool(data.get("complete", False)),
        tags=data.get("tags", ""),
        attachment_path=attachment_path,
    )

    # Add to history
    notes = db_manager.fetch_page_notes(doc_id)
    note = next((note for note in notes if note.page_number == int(page_number)), None)
    
    # Fix: retrieve values from data dictionary
    user_input = data.get("user_input", "")
    output = data.get("output", "")
    complete = bool(data.get("complete", False))
    tags = data.get("tags", "")

    db_manager.add_page_entry(
        doc_id,
        int(page_number),
        data.get("author", ""),
        user_input,
        output,
        complete,
        bool(note.ignored) if note else False,
        tags,
        attachment_path
    )
    
    # Fix: get actual count
    entries_count = db_manager.get_entry_count(doc_id, int(page_number))
    return jsonify({"entry_count": entries_count})


@app.route("/api/ignore", methods=["POST"])
def toggle_ignore() -> Any:
    payload = request.get_json(force=True)
    doc_id = payload.get("doc_id")
    page_number = payload.get("page_number")
    ignored = bool(payload.get("ignored"))

    if not doc_id or not page_number:
        return jsonify({"error": "doc_id and page_number are required."}), 400

    db_manager.set_page_ignored(doc_id, page_number, ignored)
    return jsonify({"ignored": ignored})


@app.route("/api/skip", methods=["POST"])
def toggle_skip() -> Any:
    payload = request.get_json(force=True)
    doc_id = payload.get("doc_id")
    page_number = payload.get("page_number")
    skipped = bool(payload.get("skipped"))

    if not doc_id or not page_number:
        return jsonify({"error": "doc_id and page_number are required."}), 400

    db_manager.set_page_skipped(doc_id, page_number, skipped)
    return jsonify({"skipped": skipped})


@app.route("/api/resume/<doc_id>", methods=["GET"])
def resume(doc_id: str) -> Any:
    page = db_manager.get_first_incomplete(doc_id)
    if not page:
        return jsonify({"page_number": None})
    return jsonify({"page_number": page.page_number})


@app.route("/pages/<doc_id>/<int:page_number>", methods=["GET"])
def serve_page_pdf(doc_id: str, page_number: int) -> Any:
    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)

    split_dir = SPLIT_ROOT / doc_id
    filename = f"page_{page_number:03}.pdf"
    if not (split_dir / filename).exists():
        abort(404)
    return send_from_directory(split_dir, filename, as_attachment=False)
