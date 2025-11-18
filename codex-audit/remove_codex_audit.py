#!/usr/bin/env python3
"""Undo the audit hook configuration so Codex stops mirroring turns into ~/Documents/codex-logs."""

from __future__ import annotations

import sys
from pathlib import Path

HOOK_PATH = Path.home() / ".codex" / "hooks" / "audit_notify_hook.py"
CONFIG_PATH = Path.home() / ".codex" / "config.toml"
NOTIFY_LINE = f'notify = ["python3", "{HOOK_PATH}"]'


def _remove_hook() -> bool:
    if not HOOK_PATH.exists():
        return False
    try:
        HOOK_PATH.unlink()
    except OSError:
        return False
    return True


def _strip_notify() -> bool:
    if not CONFIG_PATH.exists():
        return False
    lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    filtered = [line for line in lines if line.strip() != NOTIFY_LINE]
    if len(filtered) == len(lines):
        return False
    CONFIG_PATH.write_text("\n".join(filtered) + ("\n" if filtered else ""), encoding="utf-8")
    return True


def main() -> int:
    removed_hook = _remove_hook()
    notify_removed = _strip_notify()
    if not removed_hook and not notify_removed:
        print("No audit hook configuration was present.")
        return 0

    if removed_hook:
        print(f"Removed hook at {HOOK_PATH}")
    if notify_removed:
        print("Removed the notify entry that pointed at the hook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
