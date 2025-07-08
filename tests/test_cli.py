import unittest
import os
from click.testing import CliRunner
from cuddly_potato.cli import cli


class TestCli(unittest.TestCase):
    def setUp(self):
        """Set up a test runner and a temporary database for CLI tests."""
        self.runner = CliRunner()
        self.db_path = "cli_test.db"

    def tearDown(self):
        """Remove the temporary database file after tests."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists("cli_export.json"):
            os.remove("cli_export.json")

    def test_add_command(self):
        """Test the 'add' command with all options."""
        result = self.runner.invoke(
            cli,
            [
                "--db",
                self.db_path,
                "add",
                "--question",
                "CLI Question?",
                "--model",
                "CLI Model",
                "--answer",
                "CLI Answer",
                "--domain",
                "CLI Domain",
                "--subdomain",
                "CLI Subdomain",
                "--comments",
                "CLI test entry",
            ],
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Entry added successfully.", result.output)

    def test_add_command_interactive(self):
        """Test the 'add' command works with interactive prompts."""
        result = self.runner.invoke(
            cli,
            ["--db", self.db_path, "add"],
            input="Interactive Q\nInteractive Model\nInteractive Answer\nDomain\nSub\nComment\n",
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Entry added successfully.", result.output)
        self.assertIn("Interactive Q", result.output)

    def test_update_command(self):
        """Test that the 'update' command correctly modifies an entry."""
        self.runner.invoke(
            cli, ["--db", self.db_path, "add"], input="Q\nM\nA\nD\nS\nC\n"
        )

        result = self.runner.invoke(
            cli,
            ["--db", self.db_path, "update", "1", "--answer", "Updated CLI Answer"],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Entry updated successfully.", result.output)

    def test_export_command(self):
        """Test that the 'export' command creates a valid JSON file."""
        self.runner.invoke(
            cli,
            ["--db", self.db_path, "add"],
            input="Export Q\nExport M\nExport A\n\n\n\n",
        )

        export_file = "cli_export.json"
        result = self.runner.invoke(
            cli,
            ["--db", self.db_path, "export", export_file],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"Data exported to {export_file}", result.output)
        self.assertTrue(os.path.exists(export_file))

    def test_db_path_creation(self):
        """Test that specifying a new db path creates the file."""
        self.assertFalse(os.path.exists(self.db_path))
        self.runner.invoke(cli, ["--db", self.db_path, "add"], input="Q\nM\nA\n\n\n\n")
        self.assertTrue(os.path.exists(self.db_path))

    def test_memory_uses_last_database(self):
        """Test that the CLI remembers the last used database path."""
        with self.runner.isolated_filesystem():
            home = os.getcwd()
            env = {"HOME": home}
            db_path = os.path.join(home, "mem.db")

            self.runner.invoke(
                cli,
                ["--db", db_path, "add"],
                input="Q1\nM\nA1\n\n\n\n",
                env=env,
            )

            result = self.runner.invoke(
                cli, ["add"], input="Q2\nM\nA2\n\n\n\n", env=env
            )

            self.assertEqual(result.exit_code, 0)

            import sqlite3

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Youtubes")
            count = cursor.fetchone()[0]
            conn.close()

            self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
