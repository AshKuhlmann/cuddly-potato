#!/usr/bin/env bash
# Removes the Claude wrapper function from common shell RC files and deletes
# the optional launcher symlink/embedded helper so you can reinstall cleanly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WRAPPER_PATH="${PROJECT_ROOT}/bin/claude-wrapper.sh"
MARKER_BEGIN="# >>> claude hooks wrapper >>>"
MARKER_END="# <<< claude hooks wrapper <<<"
INSTALL_DIR="$HOME/.local/share/claude-hooks"
EMBEDDED_LAUNCHER="${INSTALL_DIR}/claude_with_hooks.py"

NAME="claude"
PURGE_EMBEDDED=1

usage() {
  cat <<'EOF'
Usage: uninstall_claude_wrapper.sh [--name claude] [--keep-embedded]

  --name <name>      Command name that was installed (default: claude)
  --keep-embedded    Leave ~/.local/share/claude-hooks/claude_with_hooks.py in place
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      shift
      [[ $# -gt 0 ]] || { echo "error: --name requires a value" >&2; exit 1; }
      NAME="$1"
      ;;
    --keep-embedded)
      PURGE_EMBEDDED=0
      ;;
    -*)
      echo "error: unknown flag $1" >&2
      usage
      ;;
    *)
      echo "error: unexpected positional argument $1" >&2
      usage
      ;;
  esac
  shift
done

info() {
  printf '%s\n' "$*"
}

resolve_path() {
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

strip_wrapper_block() {
  local rcfile="$1"
  [[ -f "$rcfile" ]] || return 1
  if ! grep -Fqs "${MARKER_BEGIN}" "$rcfile"; then
    return 2
  fi
  local tmp
  tmp="$(mktemp)"
  awk -v start="${MARKER_BEGIN}" -v end="${MARKER_END}" '
    $0 == start {in_block=1; next}
    $0 == end {in_block=0; next}
    in_block != 1 {print}
  ' "$rcfile" > "$tmp"
  cat "$tmp" > "$rcfile"
  rm -f "$tmp"
  return 0
}

remove_shell_blocks() {
  local removed_any=0
  local rcfiles=()

  if [[ "${SHELL:-}" == *"zsh" ]] || [[ -f "${HOME}/.zshrc" ]]; then
    rcfiles+=("${HOME}/.zshrc")
  fi
  if [[ "${SHELL:-}" == *"bash" ]] || [[ -f "${HOME}/.bashrc" ]]; then
    rcfiles+=("${HOME}/.bashrc")
  fi
  if [[ "${SHELL:-}" == *"bash" ]] && [[ -f "${HOME}/.bash_profile" ]]; then
    rcfiles+=("${HOME}/.bash_profile")
  fi

  if [[ ${#rcfiles[@]} -eq 0 ]]; then
    rcfiles+=("${HOME}/.zshrc")
  fi

  for rc in "${rcfiles[@]}"; do
    if strip_wrapper_block "$rc"; then
      info "Removed wrapper block from ${rc}"
      removed_any=1
    fi
  done

  if [[ $removed_any -eq 0 ]]; then
    info "No wrapper block found in shell configuration files."
  fi
}

remove_symlink_if_matches() {
  local target="$1"
  [[ -e "$target" ]] || return 1

  if [[ -L "$target" ]]; then
    local resolved_target resolved_wrapper
    resolved_target="$(resolve_path "$target")"
    resolved_wrapper="$(resolve_path "$WRAPPER_PATH")"
    if [[ "$resolved_target" == "$resolved_wrapper" ]]; then
      rm -f "$target"
      info "Removed symlink ${target}"
      return 0
    fi
  fi

  return 2
}

remove_symlinks() {
  local removed=0
  local candidate_dirs=("/usr/local/bin" "/opt/homebrew/bin" "$HOME/.local/bin")
  local dir
  for dir in "${candidate_dirs[@]}"; do
    remove_symlink_if_matches "${dir}/${NAME}" && removed=1 || true
  done
  if [[ $removed -eq 0 ]]; then
    info "No wrapper symlink matching '${NAME}' found in standard install locations."
  fi
}

purge_embedded_launcher() {
  [[ $PURGE_EMBEDDED -eq 1 ]] || return 0
  if [[ -f "${EMBEDDED_LAUNCHER}" ]]; then
    if grep -q "Bootstrap Claude Code hooks" "${EMBEDDED_LAUNCHER}" 2>/dev/null; then
      rm -f "${EMBEDDED_LAUNCHER}"
      info "Removed embedded launcher ${EMBEDDED_LAUNCHER}"
      # remove directory if empty
      rmdir "${INSTALL_DIR}" 2>/dev/null || true
    else
      info "Left ${EMBEDDED_LAUNCHER} (did not look like the embedded launcher)."
    fi
  fi
}

remove_shell_blocks
remove_symlinks
purge_embedded_launcher

info "Uninstall complete. Open a new shell or reload your profile if needed."
