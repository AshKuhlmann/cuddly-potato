#!/usr/bin/env python3
"""
Collect Claude hook logs from multiple projects into a local ./logs directory.

The script prompts for a base directory that contains projects. For every
folder under it that has `.claude/hook-logs`, the logs are copied into
`./logs/<sanitised-project>/` relative to where this script is run.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def prompt_root() -> Path:
    try:
        user_input = input(
            "Enter the directory containing your projects "
            "(press Enter for current directory): "
        ).strip()
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(1)

    base = Path(user_input or ".").expanduser().resolve()
    if not base.exists() or not base.is_dir():
        print(f"error: {base} is not a directory.", file=sys.stderr)
        sys.exit(1)
    return base


def sanitise_path(path: Path) -> str:
    text = path.as_posix().lstrip("./")
    if not text:
        text = path.name or "project"
    return text.replace("/", "__")


def collect_logs(base_dir: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    hook_dirs = set()
    for p in base_dir.glob("**/.claude/hook-logs"):
        if not p.is_dir():
            continue
        project_root = p.parent.parent
        if project_root is None:
            continue
        hook_dirs.add(project_root)

    if not hook_dirs:
        print(f"No Claude logs found under {base_dir}.")
        return 0

    copied_files = 0
    for project_dir in sorted(hook_dirs):
        log_dir = project_dir / ".claude" / "hook-logs"
        if not log_dir.is_dir():
            continue

        try:
            rel = project_dir.relative_to(base_dir)
        except ValueError:
            rel = project_dir

        target_dir = destination / sanitise_path(rel)
        target_dir.mkdir(parents=True, exist_ok=True)

        for file_path in log_dir.iterdir():
            if not file_path.is_file():
                continue
            shutil.copy2(file_path, target_dir / file_path.name)
            copied_files += 1

        print(f"Collected logs from {project_dir} -> {target_dir}")

    return copied_files


def main() -> None:
    base_dir = prompt_root()
    destination = Path.cwd() / "logs"
    count = collect_logs(base_dir, destination)
    if count:
        print(f"\nCopied {count} log files into {destination}.")
    else:
        print("No log files copied.")


if __name__ == "__main__":
    main()
