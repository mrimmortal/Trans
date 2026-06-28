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

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is for macOS. Use scripts/deploy-linux.sh on Linux." >&2
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it from https://brew.sh, then rerun this script." >&2
  exit 1
fi

if ! has_supported_python; then
  if [[ "${YES}" -eq 1 ]]; then
    brew install python@3.11
  else
    echo "Python 3.11 or newer is required. Run: brew install python@3.11" >&2
    echo "Or rerun with --yes to install supported prerequisites." >&2
    exit 1
  fi
fi

if ! brew list portaudio >/dev/null 2>&1; then
  if [[ "${YES}" -eq 1 ]]; then
    brew install portaudio
  else
    echo "PortAudio is required for PyAudio. Run: brew install portaudio" >&2
    echo "Or rerun with --yes to install supported prerequisites." >&2
    exit 1
  fi
fi

if [[ "${INSTALL_NODE}" -eq 1 ]] && ! command -v node >/dev/null 2>&1; then
  if [[ "${YES}" -eq 1 ]]; then
    brew install node
  else
    echo "Node.js was requested but is not installed. Run: brew install node" >&2
    echo "Or rerun with --install-node --yes." >&2
    exit 1
  fi
fi

cd "${ROOT_DIR}"
exec python3 "${SCRIPT_DIR}/deploy.py" "${PASSTHROUGH[@]}"
