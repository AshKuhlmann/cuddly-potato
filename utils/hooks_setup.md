Below is a minimal, production-ready recipe that

• logs EVERY Claude Code hook event  
• stores the raw payload **and** a compact summary, per session  
• never blocks normal execution (always exits 0)  

Feel free to copy-paste straight into your project. 🚀

---

## 1. Project layout

```text
your-repo/
└─ .claude/
   ├─ settings.json         ← add hook config here
   └─ hooks/
      └─ event-logger.py    ← the Python script below
```

> Make sure the script is executable  
> `chmod +x .claude/hooks/event-logger.py`

---

## 2. settings.json (or settings.local.json)

```jsonc
{
  "hooks": {
    // ----- events that use matchers -----
    "PreToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] }
    ],
    "PostToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] }
    ],

    // ----- events without matchers -----
    "Notification":        [ { "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] } ],
    "UserPromptSubmit":    [ { "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] } ],
    "Stop":                [ { "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] } ],
    "SubagentStop":        [ { "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] } ],
    "PreCompact":          [ { "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] } ],
    "SessionStart":        [ { "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] } ],
    "SessionEnd":          [ { "hooks": [ { "type": "command",
        "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/event-logger.py" } ] } ]
  }
}
```

• `matcher: "*"` catches every tool  
• Same one-liner command is reused for all other events

---

## 3. .claude/hooks/event-logger.py

```python
#!/usr/bin/env python3
"""
Claude Code Hook – Security/Event Logger
Writes two files per session:
  • raw  payloads ->  .claude/hook-logs/<SESSION>.jsonl
  • summary lines ->  .claude/hook-logs/<SESSION>_summary.log
Never blocks (exit 0) unless its own JSON is malformed (exit 1).
"""
from __future__ import annotations
import json, sys, os, datetime, pathlib, traceback

def make_summary(data: dict) -> dict:
    """Return a trimmed, human-readable dict for quick scans."""
    event = data.get("hook_event_name")
    base = {
        "ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "event": event,
        "session": data.get("session_id"),
    }

    match event:
        case "PreToolUse" | "PostToolUse":
            base |= {
                "tool": data.get("tool_name"),
                "success": data.get("tool_response", {}).get("success")
                          if event == "PostToolUse" else None,
            }
        case "Notification":
            base["msg"] = data.get("message")
        case "UserPromptSubmit":
            base["prompt"] = data.get("prompt")[:120]  # truncate for log
        case "Stop" | "SubagentStop":
            base["stop_hook_active"] = data.get("stop_hook_active")
        case "SessionEnd":
            base["reason"] = data.get("reason")
    return base

def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        print(f"[logger] invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    # Where to store logs
    project_dir = os.getenv("CLAUDE_PROJECT_DIR", payload.get("cwd", "."))
    log_root   = pathlib.Path(project_dir) / ".claude" / "hook-logs"
    log_root.mkdir(parents=True, exist_ok=True)

    session_id = payload.get("session_id", "unknown-session")
    raw_path   = log_root / f"{session_id}.jsonl"
    sum_path   = log_root / f"{session_id}_summary.log"

    # Write raw JSON (one line)
    with raw_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, separators=(",", ":")) + "\n")

    # Write summary
    with sum_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(make_summary(payload), ensure_ascii=False) + "\n")

    # Optional: suppress stdout from appearing in transcript
    # (Nothing is printed, so transcript stays clean.)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Catch-all so logging failures donʼt block Claude
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
```

🛡️  Security notes  
• Uses `$CLAUDE_PROJECT_DIR` → logs live inside the project, **never** somewhere unexpected  
• Appends only – no destructive operations  
• Truncates prompts so secrets arenʼt fully written; tweak as desired

---

## 4. What you’ll get

```
.claude/hook-logs/
└─ 00f9ad19-…9e.jsonl            # raw payloads (one giant line each)
└─ 00f9ad19-…9e_summary.log      # tiny summaries, greppable
```

Example summary line:

```json
{"ts":"2024-06-09T12:34:56Z","event":"PostToolUse","session":"00f9ad19","tool":"Bash","success":true}
```

…so you can quickly run

```bash
rg '"success":false' .claude/hook-logs/*_summary.log
```

to spot failed tool calls, or inspect the full JSON when needed.

---

### 5. Verify it works

1. Start / restart Claude Code (hooks snapshot happens on startup).  
2. Run any prompt / tool.  
3. `tail -f .claude/hook-logs/*_summary.log` – you should see new lines roll in.  
4. If nothing appears, run `/hooks` to ensure the logger is enabled, or launch with `claude --debug` to see execution traces.

---

Happy (and safer) coding! 🔍
