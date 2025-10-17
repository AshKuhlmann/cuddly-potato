#!/usr/bin/env bash
set -euo pipefail

resolve_self_path() {
  python3 - "$1" <<'PY'
import os, sys
path = os.path.abspath(sys.argv[1])
while os.path.islink(path):
    target = os.readlink(path)
    if not os.path.isabs(target):
        path = os.path.normpath(os.path.join(os.path.dirname(path), target))
    else:
        path = target
print(os.path.abspath(path))
PY
}

SELF_PATH=$(resolve_self_path "${BASH_SOURCE[0]}")
HERE_DIR=$(cd -- "$(dirname -- "${SELF_PATH}")" && pwd)
PROJECT_ROOT=$(cd -- "${HERE_DIR}/.." && pwd)

if [[ "${CLAUDE_WRAPPER_DEBUG:-}" == "1" ]]; then
  echo "[wrapper] SELF_PATH=${SELF_PATH}" >&2
  echo "[wrapper] HERE_DIR=${HERE_DIR}" >&2
  echo "[wrapper] PROJECT_ROOT=${PROJECT_ROOT}" >&2
fi

# Candidate locations where the launcher might live already.
candidates=()
candidates+=("${PROJECT_ROOT}/scripts/claude_with_hooks.py")
candidates+=("${HERE_DIR}/../scripts/claude_with_hooks.py")
candidates+=("$HOME/development/data_logger/scripts/claude_with_hooks.py")
candidates+=("$HOME/development/data_logger/claude-tracker/scripts/claude_with_hooks.py")
candidates+=("$HOME/development/data_logger/codex/open-codex-cli/scripts/claude_with_hooks.py")

INSTALL_DIR="$HOME/.local/share/claude-hooks"
INSTALL_PATH="${INSTALL_DIR}/claude_with_hooks.py"

# Resolve the real Claude CLI binary, avoiding recursion into this wrapper
resolve_real_claude_cmd() {
  # 1) Honor explicit env if set
  if [[ -n "${CLAUDE_CMD:-}" ]]; then
    echo "${CLAUDE_CMD}"
    return 0
  fi
  # 2) Search all claude binaries on PATH and pick the first that isn't us
  local resolved_self
  resolved_self=$(resolve_self_path "${BASH_SOURCE[0]}")
  local resolved
  local path_entry
  local candidate
  local -a path_entries
  local IFS=':'
  read -r -a path_entries <<< "${PATH:-}"
  for path_entry in "${path_entries[@]}"; do
    [[ -n "$path_entry" ]] || path_entry="."
    candidate="${path_entry%/}/claude"
    if [[ -x "$candidate" ]]; then
      resolved=$(resolve_self_path "$candidate")
      if [[ "$resolved" != "$resolved_self" ]]; then
        echo "$candidate"
        return 0
      fi
    fi
  done

  # 3) Fall back to common Homebrew locations
  for cand in "/opt/homebrew/bin/claude" "/usr/local/bin/claude"; do
    if [[ -x "$cand" ]]; then
      resolved=$(resolve_self_path "$cand")
      if [[ "$resolved" != "$resolved_self" ]]; then
        echo "$cand"
        return 0
      fi
    fi
  done

  # 4) Give up
  return 1
}

find_existing_launcher() {
  for p in "${candidates[@]}"; do
    if [[ -f "$p" ]]; then
      [[ "${CLAUDE_WRAPPER_DEBUG:-}" == "1" ]] && echo "[wrapper] found $p" >&2
      echo "$p"
      return 0
    fi
    [[ "${CLAUDE_WRAPPER_DEBUG:-}" == "1" ]] && echo "[wrapper] missing $p" >&2
  done
  return 1
}

