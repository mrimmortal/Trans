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

install_python_command() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv python3-pip python3-dev build-essential portaudio19-dev"
  elif command -v dnf >/dev/null 2>&1; then
    echo "sudo dnf install -y python3 python3-pip python3-devel gcc portaudio-devel"
  elif command -v yum >/dev/null 2>&1; then
    echo "sudo yum install -y python3 python3-pip python3-devel gcc portaudio-devel"
  elif command -v pacman >/dev/null 2>&1; then
    echo "sudo pacman -Sy --needed python python-pip base-devel portaudio"
  else
    echo ""
  fi
}

ask_yes_no() {
  local prompt="$1"
  local answer
  read -r -p "${prompt} [y/N] " answer
  [[ "${answer}" == "y" || "${answer}" == "Y" ]]
}

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script is for Linux. Use scripts/deploy-macos.sh on macOS." >&2
  exit 1
fi

if ! has_supported_python; then
  INSTALL_COMMAND="$(install_python_command)"
  echo "Python 3.11 or newer is required."
  if [[ -z "${INSTALL_COMMAND}" ]]; then
    echo "Install Python 3.11 or newer, venv, pip, build tools, and PortAudio, then rerun this script." >&2
    exit 1
  fi
  echo "Suggested install command:"
  echo "  ${INSTALL_COMMAND}"
  if ask_yes_no "Run this install command now?"; then
    bash -lc "${INSTALL_COMMAND}"
  else
    echo "Install the required packages, then rerun this script." >&2
    exit 1
  fi
fi

PYTHON_BIN="$(find_python)"

cd "${CORE_DIR}"
if [[ ! -x ".venv/bin/python" ]]; then
  "${PYTHON_BIN}" -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py --host "${HOST}" --port "${PORT}" --device "${DEVICE}" --compute-type "${COMPUTE_TYPE}"
