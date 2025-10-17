#!/usr/bin/env python3
"""
View Claude hook logs.

This script allows you to select a log file and view the summary of the log. 
You can also view the full JSON payload of a selected event.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

def select_log_file() -> Path | None:
    """Prompt the user to select a log file."""
    log_dir = Path.home() / "Documents" / "claude-logs"
    if not log_dir.is_dir():
        print(f"Log directory not found: {log_dir}", file=sys.stderr)
        return None

    log_files = sorted(log_dir.glob("*_summary.log"))
    if not log_files:
        print(f"No summary log files found in {log_dir}", file=sys.stderr)
        return None

    print("Please select a log file to view:")
    for i, log_file in enumerate(log_files):
        print(f"  {i + 1}: {log_file.name}")

    try:
        selection = input("Enter the number of the log file: ")
        selection_index = int(selection) - 1
        if 0 <= selection_index < len(log_files):
            return log_files[selection_index]
        else:
            print("Invalid selection.", file=sys.stderr)
            return None
    except (ValueError, IndexError):
        print("Invalid input.", file=sys.stderr)
        return None
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        return None

def view_summary(log_file: Path):
    """Display the summary log and allow the user to select an event."""
    try:
        with log_file.open("r", encoding="utf-8") as f:
            summaries = [json.loads(line) for line in f]
    except Exception as e:
        print(f"Error reading log file: {e}", file=sys.stderr)
        return

    while True:
        print("\n--- Log Summary ---")
        for i, summary in enumerate(summaries):
            timestamp = summary.get("timestamp", "")
            event = summary.get("event", "")
            print(f"  {i + 1}: {timestamp} - {event}")

        try:
            selection = input("Enter the number of an event to view details (or 'q' to quit): ")
            if selection.lower() == 'q':
                break

            selection_index = int(selection) - 1
            if 0 <= selection_index < len(summaries):
                view_event_details(log_file, selection_index)
            else:
                print("Invalid selection.", file=sys.stderr)
        except (ValueError, IndexError):
            print("Invalid input.", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nAborted by user.", file=sys.stderr)
            break

def view_event_details(summary_file: Path, event_index: int):
    """Display the full JSON payload for a selected event."""
    raw_log_file = summary_file.with_name(summary_file.name.replace("_summary.log", ".jsonl"))
    if not raw_log_file.is_file():
        print(f"Raw log file not found: {raw_log_file}", file=sys.stderr)
        return

    try:
        with raw_log_file.open("r", encoding="utf-8") as f:
            raw_logs = [json.loads(line) for line in f]

        if 0 <= event_index < len(raw_logs):
            print("\n--- Event Details ---")
            print(json.dumps(raw_logs[event_index], indent=2))
        else:
            print("Event index out of range.", file=sys.stderr)

    except Exception as e:
        print(f"Error reading raw log file: {e}", file=sys.stderr)

def main():
    log_file = select_log_file()
    if log_file:
        view_summary(log_file)

if __name__ == "__main__":
    main()
