#!/usr/bin/env bash
# Installs a shell wrapper that routes all `claude` invocations through the
# `scripts/claude_with_hooks.py` bootstrapper so every project gets the same
# hook setup and log mirroring.
#
# Safe to run multiple times; the wrapper block is updated idempotently.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WRAPPER_PY="${PROJECT_ROOT}/scripts/claude_with_hooks.py"

if [[ ! -f "${WRAPPER_PY}" ]]; then
  echo "error: expected bootstrap script at ${WRAPPER_PY}" >&2
  exit 1
fi

MARKER_BEGIN="# >>> claude hooks wrapper >>>"
MARKER_END="# <<< claude hooks wrapper <<<"
BLOCK_TEMP="$(mktemp)"

cleanup() {
  rm -f "${BLOCK_TEMP}"
}
trap cleanup EXIT

{
  echo "${MARKER_BEGIN}"
  printf 'claude() {\n'
  printf '  python3 %q -- "$@"\n' "${WRAPPER_PY}"
  printf '}\n'
  echo "export -f claude 2>/dev/null || true  # shellcheck disable=SC3045"
  echo "${MARKER_END}"
} > "${BLOCK_TEMP}"

install_into() {
  local rcfile="$1"
  mkdir -p "$(dirname "${rcfile}")"
  touch "${rcfile}"
  local has_marker=1
  if command -v rg >/dev/null 2>&1; then
    if rg --fixed-strings --quiet "${MARKER_BEGIN}" "${rcfile}" 2>/dev/null; then
      has_marker=0
    fi
  elif grep -Fq "${MARKER_BEGIN}" "${rcfile}"; then
    has_marker=0
  fi

  if [[ ${has_marker} -eq 0 ]]; then
    # fallback if ripgrep missing
    tmpfile="$(mktemp)"
    awk -v start="${MARKER_BEGIN}" -v end="${MARKER_END}" '
      BEGIN {in_block=0}
      $0 == start {in_block=1; next}
      $0 == end {in_block=0; next}
      in_block == 0 {print}
    ' "${rcfile}" > "${tmpfile}"
    cat "${tmpfile}" > "${rcfile}"
    rm -f "${tmpfile}"
  fi

  cat "${BLOCK_TEMP}" >> "${rcfile}"
  echo "installed wrapper in ${rcfile}"
}

targets=()

if [[ "${SHELL:-}" == *"zsh" ]] || [[ -f "${HOME}/.zshrc" ]]; then
  targets+=("${HOME}/.zshrc")
fi
if [[ "${SHELL:-}" == *"bash" ]] || [[ -f "${HOME}/.bashrc" ]]; then
  targets+=("${HOME}/.bashrc")
fi
if [[ "${SHELL:-}" == *"bash" ]] && [[ -f "${HOME}/.bash_profile" ]]; then
  targets+=("${HOME}/.bash_profile")
fi

if [[ ${#targets[@]} -eq 0 ]]; then
  targets=("${HOME}/.zshrc")
fi

for rc in "${targets[@]}"; do
  install_into "${rc}"
done

cat <<EOF

Claude wrapper installed. Restart your shell or run:

  source "${targets[0]}"

to pick up the updated function immediately.
EOF
