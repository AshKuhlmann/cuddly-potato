#!/usr/bin/env python3
"""Install the Codex audit hook so each session turn is mirrored into ~/Documents/codex-logs."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).parent.resolve()
HOOK_TEMPLATE_PATH = SCRIPT_ROOT / "templates" / "audit_notify_hook.py"
HOOK_DEST = Path.home() / ".codex" / "hooks" / "audit_notify_hook.py"
CONFIG_PATH = Path.home() / ".codex" / "config.toml"
SESSION_LOG_DIR = Path.home() / "Documents" / "codex-logs"
NOTIFY_LINE = f'notify = ["python3", "{HOOK_DEST}"]'


def _read_hook_template() -> str:
    if not HOOK_TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Template not found at {HOOK_TEMPLATE_PATH}; keep templates/audit_notify_hook.py alongside this installer."
        )
    return HOOK_TEMPLATE_PATH.read_text(encoding="utf-8")


def _install_hook(hook_source: str) -> bool:
    HOOK_DEST.parent.mkdir(parents=True, exist_ok=True)
    if HOOK_DEST.exists() and HOOK_DEST.read_text(encoding="utf-8") == hook_source:
        return False
    HOOK_DEST.write_text(hook_source, encoding="utf-8")
    HOOK_DEST.chmod(0o755)
    return True


def _ensure_notify() -> bool:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(NOTIFY_LINE + "\n", encoding="utf-8")
        return True

    lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        if line.strip().startswith("notify"):
            if line.strip() == NOTIFY_LINE:
                return False
            lines[idx] = NOTIFY_LINE
            CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
    lines.insert(0, NOTIFY_LINE)
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _ensure_session_dir() -> None:
    SESSION_LOG_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    try:
        hook_source = _read_hook_template()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    installed_hook = _install_hook(hook_source)
    notify_updated = _ensure_notify()
    _ensure_session_dir()

    if not installed_hook and not notify_updated:
        print("Codex audit logging already configured.")
        return 0

    if installed_hook:
        print(f"Hook installed at {HOOK_DEST}")
    if notify_updated:
        print("Codex config now invokes the audit hook via notify.")
    print(f"Session logs will accumulate under {SESSION_LOG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
