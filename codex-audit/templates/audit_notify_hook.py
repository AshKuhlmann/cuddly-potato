#!/usr/bin/env python3
"""Codex notify hook that snapshots each turn into audit/turn_log.jsonl."""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
AUDIT_DIR = CODEX_HOME / "audit"
LOG_PATH = AUDIT_DIR / "turn_log.jsonl"
STATE_PATH = AUDIT_DIR / "state.json"
ERROR_LOG = AUDIT_DIR / "errors.log"
SESSIONS_DIR = CODEX_HOME / "sessions"
LOG_EXPORT_DIR = Path.home() / "Documents" / "llm_agent_logs"
SESSION_LOG_DIR = Path.home() / "Documents" / "codex-logs"


def _mirror_log(source: Path, prefix: str) -> None:
    if not source.exists():
        return
    LOG_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    dest = LOG_EXPORT_DIR / f"{prefix}_{source.name}"
    shutil.copy2(source, dest)


def _is_plan_update(text: str) -> bool:
    lowered = text.lower()
    if "updated plan" in lowered or "plan updated" in lowered:
        return True
    if lowered.startswith("plan:") or lowered.startswith("updated checklist"):
        return True
    if "checklist" in lowered or "todo" in lowered:
        return True
    if "□" in text or "- [" in text:
        return True
    return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_error(message: str) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = f"[{_utc_now()}] {message}\n"
    with ERROR_LOG.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def _load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {"sessions": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _log_error("state.json is corrupted; recreating")
        return {"sessions": {}}


def _save_state(state: Dict[str, Any]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(STATE_PATH)


def _parse_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _flatten_content(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    chunks: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _sanitize_filename(value: str) -> str:
    allowed = set("-_.")
    return "".join(ch if ch.isalnum() or ch in allowed else "_" for ch in value)


def _session_log_path(session_id: str) -> Path:
    safe_id = _sanitize_filename(session_id)
    return SESSION_LOG_DIR / f"{safe_id}.jsonl"


def _resolve_session_path(session_id: str, state: Dict[str, Any]) -> Path | None:
    sessions = state.setdefault("sessions", {})
    cached = sessions.get(session_id)
    if cached:
        candidate = Path(cached.get("path", ""))
        if candidate.exists():
            return candidate
    pattern = f"*{session_id}.jsonl"
    matches = list(SESSIONS_DIR.rglob(pattern))
    if not matches:
        return None
    sessions[session_id] = {"path": str(matches[0]), "offset": 0}
    return matches[0]


def _collect_events(session_path: Path, offset: int) -> tuple[int, List[Dict[str, Any]]]:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    if not session_path.exists():
        return offset, []
    with session_path.open("rb") as handle:
        handle.seek(offset)
        chunk = handle.read()
    if not chunk:
        return offset, []
    new_offset = offset + len(chunk)
    events: List[Dict[str, Any]] = []
    for line in chunk.decode("utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            _log_error(f"failed to parse session line: {exc}: {line[:120]}")
    return new_offset, events


def _summarize_turn(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    user_messages: List[str] = []
    assistant_messages: List[str] = []
    assistant_reasoning: List[str] = []
    assistant_plan_updates: List[str] = []
    assistant_tools: List[Dict[str, Any]] = []
    call_index: Dict[str, Dict[str, Any]] = {}
    token_counts: List[Any] = []
    approvals: List[Any] = []
    timeline: List[Dict[str, Any]] = []
    for event in events:
        etype = event.get("type")
        payload = event.get("payload", {})
        if etype == "response_item":
            payload_type = payload.get("type")
            if payload_type == "message":
                role = payload.get("role")
                text = _flatten_content(payload.get("content"))
                if role == "user":
                    user_messages.append(text)
                    timeline.append({"event": "user_message", "index": len(user_messages) - 1})
                elif role == "assistant":
                    assistant_messages.append(text)
                    timeline.append({"event": "assistant_message", "index": len(assistant_messages) - 1})
            elif payload_type == "reasoning":
                summary_items = payload.get("summary") or []
                summary_text = "\n".join(item.get("text", "") for item in summary_items if isinstance(item, dict))
                if summary_text:
                    if _is_plan_update(summary_text):
                        assistant_plan_updates.append(summary_text)
                        timeline.append({"event": "assistant_plan_update", "index": len(assistant_plan_updates) - 1})
                    else:
                        assistant_reasoning.append(summary_text)
                        timeline.append({"event": "assistant_reasoning", "index": len(assistant_reasoning) - 1})
            elif payload_type == "function_call":
                call_id = payload.get("call_id")
                call_entry = {
                    "call_id": call_id,
                    "tool_name": payload.get("name"),
                    "arguments": _parse_jsonish(payload.get("arguments")),
                    "started_at": event.get("timestamp"),
                    "outputs": [],
                }
                assistant_tools.append(call_entry)
                tool_idx = len(assistant_tools) - 1
                timeline.append({"event": "assistant_tool_call", "index": tool_idx})
                if call_id:
                    call_index[call_id] = call_entry
            elif payload_type == "function_call_output":
                call_id = payload.get("call_id")
                target = call_index.get(call_id)
                if not target:
                    target = {
                        "call_id": call_id,
                        "tool_name": None,
                        "arguments": None,
                        "started_at": None,
                        "outputs": [],
                    }
                    assistant_tools.append(target)
                    tool_idx = len(assistant_tools) - 1
                    if call_id:
                        call_index[call_id] = target
                target["outputs"].append(
                    {
                        "timestamp": event.get("timestamp"),
                        "result": _parse_jsonish(payload.get("output")),
                    }
                )
                tool_idx = assistant_tools.index(target)
                timeline.append(
                    {
                        "event": "assistant_tool_output",
                        "index": tool_idx,
                        "output_index": len(target["outputs"]) - 1,
                    }
                )
        elif etype == "event_msg":
            msg_type = payload.get("type")
            if msg_type == "token_count":
                token_counts.append(payload.get("info"))
            elif msg_type == "approval_request":
                approvals.append(payload)
    return {
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "assistant_reasoning": assistant_reasoning,
        "assistant_plan_updates": assistant_plan_updates,
        "assistant_tool_calls": assistant_tools,
        "token_counts": token_counts,
        "approvals": approvals,
        "event_count": len(events),
        "timeline": timeline,
    }


def _append_log(record: Dict[str, Any]) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    _mirror_log(LOG_PATH, "codex")


def _append_session_record(session_id: str, record: Dict[str, Any]) -> None:
    path = _session_log_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _main() -> int:
    if len(sys.argv) != 2:
        _log_error("notify hook requires exactly 1 argument")
        return 0
    try:
        notification = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        _log_error(f"invalid notification payload: {exc}")
        return 0

    session_id = notification.get("thread-id") or notification.get("thread_id")
    if not session_id:
        _log_error("notification missing thread-id")
        return 0

    state = _load_state()
    session_path = _resolve_session_path(session_id, state)
    if not session_path:
        _log_error(f"unable to locate session log for {session_id}")
        return 0

    session_entry = state.setdefault("sessions", {}).setdefault(session_id, {"path": str(session_path), "offset": 0})
    offset = session_entry.get("offset", 0)
    new_offset, events = _collect_events(session_path, offset)
    if not events:
        session_entry["offset"] = new_offset
        _save_state(state)
        return 0

    session_entry["offset"] = new_offset
    state.setdefault("sessions", {})[session_id] = {
        "path": str(session_path),
        "offset": new_offset,
    }
    _save_state(state)

    summary = _summarize_turn(events)
    record = {
        "timestamp": _utc_now(),
        "session": {
            "id": session_id,
            "cwd": notification.get("cwd"),
            "log_path": str(session_path),
        },
        "turn": {
            "id": notification.get("turn-id") or notification.get("turn_id"),
            "input_messages": notification.get("input-messages", []),
            "last_assistant_message": notification.get("last-assistant-message"),
            "log_span": {
                "start": offset,
                "end": new_offset,
            },
        },
        "messages": {
            "user": summary["user_messages"],
            "assistant": summary["assistant_messages"],
            "assistant_reasoning": summary["assistant_reasoning"],
            "assistant_plan_updates": summary["assistant_plan_updates"],
        },
        "assistant_tool_calls": summary["assistant_tool_calls"],
        "telemetry": {
            "token_counts": summary["token_counts"],
            "approvals": summary["approvals"],
            "event_count": summary["event_count"],
        },
        "timeline": summary["timeline"],
    }
    _append_log(record)
    _append_session_record(session_id, record)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except Exception as exc:  # noqa: BLE001
        _log_error(f"unexpected error: {exc}")
        raise SystemExit(0)
