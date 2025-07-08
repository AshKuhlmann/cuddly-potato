import sqlite3
import json
from datetime import datetime


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
    """Creates the Youtubes table if it doesn't exist."""
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS Youtubes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    model TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    date TEXT NOT NULL,
                    domain TEXT,
                    subdomain TEXT,
                    comments TEXT,
                    UNIQUE(question, model)
                )
            """
            )
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to create table: {e}")


def add_entry(conn, question, model, answer, domain, subdomain, comments):
    """Adds a new question-answer pair to the database."""
    with conn:
        try:
            conn.execute(
                """
                INSERT INTO Youtubes (question, model, answer, date, domain, subdomain, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    question,
                    model,
                    answer,
                    datetime.now().isoformat(),
                    domain,
                    subdomain,
                    comments,
                ),
            )
        except sqlite3.IntegrityError:
            raise DatabaseError("This question for this model already exists.")
        except sqlite3.Error as e:
            raise DatabaseError(f"An unexpected database error occurred: {e}")


def update_entry(conn, entry_id, question, model, answer, domain, subdomain, comments):
    """Updates an existing entry in the database."""
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Youtubes WHERE id = ?", (entry_id,))
        if cursor.fetchone() is None:
            raise DatabaseError(f"No entry found with id {entry_id}.")

        updates = []
        params = []
        if question:
            updates.append("question = ?")
            params.append(question)
        if model:
            updates.append("model = ?")
            params.append(model)
        if answer:
            updates.append("answer = ?")
            params.append(answer)
        if domain:
            updates.append("domain = ?")
            params.append(domain)
        if subdomain:
            updates.append("subdomain = ?")
            params.append(subdomain)
        if comments:
            updates.append("comments = ?")
            params.append(comments)

        if not updates:
            return

        params.append(entry_id)

        try:
            conn.execute(
                f"""
                UPDATE Youtubes
                SET {', '.join(updates)}
                WHERE id = ?
            """,
                tuple(params),
            )
        except sqlite3.IntegrityError:
            raise DatabaseError(
                "Update would create a duplicate question for the same model."
            )
        except sqlite3.Error as e:
            raise DatabaseError(
                f"An unexpected database error occurred during update: {e}"
            )


def export_to_json(conn, output_path):
    """Exports all question-answer pairs to a JSON file."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Youtubes")
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        raise DatabaseError(f"Could not write to file '{output_path}': {e}")
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to fetch data for export: {e}")
