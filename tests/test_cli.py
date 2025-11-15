import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from click.testing import CliRunner
from cuddly_potato.cli import (
    EXIT_UNEXPECTED_ERROR,
    EXIT_VALIDATION_ERROR,
    cli,
)
from cuddly_potato.database import DatabaseError


class TestCLI(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.test_db = "test_cli.db"
        self.config_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.config_dir, "config.json")
        self._patchers = [
            mock.patch("cuddly_potato.cli.CONFIG_DIR", self.config_dir),
            mock.patch("cuddly_potato.cli.CONFIG_FILE", self.config_file),
            mock.patch("cuddly_potato.gui.CONFIG_DIR", self.config_dir),
            mock.patch("cuddly_potato.gui.CONFIG_FILE", self.config_file),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        """Clean up test database."""
        self._stop_patches()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        # Clean up any export files
        for file in ["test_export.json", "test_export.xlsx"]:
            if os.path.exists(file):
                os.remove(file)
        shutil.rmtree(self.config_dir, ignore_errors=True)

    def _stop_patches(self):
        for patcher in getattr(self, "_patchers", []):
            patcher.stop()

    def _structured_logs(self, output):
        logs = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return logs

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

    def test_add_entry_missing_author_fails(self):
        """Ensure CLI rejects entries without an author."""
        result = self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "add",
                "--author",
                "",
                "--question",
                "Is validation enforced?",
                "--answer",
                "Yes",
            ],
        )
        self.assertEqual(result.exit_code, EXIT_VALIDATION_ERROR)
        self.assertIn("Author is required", result.output)

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
        self.assertEqual(result.exit_code, EXIT_VALIDATION_ERROR)
        self.assertIn("No entry found with id 999", result.output)

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
        self.assertIn("Imported 2 entries", result.output)

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

    def test_export_json_failure_exits_nonzero(self):
        """Ensure export-json surfaces errors via exit codes."""
        with mock.patch(
            "cuddly_potato.cli.export_to_json",
            side_effect=DatabaseError("disk full"),
        ):
            result = self.runner.invoke(
                cli, ["--db", self.test_db, "export-json", "out.json"]
            )
        self.assertEqual(result.exit_code, EXIT_UNEXPECTED_ERROR)
        self.assertIn("disk full", result.output)

    def test_export_excel_failure_exits_nonzero(self):
        """Ensure export-excel surfaces errors via exit codes."""
        with mock.patch(
            "cuddly_potato.cli.export_to_excel",
            side_effect=DatabaseError("permission denied"),
        ):
            result = self.runner.invoke(
                cli, ["--db", self.test_db, "export-excel", "out.xlsx"]
            )
        self.assertEqual(result.exit_code, EXIT_UNEXPECTED_ERROR)
        self.assertIn("permission denied", result.output)

    def test_import_json_reports_partial_failures(self):
        """Ensure import-json warns and exits non-zero when rows are skipped."""
        test_data = [
            {
                "author": "",
                "question": "Missing author should fail",
                "answer": "Nope",
            },
            {
                "author": "Valid",
                "question": "Will import succeed?",
                "answer": "Yes",
            },
        ]
        import_file = "test_partial_import.json"
        with open(import_file, "w") as f:
            json.dump(test_data, f)

        result = self.runner.invoke(
            cli, ["--db", self.test_db, "import-json", import_file]
        )

        self.assertEqual(result.exit_code, EXIT_VALIDATION_ERROR)
        self.assertIn("Imported 1 of 2 entries", result.output)
        self.assertIn("Author is required", result.output)

        os.remove(import_file)

    def test_structured_logging_records_success(self):
        """Structured logs include command result metadata on success."""
        result = self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "--quiet",
                "add",
                "--author",
                "Log Test",
                "--question",
                "Does logging work?",
                "--answer",
                "Yes",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        logs = self._structured_logs(result.output)
        self.assertTrue(logs, "Expected structured logs to be emitted.")
        last_log = logs[-1]
        self.assertEqual(last_log["event"], "command_result")
        self.assertEqual(last_log["command"], "add")
        self.assertEqual(last_log["status"], "success")
        self.assertEqual(last_log["exit_code"], 0)

    def test_structured_logging_records_failure(self):
        """Structured logs record non-zero exits with reason metadata."""
        result = self.runner.invoke(
            cli,
            ["--db", self.test_db, "--quiet", "update", "999", "--author", "Nobody"],
        )
        self.assertEqual(result.exit_code, EXIT_VALIDATION_ERROR)
        logs = self._structured_logs(result.output)
        self.assertTrue(logs, "Expected structured logs to be emitted.")
        last_log = logs[-1]
        self.assertEqual(last_log["event"], "command_result")
        self.assertEqual(last_log["command"], "update")
        self.assertEqual(last_log["status"], "validation_error")
        self.assertEqual(last_log["exit_code"], EXIT_VALIDATION_ERROR)
        self.assertIn("Validation failed", last_log["message"])
        self.assertIn("entry 999", last_log["message"])

    def test_verbose_mode_emits_command_start_logs(self):
        """Verbose flag surfaces command start events for troubleshooting."""
        result = self.runner.invoke(
            cli,
            [
                "--db",
                self.test_db,
                "--verbose",
                "add",
                "--author",
                "Verbose",
                "--question",
                "Command start recorded?",
                "--answer",
                "Yes",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        logs = self._structured_logs(result.output)
        events = [log["event"] for log in logs]
        self.assertIn("command_start", events)
        self.assertIn("command_result", events)


if __name__ == "__main__":
    unittest.main()
