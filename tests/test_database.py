import unittest
import sqlite3
import os
import json
from cuddly_potato.database import (
    create_table,
    add_entry,
    update_entry,
    export_to_json,
    export_to_excel,
    get_last_entry,
    DatabaseError,
    ValidationError,
)


class TestDatabase(unittest.TestCase):

    def setUp(self):
        """Set up a temporary database for testing."""
        self.db_path = "test.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        create_table(self.conn)

    def tearDown(self):
        """Close the connection and remove the temporary database file."""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_add_entry(self):
        """Test adding a new entry."""
        add_entry(
            self.conn,
            "John Doe",
            "python,testing",
            "Unit testing context",
            "What is 2 + 2?",
            "Testing basic math",
            "4",
        )

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entries WHERE question = ?", ("What is 2 + 2?",))
        entry = cursor.fetchone()

        self.assertIsNotNone(entry)
        self.assertEqual(entry["author"], "John Doe")
        self.assertEqual(entry["tags"], "python,testing")
        self.assertEqual(entry["answer"], "4")

    def test_add_entry_with_missing_optional_fields(self):
        """Test adding an entry with only the required fields."""
        add_entry(
            self.conn,
            "Jane Smith",
            "",
            "",
            "Required only?",
            "",
            "Yes",
        )

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM entries WHERE question = ?",
            ("Required only?",),
        )
        entry = cursor.fetchone()

        self.assertIsNotNone(entry)
        self.assertEqual(entry["author"], "Jane Smith")
        self.assertEqual(entry["tags"], "")
        self.assertEqual(entry["context"], "")
        self.assertEqual(entry["reason"], "")

    def test_add_entry_missing_required_field_raises(self):
        """Ensure required fields are validated."""
        with self.assertRaises(ValidationError):
            add_entry(
                self.conn,
                "",
                "",
                "",
                "Question present",
                "",
                "Answer present",
            )

    def test_get_last_entry(self):
        """Test retrieving the last entry."""
        add_entry(
            self.conn,
            "Author1",
            "tag1",
            "context1",
            "Question1",
            "reason1",
            "Answer1",
        )
        add_entry(
            self.conn,
            "Author2",
            "tag2",
            "context2",
            "Question2",
            "reason2",
            "Answer2",
        )

        last_entry = get_last_entry(self.conn)
        self.assertIsNotNone(last_entry)
        self.assertEqual(last_entry["author"], "Author2")
        self.assertEqual(last_entry["question"], "Question2")

    def test_get_last_entry_empty_database(self):
        """Test getting last entry from empty database."""
        last_entry = get_last_entry(self.conn)
        self.assertIsNone(last_entry)

    def test_update_entry(self):
        """Test updating an existing entry."""
        add_entry(
            self.conn,
            "Old Author",
            "old,tags",
            "Old Context",
            "Old Question",
            "Old Reason",
            "Old Answer",
        )

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM entries WHERE question = 'Old Question'")
        entry_id = cursor.fetchone()["id"]

        update_entry(
            self.conn,
            entry_id,
            "New Author",
            "new,tags",
            "New Context",
            "New Question",
            "New Reason",
            "New Answer",
        )

        cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        entry = cursor.fetchone()

        self.assertEqual(entry["author"], "New Author")
        self.assertEqual(entry["question"], "New Question")
        self.assertEqual(entry["tags"], "new,tags")

    def test_update_nonexistent_entry(self):
        """Test updating an entry that does not exist."""
        with self.assertRaises(ValidationError):
            update_entry(
                self.conn, 999, "New Author", None, None, None, None, None
            )

    def test_export_to_json(self):
        """Test exporting data to a JSON file."""
        add_entry(
            self.conn, "Author1", "tag1", "context1", "Q1", "reason1", "A1"
        )
        add_entry(
            self.conn, "Author2", "tag2", "context2", "Q2", "reason2", "A2"
        )

        json_path = "test_export.json"
        export_to_json(self.conn, json_path)

        self.assertTrue(os.path.exists(json_path))

        with open(json_path, "r") as f:
            data = json.load(f)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["author"], "Author1")
            self.assertEqual(data[1]["author"], "Author2")

        os.remove(json_path)

    def test_export_to_excel(self):
        """Test exporting data to an Excel file."""
        add_entry(
            self.conn, "Author1", "tag1", "context1", "Q1", "reason1", "A1"
        )
        add_entry(
            self.conn, "Author2", "tag2", "context2", "Q2", "reason2", "A2"
        )

        excel_path = "test_export.xlsx"
        export_to_excel(self.conn, excel_path)

        self.assertTrue(os.path.exists(excel_path))

        os.remove(excel_path)

    def test_create_table_idempotent(self):
        """Test that calling create_table multiple times doesn't cause errors."""
        try:
            create_table(self.conn)
        except Exception as e:
            self.fail(f"create_table() raised an exception on second call: {e}")

    def test_long_text_fields(self):
        """Test that long text fields are handled correctly."""
        long_text = "A" * 10000  # 10,000 character string
        add_entry(
            self.conn,
            "Author",
            "tags",
            long_text,
            long_text,
            long_text,
            long_text,
        )

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entries WHERE author = ?", ("Author",))
        entry = cursor.fetchone()

        self.assertIsNotNone(entry)
        self.assertEqual(len(entry["context"]), 10000)
        self.assertEqual(len(entry["question"]), 10000)


if __name__ == "__main__":
    unittest.main()
