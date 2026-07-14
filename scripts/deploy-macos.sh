#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CORE_DIR="${ROOT_DIR}/CoreSTT"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8020}"
DEVICE="${DEVICE:-cpu}"
COMPUTE_TYPE="${COMPUTE_TYPE:-default}"

has_supported_python() {
  local candidate
  for candidate in "${PYTHON:-}" python3.13 python3.12 python3.11 python3; do
    [[ -z "${candidate}" ]] && continue
    if command -v "${candidate}" >/dev/null 2>&1; then
      "${candidate}" - <<'PY' >/dev/null 2>&1 && return 0
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
    fi
  done
  return 1
}

find_python() {
  local candidate
  for candidate in "${PYTHON:-}" python3.13 python3.12 python3.11 python3; do
    [[ -z "${candidate}" ]] && continue
    if command -v "${candidate}" >/dev/null 2>&1; then
      if "${candidate}" - <<'PY' >/dev/null 2>&1; then
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
        echo "${candidate}"
        return 0
      fi
    fi
  done
  return 1
}

ask_yes_no() {
  local prompt="$1"
  local answer
  read -r -p "${prompt} [y/N] " answer
  [[ "${answer}" == "y" || "${answer}" == "Y" ]]
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is for macOS. Use scripts/deploy-linux.sh on Linux." >&2
  exit 1
fi

if ! has_supported_python; then
  echo "Python 3.11 or newer is required."
  if command -v brew >/dev/null 2>&1 && ask_yes_no "Install Python 3.11 with Homebrew now?"; then
    brew install python@3.11
  else
    echo "Install Python 3.11 or newer, then rerun this script." >&2
    exit 1
  fi
fi

if command -v brew >/dev/null 2>&1 && ! brew list portaudio >/dev/null 2>&1; then
  echo "PyAudio may require PortAudio on macOS."
  ask_yes_no "Install PortAudio with Homebrew now?" && brew install portaudio
fi

PYTHON_BIN="$(find_python)"

cd "${CORE_DIR}"
if [[ ! -x ".venv/bin/python" ]]; then
  "${PYTHON_BIN}" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py --host "${HOST}" --port "${PORT}" --device "${DEVICE}" --compute-type "${COMPUTE_TYPE}"
