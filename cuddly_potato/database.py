import sqlite3
import json
from datetime import datetime


def get_db_connection(db_path="cuddly_potato.db"):
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_table(conn):
    """Creates the Youtubes table if it doesn't exist."""
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
            return "Entry added successfully."
        except sqlite3.IntegrityError:
            return "Error: This question for this model already exists."


def update_entry(conn, entry_id, question, model, answer, domain, subdomain, comments):
    """Updates an existing entry in the database."""
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Youtubes WHERE id = ?", (entry_id,))
        if cursor.fetchone() is None:
            return f"Error: No entry found with id {entry_id}."

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
            return "No fields to update."

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
            return "Entry updated successfully."
        except sqlite3.IntegrityError:
            return "Error: Update would create a duplicate question for the same model."


def export_to_json(conn, output_path):
    """Exports all question-answer pairs to a JSON file."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Youtubes")
    rows = cursor.fetchall()

    data = [dict(row) for row in rows]

    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)
    return f"Data exported to {output_path}"
