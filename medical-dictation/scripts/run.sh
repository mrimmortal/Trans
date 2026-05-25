#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PID=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run.sh mac-dev     Start backend + frontend for macOS development
  ./scripts/run.sh uat-check   Compile backend and build frontend with UAT env
EOF
}

load_env() {
  set -a
  # shellcheck disable=SC1090
  source "$1"
  set +a
}

python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    echo "$PYTHON_BIN"
  elif command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo "Python 3 is required but was not found on PATH." >&2
    exit 1
  fi
}

requirements_fingerprint() {
  local requirements_file="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$requirements_file" | awk '{print $1}'
  else
    sha256sum "$requirements_file" | awk '{print $1}'
  fi
}

ensure_backend_venv() {
  local requirements_file="$1"
  local base_name
  local expected_hash
  local marker_file

  base_name="$(basename "$requirements_file")"

  cd "$BACKEND_DIR"
  if [[ ! -d "$BACKEND_DIR/venv" ]]; then
    "$(python_bin)" -m venv "$BACKEND_DIR/venv"
  fi

  # shellcheck disable=SC1091
  source "$BACKEND_DIR/venv/bin/activate"

  expected_hash="$(requirements_fingerprint "$requirements_file")"
  marker_file="$BACKEND_DIR/venv/.${base_name}.sha256"

  if [[ ! -f "$marker_file" ]] || [[ "$(cat "$marker_file")" != "$expected_hash" ]]; then
    python -m pip install --upgrade pip
    python -m pip install -r "$requirements_file"
    printf '%s' "$expected_hash" > "$marker_file"
  fi
}

node_run() {
  local script_name="$1"
  if command -v pnpm >/dev/null 2>&1; then
    pnpm "$script_name"
  else
    npm run "$script_name"
  fi
}

mac_dev() {
  cleanup() {
    if [[ -n "${BACKEND_PID:-}" ]]; then
      kill "$BACKEND_PID" >/dev/null 2>&1 || true
    fi
  }
  trap cleanup EXIT INT TERM

  cd "$BACKEND_DIR"
  load_env "$BACKEND_DIR/.env.mac"
  ensure_backend_venv "$BACKEND_DIR/requirements-mac.txt"

  python run.py &
  BACKEND_PID=$!

  sleep 3

  cd "$FRONTEND_DIR"
  load_env "$FRONTEND_DIR/.env.local.mac"
  export PORT="${FRONTEND_PORT:-3000}"
  node_run dev
}

uat_check() {
  cd "$BACKEND_DIR"
  load_env "$BACKEND_DIR/.env.uat"
  "$(python_bin)" -m compileall app

  cd "$FRONTEND_DIR"
  load_env "$FRONTEND_DIR/.env.uat"
  node_run build
}

case "${1:-}" in
  mac-dev)
    mac_dev
    ;;
  uat-check)
    uat_check
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
