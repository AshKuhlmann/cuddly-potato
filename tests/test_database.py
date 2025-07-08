import unittest
import sqlite3
import os
from cuddly_potato.database import create_table, add_entry, update_entry, export_to_json


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
        result = add_entry(
            self.conn,
            "What is 2 + 2?",
            "TestModel",
            "4",
            "Math",
            "Basic Math",
            "A test entry",
        )
        self.assertEqual(result, "Entry added successfully.")

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
        result = add_entry(
            self.conn,
            "What is 2 + 2?",
            "TestModel",
            "4.0",
            "Math",
            "Basic Math",
            "Second entry",
        )
        self.assertEqual(result, "Error: This question for this model already exists.")

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

        result = update_entry(
            self.conn,
            entry_id,
            "New Question",
            "NewModel",
            "NewAnswer",
            "NewDomain",
            "NewSub",
            "NewComment",
        )
        self.assertEqual(result, "Entry updated successfully.")

        cursor.execute("SELECT * FROM Youtubes WHERE id = ?", (entry_id,))
        entry = cursor.fetchone()

        self.assertEqual(entry["question"], "New Question")
        self.assertEqual(entry["model"], "NewModel")

    def test_update_nonexistent_entry(self):
        """Test updating an entry that does not exist."""
        result = update_entry(
            self.conn, 999, "New Question", None, None, None, None, None
        )
        self.assertEqual(result, "Error: No entry found with id 999.")

    def test_export_to_json(self):
        """Test exporting data to a JSON file."""
        add_entry(self.conn, "Q1", "M1", "A1", "D1", "S1", "C1")
        add_entry(self.conn, "Q2", "M2", "A2", "D2", "S2", "C2")

        json_path = "test_export.json"
        result = export_to_json(self.conn, json_path)

        self.assertEqual(result, f"Data exported to {json_path}")
        self.assertTrue(os.path.exists(json_path))

        os.remove(json_path)


if __name__ == "__main__":
    unittest.main()
