import unittest
import os
import json
import sqlite3
from click.testing import CliRunner
from cuddly_potato.cli import cli


class TestCLI(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.test_db = "test_cli.db"

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        # Clean up any export files
        for file in ["test_export.json", "test_export.xlsx"]:
            if os.path.exists(file):
                os.remove(file)

    def test_add_entry(self):
        """Test adding an entry via CLI."""
        result = self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "add",
                "--author",
                "John Doe",
                "--tags",
                "python,testing",
                "--context",
                "Test context",
                "--question",
                "What is testing?",
                "--reason",
                "To verify functionality",
                "--answer",
                "Testing is verification",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Entry added successfully", result.output)

    def test_add_entry_with_prompts(self):
        """Test adding an entry with interactive prompts."""
        result = self.runner.invoke(
            cli,
            ["--db", self.test_db, "add"],
            input="John Doe\nWhat is Python?\nPython is a programming language\n",
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Entry added successfully", result.output)

    def test_update_entry(self):
        """Test updating an entry."""
        # First add an entry
        self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "add",
                "--author",
                "Jane",
                "--question",
                "Q1",
                "--answer",
                "A1",
            ],
        )

        # Now update it
        result = self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "update",
                "1",
                "--author",
                "Jane Smith",
                "--question",
                "Updated Question",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("updated successfully", result.output)

    def test_update_nonexistent_entry(self):
        """Test updating an entry that doesn't exist."""
        result = self.runner.invoke(
            cli,
            ["--db", self.test_db, "update", "999", "--author", "Nobody"],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Error", result.output)

    def test_export_json(self):
        """Test exporting to JSON."""
        # Add an entry first
        self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "add",
                "--author",
                "Export Test",
                "--question",
                "Test Q",
                "--answer",
                "Test A",
            ],
        )

        # Export to JSON
        result = self.runner.invoke(
            cli, ["--db", self.test_db, "export-json", "test_export.json"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(os.path.exists("test_export.json"))

        # Verify the exported data
        with open("test_export.json", "r") as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["author"], "Export Test")

    def test_export_excel(self):
        """Test exporting to Excel."""
        # Add an entry first
        self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "add",
                "--author",
                "Excel Test",
                "--question",
                "Test Q",
                "--answer",
                "Test A",
            ],
        )

        # Export to Excel
        result = self.runner.invoke(
            cli, ["--db", self.test_db, "export-excel", "test_export.xlsx"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(os.path.exists("test_export.xlsx"))

    def test_import_json(self):
        """Test importing entries from JSON file."""
        # Create a test JSON file
        test_data = [
            {
                "author": "Import Author 1",
                "tags": "test,import",
                "context": "Import context 1",
                "question": "Import question 1",
                "reason": "Import reason 1",
                "answer": "Import answer 1",
            },
            {
                "author": "Import Author 2",
                "tags": "test",
                "context": "Import context 2",
                "question": "Import question 2",
                "reason": "Import reason 2",
                "answer": "Import answer 2",
            },
        ]

        import_file = "test_import.json"
        with open(import_file, "w") as f:
            json.dump(test_data, f)

        # Import the data
        result = self.runner.invoke(
            cli, ["--db", self.test_db, "import-json", import_file]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully imported 2 entries", result.output)

        # Verify the data was imported
        conn = sqlite3.connect(self.test_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entries")
        entries = cursor.fetchall()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["author"], "Import Author 1")
        conn.close()

        # Clean up
        os.remove(import_file)


if __name__ == "__main__":
    unittest.main()
