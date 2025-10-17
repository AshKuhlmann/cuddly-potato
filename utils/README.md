# Claude Tracker

Claude Tracker gives you an opt-in, transparent way to log every Claude Code hook event without touching the Claude CLI itself. The bootstrapper configures each project on-demand, keeps the logger script up to date, mirrors session data to a central location, and ships companion tools for viewing or aggregating the resulting logs.

---

## Highlights

- Automated `.claude` bootstrap that enables every hook event and keeps the logger executable in sync.
- Dual-format logging: raw JSON lines for auditing plus concise summaries that stay easy to scan or grep.
- Safe-by-design defaults—logs stay inside the project tree and mirrored copies land in `~/Documents/claude-logs/`.
- Drop-in shell wrapper that works with existing workflows (`claude ...`) and respects custom Claude CLI locations.
- Utilities for bulk collection, per-project exports, viewing sessions interactively, and uninstalling cleanly.

---

## Quick Start

### Prerequisites

- Claude CLI (install via Anthropic’s instructions).
- Python 3.9+ available on your PATH (used by the bootstrapper and helpers).
- A POSIX shell (bash/zsh) where you normally run `claude`.

### 1. Install the wrapper

Pick the option that matches how you prefer to launch `claude`:

- **Shell function wrapper (recommended for development shells)**  
  Adds a small function to your shell rc file that routes `claude` through the bootstrapper.
  ```bash
  ./scripts/install_claude_wrapper.sh
  ```

- **Standalone command wrapper (symlink on PATH)**  
  Symlinks `bin/claude-wrapper.sh` into a directory such as `/usr/local/bin` or `~/.local/bin`.
  ```bash
  ./bin/install-claude-wrapper.sh           # install as `claude`
  ./bin/install-claude-wrapper.sh --name c  # install under a custom name
  ```

After installation, restart your shell or `source` the modified rc file so the new command/function is active.

### 2. Launch Claude as usual

Run `claude` inside any project directory. On the first invocation per project, the bootstrapper:

1. Creates `.claude/hooks/event-logger.py` (from the repo copy or an embedded fallback).
2. Ensures `.claude/settings.local.json` points every hook event at the logger with the correct matcher settings.
3. Runs the real Claude CLI with your original arguments.
4. Mirrors `.claude/hook-logs/*` to `~/Documents/claude-logs/<sanitised-project>/`.

You will see a status line on stderr confirming that hooks are active and where logs were mirrored.

### 3. Inspect the logs

Per-project logs live at:

```
your-project/
└─ .claude/
   ├─ hooks/
   │  └─ event-logger.py
   ├─ hook-logs/
   │  ├─ <session>.jsonl
   │  └─ <session>_summary.log
   └─ settings.local.json
```

Mirrored copies are available at `~/Documents/claude-logs/<sanitised-project>/`, where the project path is converted into a filesystem-safe slug.

Use the interactive viewer to browse summaries and inspect raw payloads:

```bash
python3 scripts/view_logs.py
```

---

## Provided Commands & Scripts

| Path | Purpose | Key options |
|------|---------|-------------|
| `scripts/claude_with_hooks.py` | Core bootstrapper invoked by the wrapper. | `--project`, `--claude-cmd`, `--log-destination` |
| `scripts/install_claude_wrapper.sh` | Adds a `claude()` shell function to your rc files. | none |
| `scripts/uninstall_claude_wrapper.sh` | Removes the wrapper function, related symlinks, and embedded helper. | `--name`, `--keep-embedded` |
| `bin/install-claude-wrapper.sh` | Symlinks `bin/claude-wrapper.sh` into a directory on your PATH. | `--name`, `--force` |
| `bin/claude-wrapper.sh` | POSIX shell wrapper that locates or installs the Python launcher before delegating to the real CLI. | honors `CLAUDE_CMD`, `CLAUDE_WRAPPER_DEBUG` |
| `scripts/collect_claude_logs.py` | Prompts for a root directory and copies `.claude/hook-logs` from every project into `./logs/`. | interactive |
| `scripts/copy_project_logs.py` | Copies logs from a single project into `./logs/`. | `--dest` |
| `scripts/view_logs.py` | Interactive TUI-lite viewer for `_summary.log` files plus their raw JSON counterparts. | interactive |

Run any script with `--help` (when available) for additional details.

---

## Configuration Notes

- `CLAUDE_CMD` – forces the wrapper to launch a specific Claude binary (useful if your CLI lives outside `PATH`).
- `CLAUDE_WRAPPER_DEBUG=1` – prints diagnostic information from `bin/claude-wrapper.sh` about resolution order and paths.
- `--project PATH` (bootstrapper) – bootstrap and log as if you were running inside another directory.
- `--log-destination PATH` (bootstrapper) – override the mirror target directory.

Logs always stay inside the project tree first, using `$CLAUDE_PROJECT_DIR/.claude/hook-logs`. The summaries trim long strings to keep secrets out of the mirrored files; adjust the logger script if you need a different redaction policy.

---

## Uninstalling or Starting Fresh

If you set up the shell function wrapper:

```bash
./scripts/uninstall_claude_wrapper.sh
./scripts/uninstall_claude_wrapper.sh --name claude --keep-embedded  # leave the cached launcher in place
```

If you installed the symlinked command, remove the relevant symlink from `/usr/local/bin`, `/opt/homebrew/bin`, or `~/.local/bin`. The uninstall script above attempts this automatically when called without `--keep-embedded`.

To completely remove logging from a project, delete the generated `.claude/hooks/event-logger.py`, `.claude/settings.local.json`, and `.claude/hook-logs/` directory from that project.

---

## Manual Hook Setup

Prefer to manage the hooks yourself or audit the exact configuration? See `hooks_setup.md` for a copy-paste recipe that mirrors what the bootstrapper writes, including the full `event-logger.py` implementation and JSON hook configuration.

---

## Troubleshooting

- **`claude` still launches without hooks** – ensure your shell sourced the updated rc file (e.g., `source ~/.zshrc`) or confirm the symlinked command is ahead of the real binary on your `PATH`.
- **No logs appear** – verify the project allows the bootstrapper to write under `.claude/` and that your Claude session actually triggered hooks. The viewer expects summary files ending in `_summary.log`.
- **Custom Claude binary** – set `CLAUDE_CMD=/path/to/claude` before invoking the wrapper, or pass `--claude-cmd` directly to `scripts/claude_with_hooks.py`.
- **Multiple Python versions** – the wrapper uses `python3`. If that points to an unexpected interpreter, adjust your PATH or modify the wrapper scripts accordingly.

---

Claude Tracker aims to make collaborative or regulated development safer by providing an auditable record of Claude Code actions. Contributions, issues, and suggestions are welcome!
