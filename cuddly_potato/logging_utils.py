import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredLogger:
    """Emit structured JSON logs that remain easy to parse in automation."""

    def __init__(self, stream=None, verbose: bool = False):
        self.stream = stream or sys.stderr
        self.verbose = verbose

    def _write(self, payload: Dict[str, Any]) -> None:
        self.stream.write(json.dumps(payload, default=str) + "\n")
        self.stream.flush()

    def log(
        self,
        level: str,
        event: str,
        message: Optional[str] = None,
        **fields: Any,
    ) -> None:
        """Emit a structured log entry."""
        if level == "debug" and not self.verbose:
            return

        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
        }
        if message is not None:
            payload["message"] = message
        payload.update(fields)
        self._write(payload)

    def command_start(self, command: str, **fields: Any) -> None:
        self.log("debug", "command_start", command=command, **fields)

    def command_result(
        self,
        command: str,
        status: str,
        exit_code: int,
        message: Optional[str] = None,
        **fields: Any,
    ) -> None:
        level = "info" if exit_code == 0 else "error"
        self.log(
            level,
            "command_result",
            message,
            command=command,
            status=status,
            exit_code=exit_code,
            **fields,
        )