ensure_launcher() {
  local target="$1"
  mkdir -p -- "$(dirname -- "$target")"
  cat >"$target" <<'PYEOF'
#!/usr/bin/env python3
"""
Bootstrap Claude Code hooks for any project before launching the CLI.

This file is embedded by bin/claude-wrapper.sh and re-created if missing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import textwrap


HOOK_EVENTS_WITH_MATCHER = {"PreToolUse", "PostToolUse"}
ALL_HOOK_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact",
    "SessionStart",
    "SessionEnd",
]

EMBEDDED_EVENT_LOGGER = textwrap.dedent('''#!/usr/bin/env python3
"""
Claude Code Hook – Security/Event Logger
Writes two files per session:
  • raw  payloads ->  .claude/hook-logs/<SESSION>.jsonl
  • summary lines ->  .claude/hook-logs/<SESSION>_summary.log
Never blocks (exit 0) unless its own JSON is malformed (exit 1).
"""
from __future__ import annotations
import json, sys, os, datetime, pathlib, traceback
from typing import Any, Dict, List, Optional

SUMMARY_CHAR_LIMIT = 400

def _clip(text: Optional[str], limit: int = SUMMARY_CHAR_LIMIT) -> Optional[str]:
    if not text:
        return None
    cleaned = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"

def _stringify(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)

def _summarize_tool_io(data: Dict[str, Any]) -> Dict[str, Any]:
    raw_input = data.get("tool_input")
    raw_output = data.get("tool_response")
    summary: Dict[str, Any] = {
        "input": None,
        "output": None,
        "stdout": None,
        "stderr": None,
        "exit_code": None,
        "success": None,
    }
    if raw_input is not None:
        if isinstance(raw_input, dict):
            if "command" in raw_input:
                summary["input"] = _clip(_stringify(raw_input["command"]))
            elif "file_path" in raw_input:
                summary["input"] = raw_input["file_path"]
            elif "path" in raw_input:
                summary["input"] = raw_input["path"]
            else:
                summary["input"] = _clip(_stringify(raw_input))
        else:
            summary["input"] = _clip(_stringify(raw_input))
    if isinstance(raw_output, dict):
        if "success" in raw_output:
            summary["success"] = raw_output.get("success")
        if "exit_code" in raw_output:
            summary["exit_code"] = raw_output.get("exit_code")
        stdout = raw_output.get("stdout")
        if stdout:
            summary["stdout"] = _clip(stdout)
        stderr = raw_output.get("stderr")
        if stderr:
            summary["stderr"] = _clip(stderr)
        if raw_output.get("type") == "text":
            file_info = raw_output.get("file")
            if isinstance(file_info, dict) and "content" in file_info:
                summary["output"] = _clip(file_info.get("content"))
            elif "text" in raw_output:
                summary["output"] = _clip(_stringify(raw_output["text"]))
        if summary["output"] is None:
            for key in ("output", "result", "data", "content"):
                if key in raw_output and raw_output[key]:
                    summary["output"] = _clip(_stringify(raw_output[key]))
                    break
            if summary["output"] is None and not stdout and not stderr:
                summary["output"] = _clip(_stringify(raw_output))
    elif raw_output is not None:
        summary["output"] = _clip(_stringify(raw_output))
    return summary

def _todo_key(item: Any) -> str:
    if isinstance(item, dict):
        content = item.get("content")
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False, sort_keys=True)
        except Exception:
            return str(content)
    return _stringify(item)

def _normalize_todo_item(item: Any) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {"content": _clip(_stringify(item)), "status": None, "active_form": None}
    active_form = item.get("activeForm")
    if active_form is None:
        active_form = item.get("active_form")
    return {
        "content": _clip(_stringify(item.get("content"))),
        "status": item.get("status"),
        "active_form": _clip(_stringify(active_form)) if active_form else None,
    }

def _normalize_todo_items(items: Any) -> Optional[List[Dict[str, Any]]]:
    if not items:
        return None
    if isinstance(items, list):
        return [_normalize_todo_item(entry) for entry in items]
    return [_normalize_todo_item(items)]

def _diff_todos(old: Any, new: Any) -> Optional[Dict[str, Any]]:
    old_list = old if isinstance(old, list) else []
    new_list = new if isinstance(new, list) else []
    if not old_list and not new_list:
        return None
    old_key_to_item = {}
    for item in old_list:
        if isinstance(item, dict):
            old_key_to_item[_todo_key(item)] = item
    new_key_to_item = {}
    for item in new_list:
        if isinstance(item, dict):
            new_key_to_item[_todo_key(item)] = item
    added = [_normalize_todo_item(item) for item in new_list if _todo_key(item) not in old_key_to_item]
    removed = [_normalize_todo_item(item) for item in old_list if _todo_key(item) not in new_key_to_item]
    changed = []
    for key in set(old_key_to_item.keys()) & set(new_key_to_item.keys()):
        old_item = old_key_to_item[key]
        new_item = new_key_to_item[key]
        old_status = old_item.get("status")
        new_status = new_item.get("status")
        old_active = old_item.get("activeForm") or old_item.get("active_form")
        new_active = new_item.get("activeForm") or new_item.get("active_form")
        if old_status != new_status or old_active != new_active:
            changed.append({
                "content": _clip(_stringify(new_item.get("content"))),
                "from": {"status": old_status, "active_form": _clip(_stringify(old_active)) if old_active else None},
                "to":   {"status": new_status, "active_form": _clip(_stringify(new_active)) if new_active else None},
            })
    result = {}
    if added:   result["added"] = added
    if removed: result["removed"] = removed
    if changed: result["changed"] = changed
    return result or None

def _sanitize_plan_payload(value: Any, depth: int = 0) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return _clip(value, limit=600 if depth == 0 else SUMMARY_CHAR_LIMIT)
    if isinstance(value, list):
        return [_sanitize_plan_payload(entry, depth + 1) for entry in value]
    if isinstance(value, dict):
        return {str(k): _sanitize_plan_payload(v, depth + 1) for k, v in value.items()}
    return value

def _extract_plan_updates(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tool_name = data.get("tool_name")
    if not tool_name:
        return None
    lower_name = str(tool_name).lower()
    event = data.get("hook_event_name")
    stage = "post" if event == "PostToolUse" else "pre" if event == "PreToolUse" else event
    plan_update: Dict[str, Any] = {"tool": tool_name, "stage": stage}
    if lower_name.startswith("todo"):
        plan_update["type"] = "todo"
        requested = _normalize_todo_items((data.get("tool_input") or {}).get("todos"))
        if requested:
            plan_update["requested"] = requested
        response = data.get("tool_response") or {}
        new_todos = response.get("newTodos") or response.get("todos")
        normalized_new = _normalize_todo_items(new_todos)
        if normalized_new:
            plan_update["result"] = normalized_new
        diff = _diff_todos(response.get("oldTodos"), new_todos)
        if diff:
            plan_update["changes"] = diff
        success = response.get("success")
        if success is not None:
            plan_update["success"] = success
    elif "plan" in lower_name:
        plan_update["type"] = "plan"
        requested = (data.get("tool_input") or {}).get("plan")
        sanitized_requested = _sanitize_plan_payload(requested)
        if sanitized_requested is not None:
            plan_update["requested"] = sanitized_requested
        response = data.get("tool_response") or {}
        for key in ("plan", "result", "data"):
            if key in response:
                sanitized_result = _sanitize_plan_payload(response.get(key))
                if sanitized_result is not None:
                    plan_update["result"] = sanitized_result
                break
        success = response.get("success")
        if success is not None:
            plan_update["success"] = success
    else:
        return None
    cleaned = {k: v for k, v in plan_update.items() if v is not None}
    informative = [k for k in cleaned if k not in {"tool", "stage", "type"}]
    if not informative:
        return None
    return cleaned

def _build_context_from_lines(lines, max_entries: int = 8):
    context = []
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except Exception:
            continue
        entry_type = entry.get("type")
        if entry_type == "assistant":
            message = entry.get("message") or {}
            content = message.get("content") or []
            text = None
            thinking = None
            tool_uses = []
            for item in reversed(content):
                item_type = item.get("type")
                if item_type == "text" and text is None:
                    text = _clip(item.get("text"))
                elif item_type == "thinking" and thinking is None:
                    thinking = _clip(item.get("thinking"))
                elif item_type == "tool_use":
                    tool_uses.append({"name": item.get("name"), "input": _clip(_stringify(item.get("input")))})
            if text:
                context.append({"actor": "assistant", "type": "text", "content": text})
            if thinking:
                context.append({"actor": "assistant", "type": "thinking", "content": thinking})
            for tool in tool_uses:
                context.append({"actor": "assistant", "type": "tool_use", "name": tool.get("name"), "content": tool.get("input")})
        elif entry_type == "user":
            message = entry.get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                clipped = _clip(content)
                if clipped:
                    context.append({"actor": "user", "type": "text", "content": clipped})
            elif isinstance(content, list):
                for item in content:
                    item_type = item.get("type")
                    if item_type == "text":
                        clipped = _clip(item.get("text"))
                        if clipped:
                            context.append({"actor": "user", "type": "text", "content": clipped})
                    elif item_type == "tool_result":
                        summary = _clip(_stringify(item.get("content")))
                        if summary:
                            context.append({"actor": "tool", "type": "result", "tool_id": item.get("tool_use_id"), "content": summary})
        if len(context) >= max_entries:
            break
    context.reverse()
    return context

def _extract_transcript_snapshot(transcript_path: Optional[str], max_context: int = 8) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {"text": None, "thinking": None, "plan": None, "context": []}
    if not transcript_path:
        return snapshot
    path = Path(transcript_path)
    if not path.is_file():
        return snapshot
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return snapshot
    pending_results: Dict[str, Optional[str]] = {}
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except Exception:
            continue
        entry_type = entry.get("type")
        if entry_type == "assistant":
            message = entry.get("message") or {}
            content = message.get("content") or []
            for item in reversed(content):
                item_type = item.get("type")
                if item_type == "text" and snapshot["text"] is None:
                    val = item.get("text")
                    if val:
                        snapshot["text"] = _clip(val)
                elif item_type == "thinking" and snapshot["thinking"] is None:
                    val = item.get("thinking")
                    if val:
                        snapshot["thinking"] = _clip(val)
                elif item_type == "tool_use" and snapshot["plan"] is None:
                    name = item.get("name") or ""
                    if "plan" in name.lower():
                        tool_id = item.get("id")
                        info: Dict[str, Any] = {
                            "source": "tool_use", "name": item.get("name"), "input": _clip(_stringify(item.get("input"))), "output": None, "status": "pending",
                        }
                        if tool_id and tool_id in pending_results:
                            info["output"] = pending_results.pop(tool_id)
                            info["status"] = "completed"
                        snapshot["plan"] = info
            if snapshot["text"] and snapshot["thinking"] and snapshot["plan"]:
                break
        elif entry_type == "user":
            message = entry.get("message") or {}
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "tool_result":
                        tool_id = item.get("tool_use_id")
                        pending_results[tool_id] = _clip(_stringify(item.get("content")))
    snapshot["context"] = _build_context_from_lines(lines, max_entries=max_context)
    return snapshot

def make_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    event = data.get("hook_event_name")
    snapshot = _extract_transcript_snapshot(data.get("transcript_path"))
    tool_info = _summarize_tool_io(data) if event in {"PreToolUse", "PostToolUse"} else {
        "input": None, "output": None, "stdout": None, "stderr": None, "exit_code": None, "success": None,
    }
    plan_update = _extract_plan_updates(data)
    snapshot_plan = snapshot.get("plan")
    assistant_plan: Optional[Dict[str, Any]]
    if snapshot_plan or plan_update:
        assistant_plan = {}
        if snapshot_plan:
            assistant_plan["latest"] = snapshot_plan
        if plan_update:
            assistant_plan["update"] = plan_update
    else:
        assistant_plan = None
    summary: Dict[str, Any] = {
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "event": event,
        "session": data.get("session_id"),
        "user": {"prompt": None},
        "assistant": {"thinking": snapshot.get("thinking"), "output": snapshot.get("text"), "plan": assistant_plan},
        "tool": {
            "name": data.get("tool_name"),
            "input": tool_info.get("input"),
            "output": tool_info.get("output"),
            "stdout": tool_info.get("stdout"),
            "stderr": tool_info.get("stderr"),
            "exit_code": tool_info.get("exit_code"),
            "success": tool_info.get("success"),
        },
        "context": snapshot.get("context", []),
        "metadata": {},
    }
    if event == "UserPromptSubmit":
        summary["user"]["prompt"] = _clip(data.get("prompt") or "")
    if event == "PostToolUse":
        raw_success = data.get("tool_response", {}).get("success")
        if summary["tool"]["success"] is None and raw_success is not None:
            summary["tool"]["success"] = raw_success
    if event == "Notification":
        summary["metadata"]["message"] = data.get("message")
    if event in {"Stop", "SubagentStop"}:
        summary["metadata"]["stop_hook_active"] = data.get("stop_hook_active")
    if event == "SessionEnd":
        summary["metadata"]["reason"] = data.get("reason")
    if event == "SessionStart":
        summary["metadata"]["source"] = data.get("source")
    if event == "PreCompact":
        summary["metadata"]["reason"] = data.get("reason")
    if event in {"PreToolUse", "PostToolUse"}:
        if plan_update:
            summary["metadata"]["plan_event"] = {
                "stage": plan_update.get("stage"),
                "tool_name": plan_update.get("tool"),
                "type": plan_update.get("type"),
            }
    if not summary["metadata"]:
        summary["metadata"] = None
    return summary

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, default=Path.cwd())
    p.add_argument("--claude-cmd", default=os.environ.get("CLAUDE_CMD", "claude"))
    p.add_argument("--log-destination", type=Path, default=Path.home() / "Documents" / "claude-logs")
    p.add_argument("claude_args", nargs=argparse.REMAINDER)
    return p.parse_args()

def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def ensure_gitignore_excludes_claude(project_dir: Path) -> None:
    gitignore = project_dir / ".gitignore"
    entry = ".claude/"
    alt_entries = {entry, "/.claude/", ".claude", "/.claude"}
    content = read_text(gitignore)
    if content is None:
        write_text(gitignore, entry + "\n")
        return
    existing = {line.strip() for line in content.splitlines() if line.strip()}
    if alt_entries & existing:
        return
    with gitignore.open("a", encoding="utf-8") as handle:
        if content and not content.endswith("\n"):
            handle.write("\n")
        handle.write(entry + "\n")

def ensure_event_logger(project_dir: Path, template_logger: Path, embedded: str) -> None:
    hooks_dir = project_dir / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    target = hooks_dir / "event-logger.py"
    template_content = read_text(template_logger)
    if template_content is None:
        template_content = embedded
    current_content = read_text(target)
    if current_content != template_content:
        write_text(target, template_content)
    target.chmod(stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

def build_hook_block(command: str, include_matcher: bool) -> Dict[str, Any]:
    hook_entry: Dict[str, Any] = {"hooks": [{"type": "command", "command": command}]}
    if include_matcher:
        hook_entry["matcher"] = "*"
    return hook_entry

def update_settings(project_dir: Path, command: str) -> Path:
    config_dir = project_dir / ".claude"
    config_dir.mkdir(parents=True, exist_ok=True)
    candidate_paths = [config_dir / "settings.local.json", config_dir / "settings.json"]
    for path in candidate_paths:
        if path.exists():
            settings_path = path
            break
    else:
        settings_path = candidate_paths[0]
    content = read_text(settings_path)
    if content:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(f"{settings_path} contains invalid JSON; fix or remove it.")
    else:
        data = {}
    hooks: Dict[str, Any] = {}
    for event in ALL_HOOK_EVENTS:
        include_matcher = event in HOOK_EVENTS_WITH_MATCHER
        hooks[event] = [build_hook_block(command, include_matcher)]
    data["hooks"] = hooks
    write_text(settings_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return settings_path

def run_claude(project_dir: Path, claude_cmd: str, claude_args: List[str]) -> int:
    env = os.environ.copy()
    env.setdefault("CLAUDE_PROJECT_DIR", str(project_dir))
    forwarded_args = claude_args
    if forwarded_args and forwarded_args[0] == "--":
        forwarded_args = forwarded_args[1:]
    try:
        proc = subprocess.run([claude_cmd, *forwarded_args], env=env)
    except FileNotFoundError as exc:
        raise FileNotFoundError("Unable to launch Claude CLI '{}'. Set --claude-cmd or CLAUDE_CMD if the binary lives elsewhere.".format(claude_cmd)) from exc
    return proc.returncode

def sanitise_project_name(project_dir: Path) -> str:
    resolved = project_dir.resolve()
    name = resolved.as_posix().replace("/", "-")
    return name.lstrip("-")

def mirror_logs(project_dir: Path, destination_root: Path) -> None:
    source = project_dir / ".claude" / "hook-logs"
    if not source.is_dir():
        return
    dest = destination_root / sanitise_project_name(project_dir)
    dest.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*"):
        if path.is_file():
            shutil.copy2(path, dest / path.name)

def main() -> int:
    args = parse_args()
    project_dir: Path = args.project.resolve()
    template_logger = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "event-logger.py"
    ensure_event_logger(project_dir, template_logger, EMBEDDED_EVENT_LOGGER)
    ensure_gitignore_excludes_claude(project_dir)
    settings_path = update_settings(project_dir, '"$CLAUDE_PROJECT_DIR"/.claude/hooks/event-logger.py')
    exit_code = run_claude(project_dir, args.claude_cmd, args.claude_args)
    try:
        log_destination = args.log_destination.expanduser()
        mirror_logs(project_dir, log_destination)
    except Exception as exc:
        print(f"[claude-with-hooks] warning: failed to mirror logs: {exc}", file=sys.stderr)
        log_destination = args.log_destination.expanduser()
    print("[claude-with-hooks] hooks active via {}, logs mirrored to {}".format(settings_path, log_destination), file=sys.stderr)
    return exit_code

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
PYEOF
  chmod +x -- "$target"
}

LAUNCHER_PATH=""
if LAUNCHER_PATH=$(find_existing_launcher); then
  :
else
  LAUNCHER_PATH="$INSTALL_PATH"
  ensure_launcher "$LAUNCHER_PATH"
fi

if [[ "${CLAUDE_WRAPPER_DEBUG:-}" == "1" ]]; then
  echo "[wrapper] using launcher ${LAUNCHER_PATH}" >&2
fi

REAL_CLAUDE_CMD=$(resolve_real_claude_cmd || true)
if [[ -z "${REAL_CLAUDE_CMD}" ]]; then
  echo "[wrapper] error: could not locate a real 'claude' binary on PATH. Set CLAUDE_CMD=/full/path/to/claude" >&2
  exit 127
fi
if [[ "${CLAUDE_WRAPPER_DEBUG:-}" == "1" ]]; then
  echo "[wrapper] using real claude binary ${REAL_CLAUDE_CMD}" >&2
fi

exec python3 "$LAUNCHER_PATH" --claude-cmd "${REAL_CLAUDE_CMD}" -- "$@"
