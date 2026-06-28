#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

INSTALL_NODE=0
YES=0
PASSTHROUGH=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-node)
      INSTALL_NODE=1
      PASSTHROUGH+=("$1")
      shift
      ;;
    --yes|-y)
      YES=1
      shift
      ;;
    *)
      PASSTHROUGH+=("$1")
      shift
      ;;
  esac
done

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

detect_install_command() {
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

run_install_command() {
  local command_text="$1"
  if [[ -z "${command_text}" ]]; then
    echo "No supported Linux package manager was detected. Install Python 3.11+, venv, pip, build tools, and PortAudio manually." >&2
    exit 1
  fi
  if [[ "${YES}" -eq 1 ]]; then
    bash -lc "${command_text}"
  else
    echo "Missing supported Python or OS audio/build prerequisites." >&2
    echo "Run this command, then rerun the script:" >&2
    echo "  ${command_text}" >&2
    echo "Or rerun with --yes to execute it automatically." >&2
    exit 1
  fi
}

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script is for Linux. Use scripts/deploy-macos.sh on macOS." >&2
  exit 1
fi

INSTALL_COMMAND="$(detect_install_command)"
if ! has_supported_python; then
  run_install_command "${INSTALL_COMMAND}"
fi

if [[ "${INSTALL_NODE}" -eq 1 ]] && ! command -v node >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    NODE_COMMAND="sudo apt-get update && sudo apt-get install -y nodejs npm"
  elif command -v dnf >/dev/null 2>&1; then
    NODE_COMMAND="sudo dnf install -y nodejs npm"
  elif command -v yum >/dev/null 2>&1; then
    NODE_COMMAND="sudo yum install -y nodejs npm"
  elif command -v pacman >/dev/null 2>&1; then
    NODE_COMMAND="sudo pacman -Sy --needed nodejs npm"
  else
    NODE_COMMAND=""
  fi
  if [[ -z "${NODE_COMMAND}" ]]; then
    echo "Node.js was requested, but no supported package manager was detected." >&2
    exit 1
  fi
  if [[ "${YES}" -eq 1 ]]; then
    bash -lc "${NODE_COMMAND}"
  else
    echo "Node.js was requested but is not installed. Run:" >&2
    echo "  ${NODE_COMMAND}" >&2
    echo "Or rerun with --install-node --yes." >&2
    exit 1
  fi
fi

cd "${ROOT_DIR}"
exec python3 "${SCRIPT_DIR}/deploy.py" "${PASSTHROUGH[@]}"
