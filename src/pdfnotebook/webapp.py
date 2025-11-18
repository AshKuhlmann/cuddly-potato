"""Flask-powered web interface for the Pdf Notebook Assistant."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

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

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.config["JSON_SORT_KEYS"] = False


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
    }


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/documents", methods=["GET"])
def list_documents() -> Any:
    docs = db_manager.list_documents()
    return jsonify({"documents": [_document_payload(doc) for doc in docs]})


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
def save_general_entry() -> Any:
    payload = request.get_json(force=True)
    doc_id = payload.get("doc_id")
    author = payload.get("author", "").strip()
    user_input = payload.get("user_input", "").strip()
    output = payload.get("output", "").strip()
    tags = payload.get("tags", "").strip()

    if not doc_id:
        return jsonify({"error": "doc_id is required."}), 400

    doc = db_manager.get_document(doc_id)
    if not doc:
        abort(404)

    db_manager.add_general_entry(doc_id, author, user_input, output, tags)
    entries = db_manager.list_general_entries(doc_id)
    latest = db_manager.get_latest_general_entry(doc_id)
    return jsonify({
        "entries": [_general_payload(entry) for entry in entries],
        "latest": _general_payload(latest) if latest else None,
    })


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
            }
        }
    )


@app.route("/api/entry", methods=["POST"])
def save_entry() -> Any:
    payload = request.get_json(force=True)
    doc_id = payload.get("doc_id")
    page_number = payload.get("page_number")
    author = payload.get("author", "").strip()
    user_input = payload.get("user_input", "").strip()
    output = payload.get("output", "").strip()
    complete = bool(payload.get("complete"))
    tags = payload.get("tags", "").strip()

    if not doc_id or not page_number:
        return jsonify({"error": "doc_id and page_number are required."}), 400

    db_manager.upsert_page_note(
        doc_id, page_number, author, user_input, output, complete, tags
    )
    entries = db_manager.get_entry_count(doc_id, page_number)
    notes = db_manager.fetch_page_notes(doc_id)
    note = next((note for note in notes if note.page_number == page_number), None)
    db_manager.add_page_entry(
        doc_id,
        page_number,
        author,
        user_input,
        output,
        complete,
        bool(note.ignored) if note else False,
        tags,
    )
    return jsonify({"entry_count": entries})


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
