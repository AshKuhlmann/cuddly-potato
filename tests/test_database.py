import unittest
import sqlite3
import os
import json
from cuddly_potato.database import (
    create_table,
    add_entry,
    update_entry,
    export_to_json,
    DatabaseError,
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
            "What is 2 + 2?",
            "TestModel",
            "4",
            "Math",
            "Basic Math",
            "A test entry",
        )

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM Youtubes WHERE question = ?", ("What is 2 + 2?",))
        entry = cursor.fetchone()

        self.assertIsNotNone(entry)
        self.assertEqual(entry["model"], "TestModel")
        self.assertEqual(entry["answer"], "4")

    def test_add_duplicate_entry(self):
        """Test adding a duplicate entry."""
        add_entry(
            self.conn,
            "What is 2 + 2?",
            "TestModel",
            "4",
            "Math",
            "Basic Math",
            "First entry",
        )
        with self.assertRaises(DatabaseError):
            add_entry(
                self.conn,
                "What is 2 + 2?",
                "TestModel",
                "4.0",
                "Math",
                "Basic Math",
                "Second entry",
            )

    def test_update_entry(self):
        """Test updating an existing entry."""
        add_entry(
            self.conn,
            "Old Question",
            "OldModel",
            "OldAnswer",
            "OldDomain",
            "OldSub",
            "OldComment",
        )

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM Youtubes WHERE question = 'Old Question'")
        entry_id = cursor.fetchone()["id"]

        update_entry(
            self.conn,
            entry_id,
            "New Question",
            "NewModel",
            "NewAnswer",
            "NewDomain",
            "NewSub",
            "NewComment",
        )

        cursor.execute("SELECT * FROM Youtubes WHERE id = ?", (entry_id,))
        entry = cursor.fetchone()

        self.assertEqual(entry["question"], "New Question")
        self.assertEqual(entry["model"], "NewModel")

    def test_update_nonexistent_entry(self):
        """Test updating an entry that does not exist."""
        with self.assertRaises(DatabaseError):
            update_entry(self.conn, 999, "New Question", None, None, None, None, None)

    def test_export_to_json(self):
        """Test exporting data to a JSON file."""
        add_entry(self.conn, "Q1", "M1", "A1", "D1", "S1", "C1")
        add_entry(self.conn, "Q2", "M2", "A2", "D2", "S2", "C2")

        json_path = "test_export.json"
        export_to_json(self.conn, json_path)

        self.assertTrue(os.path.exists(json_path))

        os.remove(json_path)

    def test_create_table_idempotent(self):
        """Test that calling create_table multiple times doesn't cause errors."""
        try:
            create_table(self.conn)
        except Exception as e:  # pragma: no cover - fail if any exception
            self.fail(f"create_table() raised an exception on second call: {e}")

    def test_add_entry_with_missing_optional_fields(self):
        """Test adding an entry with only the required fields."""
        add_entry(
            self.conn,
            "Required only?",
            "TestModel",
            "Yes",
            None,
            None,
            None,
        )

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM Youtubes WHERE question = ?",
            ("Required only?",),
        )
        entry = cursor.fetchone()

        self.assertIsNotNone(entry)
        self.assertIsNone(entry["domain"])
        self.assertIsNone(entry["subdomain"])
        self.assertIsNone(entry["comments"])

    def test_update_entry_partial(self):
        """Test updating only a single field of an existing entry."""
        add_entry(
            self.conn,
            "Initial Q",
            "ModelX",
            "Initial A",
            "DomainX",
            "SubX",
            "CommentX",
        )
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM Youtubes WHERE question = 'Initial Q'")
        entry_id = cursor.fetchone()["id"]

        update_entry(
            self.conn,
            entry_id,
            None,
            None,
            "Updated Answer Only",
            None,
            None,
            None,
        )

        cursor.execute("SELECT * FROM Youtubes WHERE id = ?", (entry_id,))
        entry = cursor.fetchone()

        self.assertEqual(entry["question"], "Initial Q")
        self.assertEqual(entry["answer"], "Updated Answer Only")

    def test_update_entry_to_create_duplicate(self):
        """Test that an update fails if it creates a duplicate question/model pair."""
        add_entry(self.conn, "Unique Q1", "ModelA", "A1", None, None, None)
        add_entry(self.conn, "Unique Q2", "ModelA", "A2", None, None, None)

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM Youtubes WHERE question = 'Unique Q2'")
        entry_id_to_update = cursor.fetchone()["id"]

        with self.assertRaises(DatabaseError):
            update_entry(
                self.conn,
                entry_id_to_update,
                "Unique Q1",
                "ModelA",
                "A3",
                None,
                None,
                None,
            )

    def test_export_to_json_empty_db(self):
        """Test exporting an empty database results in an empty JSON list."""
        json_path = "test_empty_export.json"
        export_to_json(self.conn, json_path)

        self.assertTrue(os.path.exists(json_path))

        with open(json_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data, [])

        os.remove(json_path)


if __name__ == "__main__":
    unittest.main()
