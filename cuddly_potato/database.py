import sqlite3
import json
from datetime import datetime
from openpyxl import Workbook


class DatabaseError(Exception):
    """Custom exception for database errors."""

    pass


def get_db_connection(db_path="cuddly_potato.db"):
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Could not connect to database at '{db_path}': {e}")


def create_table(conn):
    """Creates the entries table if it doesn't exist."""
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author TEXT NOT NULL,
                    tags TEXT,
                    context TEXT,
                    question TEXT NOT NULL,
                    reason TEXT,
                    answer TEXT NOT NULL,
                    date TEXT NOT NULL
                )
            """
            )
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to create table: {e}")


def add_entry(conn, author, tags, context, question, reason, answer):
    """Adds a new entry to the database."""
    with conn:
        try:
            conn.execute(
                """
                INSERT INTO entries (author, tags, context, question, reason, answer, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    author,
                    tags,
                    context,
                    question,
                    reason,
                    answer,
                    datetime.now().isoformat(),
                ),
            )
        except sqlite3.Error as e:
            raise DatabaseError(f"An unexpected database error occurred: {e}")


def get_last_entry(conn):
    """Retrieves the most recent entry from the database."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM entries ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to fetch last entry: {e}")


def update_entry(conn, entry_id, author, tags, context, question, reason, answer):
    """Updates an existing entry in the database."""
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM entries WHERE id = ?", (entry_id,))
        if cursor.fetchone() is None:
            raise DatabaseError(f"No entry found with id {entry_id}.")

        updates = []
        params = []
        if author:
            updates.append("author = ?")
            params.append(author)
        if tags is not None:  # Allow empty string
            updates.append("tags = ?")
            params.append(tags)
        if context is not None:  # Allow empty string
            updates.append("context = ?")
            params.append(context)
        if question:
            updates.append("question = ?")
            params.append(question)
        if reason is not None:  # Allow empty string
            updates.append("reason = ?")
            params.append(reason)
        if answer:
            updates.append("answer = ?")
            params.append(answer)

        if not updates:
            return

        params.append(entry_id)

        try:
            conn.execute(
                f"""
                UPDATE entries
                SET {', '.join(updates)}
                WHERE id = ?
            """,
                tuple(params),
            )
        except sqlite3.Error as e:
            raise DatabaseError(
                f"An unexpected database error occurred during update: {e}"
            )


def export_to_json(conn, output_path):
    """Exports all entries to a JSON file."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entries")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        raise DatabaseError(f"Could not write to file '{output_path}': {e}")
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to fetch data for export: {e}")


def export_to_excel(conn, output_path):
    """Exports all entries to an Excel file."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entries")
        rows = cursor.fetchall()

        # Create workbook and worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Entries"

        # Write headers
        headers = ["ID", "Author", "Tags", "Context", "Question", "Reason", "Answer", "Date"]
        ws.append(headers)

        # Write data rows
        for row in rows:
            ws.append([
                row["id"],
                row["author"],
                row["tags"],
                row["context"],
                row["question"],
                row["reason"],
                row["answer"],
                row["date"]
            ])

        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
            ws.column_dimensions[column_letter].width = adjusted_width

        wb.save(output_path)
    except IOError as e:
        raise DatabaseError(f"Could not write to file '{output_path}': {e}")
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to fetch data for export: {e}")
    except Exception as e:
        raise DatabaseError(f"Failed to create Excel file: {e}")
