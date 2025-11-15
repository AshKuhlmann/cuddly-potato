import json
import sqlite3
from pathlib import Path
from click.testing import Result

from cuddly_potato import cli as cli_module
from cuddly_potato.cli import cli
from cuddly_potato import database as database_module


def _assert_success(result: Result, message: str):
    assert (
        result.exit_code == 0
    ), f"{message} failed with exit_code={result.exit_code} output={result.output} exc={result.exception}"


def test_full_cli_user_story(cli_isolated):
    runner, base_path = cli_isolated
    db_path = base_path / "story.db"
    json_path = base_path / "story.json"
    excel_path = base_path / "story.xlsx"
    imported_db_path = base_path / "story-imported.db"

    add_result = runner.invoke(
        cli,
        [
            "--db",
            str(db_path),
            "add",
            "--author",
            "Story Author",
            "--tags",
            "writing,testing",
            "--context",
            "Documenting entire user story",
            "--question",
            "How does the full journey look?",
            "--reason",
            "Validate CLI paths",
            "--answer",
            "By running add/update/export/import commands",
        ],
    )
    _assert_success(add_result, "add command")
    assert "Entry added successfully" in add_result.output

    update_result = runner.invoke(
        cli,
        [
            "--db",
            str(db_path),
            "update",
            "1",
            "--answer",
            "Updated integration answer",
            "--tags",
            "writing,testing,updated",
        ],
    )
    _assert_success(update_result, "update command")
    assert "updated successfully" in update_result.output.lower()

    export_json_result = runner.invoke(
        cli,
        ["--db", str(db_path), "export-json", str(json_path)],
    )
    _assert_success(export_json_result, "export-json command")
    assert json_path.exists()

    export_excel_result = runner.invoke(
        cli,
        ["--db", str(db_path), "export-excel", str(excel_path)],
    )
    _assert_success(export_excel_result, "export-excel command")
    assert excel_path.exists()

    import_result = runner.invoke(
        cli,
        ["--db", str(imported_db_path), "import-json", str(json_path)],
    )
    _assert_success(import_result, "import-json command")
    assert "Imported 1 entries" in import_result.output

    exported_data = json.loads(json_path.read_text())
    assert exported_data[0]["answer"] == "Updated integration answer"

    conn = sqlite3.connect(imported_db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM entries").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]["author"] == "Story Author"
    assert rows[0]["tags"] == "writing,testing,updated"
    assert "user story" in rows[0]["context"]


def test_cli_remembers_last_database(cli_isolated, config_paths):
    runner, base_path = cli_isolated
    _, config_file = config_paths
    db_path = base_path / "remember.db"

    first_result = runner.invoke(
        cli,
        [
            "--db",
            str(db_path),
            "add",
            "--author",
            "First Memory",
            "--question",
            "What is persistence?",
            "--answer",
            "Remembering between commands.",
        ],
    )
    _assert_success(first_result, "initial add command")
    assert config_file.exists()

    stored_path = json.loads(config_file.read_text())["last_db_path"]
    assert Path(stored_path) == db_path

    second_result = runner.invoke(
        cli,
        ["add"],
        input="Second Memory\nHow many entries?\nAt least two!\n",
    )
    _assert_success(second_result, "implicit add command")

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    conn.close()
    assert count == 2


def test_cli_export_json_handles_empty_database(cli_isolated):
    runner, base_path = cli_isolated
    db_path = base_path / "empty.db"
    output_path = base_path / "empty.json"
    result = runner.invoke(
        cli, ["--db", str(db_path), "export-json", str(output_path)]
    )
    _assert_success(result, "export-json on empty db")
    assert json.loads(output_path.read_text()) == []


def test_cli_import_invalid_json(cli_isolated):
    runner, base_path = cli_isolated
    db_path = base_path / "bad.db"
    bad_path = base_path / "bad.json"
    bad_path.write_text("{not-valid-json")

    result = runner.invoke(
        cli, ["--db", str(db_path), "import-json", str(bad_path)]
    )
    assert result.exit_code != 0
    assert "Invalid JSON format" in result.output


def test_cli_import_non_list_payload(cli_isolated):
    runner, base_path = cli_isolated
    db_path = base_path / "dict.db"
    payload_path = base_path / "payload.json"
    payload_path.write_text(json.dumps({"not": "a list"}))

    result = runner.invoke(
        cli, ["--db", str(db_path), "import-json", str(payload_path)]
    )
    assert result.exit_code != 0
    assert "must contain an array" in result.output


def test_cli_import_warns_and_continues_on_failure(cli_isolated, monkeypatch):
    runner, base_path = cli_isolated
    db_path = base_path / "partial.db"
    payload_path = base_path / "partial.json"
    payload_path.write_text(
        json.dumps(
            [
                {
                    "author": "Okay",
                    "question": "Valid entry?",
                    "answer": "Yes",
                },
                {
                    "author": "Broken",
                    "question": "Will this be skipped?",
                    "answer": "No",
                },
            ]
        )
    )

    real_add_entry = database_module.add_entry
    call_count = {"value": 0}

    def flaky_add_entry(conn, *args, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 2:
            raise RuntimeError("boom")
        return real_add_entry(conn, *args, **kwargs)

    monkeypatch.setattr(cli_module, "add_entry", flaky_add_entry)

    result = runner.invoke(
        cli, ["--db", str(db_path), "import-json", str(payload_path)]
    )
    assert result.exit_code != 0
    assert "Imported 1 of 2 entries" in result.output
    assert "Skipped entries" in result.output

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT author FROM entries").fetchone()
    conn.close()
    assert row[0] == "Okay"


def test_cli_update_nonexistent_entry(cli_isolated):
    runner, base_path = cli_isolated
    db_path = base_path / "missing.db"
    result = runner.invoke(
        cli, ["--db", str(db_path), "update", "999", "--author", "Nobody"]
    )
    _assert_success(result, "update missing row")
    assert "No entry found with id 999" in result.output
