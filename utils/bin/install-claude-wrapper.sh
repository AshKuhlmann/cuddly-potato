#!/usr/bin/env bash
set -euo pipefail

# Convenience installer for the Claude wrapper.
# - Symlinks bin/claude-wrapper.sh to a bin dir on your PATH.
# - Prefers /usr/local/bin if writable; falls back to ~/.local/bin.
#
# Usage:
#   bin/install-claude-wrapper.sh [--name claude] [--force]
#
# Options:
#   --name  <name>   Install as this command name (default: claude)
#   --force          Overwrite existing target if present

NAME="claude"
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      shift
      [[ $# -gt 0 ]] || { echo "error: --name requires a value" >&2; exit 1; }
      NAME="$1"
      ;;
    --force)
      FORCE=1
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      echo "usage: $0 [--name claude] [--force]" >&2
      exit 1
      ;;
  esac
  shift
done

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
WRAPPER_PATH="${REPO_ROOT}/bin/claude-wrapper.sh"

if [[ ! -x "$WRAPPER_PATH" ]]; then
  echo "error: wrapper not found or not executable at $WRAPPER_PATH" >&2
  echo "hint: ensure you checked out the repo and that bin/claude-wrapper.sh exists." >&2
  exit 1
fi

# Decide install directory
choose_dir() {
  local candidates=("/usr/local/bin" "/opt/homebrew/bin" "$HOME/.local/bin")
  for d in "${candidates[@]}"; do
    if [[ -d "$d" && -w "$d" ]] || mkdir -p "$d" 2>/dev/null; then
      if [[ -w "$d" ]]; then
        echo "$d"; return 0
      fi
    fi
  done
  # Fallback to ~/.local/bin even if not writable (will fail later visibly)
  echo "$HOME/.local/bin"
}

TARGET_DIR=$(choose_dir)
TARGET="$TARGET_DIR/$NAME"

if [[ -e "$TARGET" && "$FORCE" != 1 ]]; then
  echo "error: $TARGET already exists. Re-run with --force to replace, or use --name to install under a different name." >&2
  exit 1
fi

mkdir -p -- "$TARGET_DIR"
ln -sfn "$WRAPPER_PATH" "$TARGET"
chmod +x "$WRAPPER_PATH"

echo "Installed: $TARGET -> $WRAPPER_PATH"

# PATH guidance if needed
case ":$PATH:" in
  *:"$TARGET_DIR":*) ;;
  *)
    echo
    echo "Note: $TARGET_DIR is not on your PATH. Add one of these to your shell profile:"
    echo "  Bash/Zsh:  echo 'export PATH=\"$TARGET_DIR:\$PATH\"' >> ~/.bashrc  # or ~/.zshrc"
    echo "  Fish:      set -Ux fish_user_paths $TARGET_DIR \$fish_user_paths"
    ;;
esac

echo
echo "Try: $NAME --help (or whatever Claude args you use)"

