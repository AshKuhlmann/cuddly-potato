"""A persistence layer that tracks PDF documents, pages, and entry history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import sqlite3


@dataclass
class Document:
    """Metadata for an uploaded PDF document."""

    doc_id: str
    name: str
    source_path: str
    page_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class PageNote:
    """The most recent annotation state for a single page."""

    id: int
    doc_id: str
    page_number: int
    author: str
    user_input: str
    output: str
    complete: bool
    ignored: bool
    tags: str
    skipped: bool
    attachment_path: Optional[str]
    updated_at: datetime


@dataclass
class PageEntry:
    """A saved entry that belongs to a particular page."""

    doc_id: str
    page_number: int
    author: str
    user_input: str
    output: str
    complete: bool
    ignored: bool
    tags: str
    created_at: datetime


@dataclass
class GeneralEntry:
    doc_id: str
    author: str
    user_input: str
    output: str
    tags: str
    created_at: datetime


class DatabaseManager:
    """Helper around SQLite that keeps documents, pages, and entries synchronized."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_path TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS page_notes (
                id INTEGER PRIMARY KEY,
                doc_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                author TEXT DEFAULT '',
                user_input TEXT DEFAULT '',
            output TEXT DEFAULT '',
            complete INTEGER DEFAULT 0,
            ignored INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            tags TEXT DEFAULT '',
            attachment_path TEXT,
            updated_at TEXT NOT NULL,
            UNIQUE(doc_id, page_number),
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS page_entries (
                id INTEGER PRIMARY KEY,
                doc_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                author TEXT DEFAULT '',
                user_input TEXT DEFAULT '',
                output TEXT DEFAULT '',
                complete INTEGER DEFAULT 0,
                ignored INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                attachment_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS general_entries (
                id INTEGER PRIMARY KEY,
                doc_id TEXT NOT NULL,
                author TEXT DEFAULT '',
                user_input TEXT DEFAULT '',
                output TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                attachment_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
            """
        )
        self.connection.commit()
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        expectations = {
            "page_notes": {
                "tags": "TEXT DEFAULT ''",
                "skipped": "INTEGER DEFAULT 0",
                "attachment_path": "TEXT",
            },
            "page_entries": {
                "tags": "TEXT DEFAULT ''",
                "attachment_path": "TEXT",
            },
            "general_entries": {
                "attachment_path": "TEXT",
            },
        }
        for table, columns in expectations.items():
            cursor = self.connection.execute(f"PRAGMA table_info({table})")
            existing = {row["name"] for row in cursor}
            for name, definition in columns.items():
                if name not in existing:
                    self.connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                    )
        self.connection.commit()

    def create_document(
        self, doc_id: str, name: str, source_path: Path, page_count: int
    ) -> None:
        """Add metadata for a new document."""
        now = datetime.utcnow().isoformat()
        self.connection.execute(
            """
            INSERT OR REPLACE INTO documents
                (doc_id, name, source_path, page_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (doc_id, name, str(source_path), page_count, now, now),
        )
        self.connection.commit()

    def list_documents(self) -> List[Document]:
        """Return every uploaded PDF sorted by creation time descending."""
        cursor = self.connection.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        )
        return [self._row_to_document(row) for row in cursor.fetchall()]

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Load the document identified by ``doc_id``."""
        cursor = self.connection.execute(
            "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
        )
        row = cursor.fetchone()
        return self._row_to_document(row) if row else None

    def delete_document(self, doc_id: str) -> None:
        """Remove a document and cascade the clean-up through SQLite."""
        self.connection.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        self.connection.commit()

    def ensure_page_entries(self, doc_id: str, total_pages: int) -> None:
        """Populate every page for the document if the row is missing."""
        now = datetime.utcnow().isoformat()
        insert = """
        INSERT OR IGNORE INTO page_notes (doc_id, page_number, updated_at)
        VALUES (?, ?, ?)
        """
        for page_number in range(1, total_pages + 1):
            self.connection.execute(insert, (doc_id, page_number, now))
        self.connection.commit()

    def upsert_page_note(
        self,
        doc_id: str,
        page_number: int,
        author: str,
        user_input: str,
        output: str,
        complete: bool,
        tags: str,
        attachment_path: Optional[str] = None,
    ) -> None:
        """Update the current metadata for a page and refresh the document timestamp."""
        now = datetime.utcnow().isoformat()
        self.connection.execute(
            """
            INSERT INTO page_notes
                (doc_id, page_number, author, user_input, output, complete, tags, attachment_path, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id, page_number) DO UPDATE SET
                author=excluded.author,
                user_input=excluded.user_input,
                output=excluded.output,
                complete=excluded.complete,
                tags=excluded.tags,
                attachment_path=excluded.attachment_path,
                updated_at=excluded.updated_at
            """,
            (
                doc_id,
                page_number,
                author,
                user_input,
                output,
                int(complete),
                tags,
                attachment_path,
                now,
            ),
        )
        self.connection.execute(
            "UPDATE documents SET updated_at = ? WHERE doc_id = ?", (now, doc_id)
        )
        self.connection.commit()

    def add_page_entry(
        self,
        doc_id: str,
        page_number: int,
        author: str,
        user_input: str,
        output: str,
        complete: bool,
        ignored: bool,
        tags: str,
        attachment_path: Optional[str] = None,
    ) -> None:
        """Persist a historical entry for auditing or review."""
        now = datetime.utcnow().isoformat()
        self.connection.execute(
            """
            INSERT INTO page_entries
                (doc_id, page_number, author, user_input, output, complete, ignored, tags, attachment_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                page_number,
                author,
                user_input,
                output,
                int(complete),
                int(ignored),
                tags,
                attachment_path,
                now,
            ),
        )
        self.connection.commit()

    def get_latest_page_entry(self, doc_id: str) -> Optional[PageEntry]:
        cursor = self.connection.execute(
            """
            SELECT * FROM page_entries
            WHERE doc_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (doc_id,),
        )
        row = cursor.fetchone()
        return self._row_to_page_entry(row) if row else None

    def get_random_page_entry(self, doc_id: str) -> Optional[PageEntry]:
        cursor = self.connection.execute(
            """
            SELECT * FROM page_entries
            WHERE doc_id = ?
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (doc_id,),
        )
        row = cursor.fetchone()
        return self._row_to_page_entry(row) if row else None

    def add_general_entry(
        self,
        doc_id: str,
        author: str,
        user_input: str,
        output: str,
        tags: str,
        attachment_path: Optional[str] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        self.connection.execute(
            """
            INSERT INTO general_entries
                (doc_id, author, user_input, output, tags, attachment_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, author, user_input, output, tags, attachment_path, now),
        )
        self.connection.commit()

    def list_general_entries(self, doc_id: str, limit: int = 20) -> List[GeneralEntry]:
        cursor = self.connection.execute(
            "SELECT * FROM general_entries WHERE doc_id = ? ORDER BY created_at DESC LIMIT ?",
            (doc_id, limit),
        )
        return [self._row_to_general_entry(row) for row in cursor.fetchall()]

    def get_latest_general_entry(self, doc_id: str) -> Optional[GeneralEntry]:
        cursor = self.connection.execute(
            "SELECT * FROM general_entries WHERE doc_id = ? ORDER BY created_at DESC LIMIT 1",
            (doc_id,),
        )
        row = cursor.fetchone()
        return self._row_to_general_entry(row) if row else None

    def get_entry_count(self, doc_id: str, page_number: int) -> int:
        """Return how many entries exist for this document page."""
        cursor = self.connection.execute(
            "SELECT COUNT(*) FROM page_entries WHERE doc_id = ? AND page_number = ?",
            (doc_id, page_number),
        )
        return int(cursor.fetchone()[0] or 0)

    def set_page_ignored(
        self, doc_id: str, page_number: int, ignored: bool
    ) -> None:
        """Toggle the ignored flag so resume will skip the page."""
        self.connection.execute(
            """
            UPDATE page_notes SET ignored = ? WHERE doc_id = ? AND page_number = ?
            """,
            (int(ignored), doc_id, page_number),
        )
        self.connection.commit()

    def set_page_skipped(
        self, doc_id: str, page_number: int, skipped: bool
    ) -> None:
        """Mark a page as skipped (yellow queue) without removing it from resume logic."""
        self.connection.execute(
            """
            UPDATE page_notes SET skipped = ? WHERE doc_id = ? AND page_number = ?
            """,
            (int(skipped), doc_id, page_number),
        )
        self.connection.commit()

    def fetch_page_notes(self, doc_id: str) -> List[PageNote]:
        """Return a complete list of page notes for rendering the UI."""
        cursor = self.connection.execute(
            "SELECT * FROM page_notes WHERE doc_id = ? ORDER BY page_number",
            (doc_id,),
        )
        return [self._row_to_note(row) for row in cursor.fetchall()]

    def get_first_incomplete(self, doc_id: str) -> Optional[PageNote]:
        """Return the earliest page that is neither complete nor ignored."""
        cursor = self.connection.execute(
            "SELECT * FROM page_notes WHERE doc_id = ? AND complete = 0 AND ignored = 0 ORDER BY page_number LIMIT 1",
            (doc_id,),
        )
        row = cursor.fetchone()
        return self._row_to_note(row) if row else None

    def _row_to_note(self, row: sqlite3.Row) -> PageNote:
        return PageNote(
            id=row["id"],
            doc_id=row["doc_id"],
            page_number=row["page_number"],
            author=row["author"],
            user_input=row["user_input"],
            output=row["output"],
            complete=bool(row["complete"]),
            ignored=bool(row["ignored"]),
            skipped=bool(row["skipped"]),
            tags=row["tags"],
            attachment_path=row["attachment_path"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        return Document(
            doc_id=row["doc_id"],
            name=row["name"],
            source_path=row["source_path"],
            page_count=row["page_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_general_entry(self, row: sqlite3.Row) -> GeneralEntry:
        return GeneralEntry(
            doc_id=row["doc_id"],
            author=row["author"],
            user_input=row["user_input"],
            output=row["output"],
            tags=row["tags"],
            attachment_path=row["attachment_path"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_page_entry(self, row: sqlite3.Row) -> PageEntry:
        return PageEntry(
            doc_id=row["doc_id"],
            page_number=row["page_number"],
            author=row["author"],
            user_input=row["user_input"],
            output=row["output"],
            complete=bool(row["complete"]),
            ignored=bool(row["ignored"]),
            tags=row["tags"],
            attachment_path=row["attachment_path"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def close(self) -> None:
        self.connection.close()
