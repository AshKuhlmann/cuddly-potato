#!/usr/bin/env python3
"""
Copy Claude `.claude/hook-logs` files from a single project tree into ./logs.

Usage:
    python3 scripts/copy_project_logs.py /path/to/project [--dest /tmp/logs]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def sanitise_fragment(path: Path) -> str:
    """Convert a relative path into a safe directory fragment."""
    text = path.as_posix().lstrip("./")
    if not text:
        text = path.name or "project"
    return text.replace("/", "__")


def collect_logs(project_dir: Path, destination: Path) -> int:
    """Copy log files under project_dir into destination/log-subdir."""
    if not project_dir.exists() or not project_dir.is_dir():
        raise FileNotFoundError(f"{project_dir} is not a directory")

    destination.mkdir(parents=True, exist_ok=True)

    hook_dirs = sorted(project_dir.glob("**/.claude/hook-logs"))
    if not hook_dirs:
        return 0

    copied = 0
    for hook_dir in hook_dirs:
        if not hook_dir.is_dir():
            continue

        project_root = hook_dir.parent.parent
        try:
            relative_project = project_root.relative_to(project_dir)
        except ValueError:
            relative_project = project_root

        target = destination / sanitise_fragment(relative_project)
        target.mkdir(parents=True, exist_ok=True)

        for file_path in hook_dir.iterdir():
            if not file_path.is_file():
                continue
            shutil.copy2(file_path, target / file_path.name)
            copied += 1

    return copied


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy Claude hook logs from a project into ./logs."
    )
    parser.add_argument(
        "project",
        type=Path,
        help="Path to the project directory that contains .claude/hook-logs",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path.cwd() / "logs",
        help="Destination directory for collected logs (default: ./logs)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        project_dir: Path = args.project.expanduser().resolve()
        destination: Path = args.dest.expanduser().resolve()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        copied = collect_logs(project_dir, destination)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if copied:
        print(
            f"Copied {copied} log file(s) from {project_dir} into {destination}."
        )
    else:
        print(
            f"No Claude logs found under {project_dir}. "
            f"Expected directories like {project_dir}/.claude/hook-logs."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
