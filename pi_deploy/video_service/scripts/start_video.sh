#!/usr/bin/env bash
set -euo pipefail

SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$SERVICE_DIR/.run"
mkdir -p "$RUN_DIR"
cd "$SERVICE_DIR"

start_service() {
  local name="$1"
  shift
  local pid_file="$RUN_DIR/$name.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name is already running (PID $(cat "$pid_file"))"
    return
  fi
  nohup "$@" >"$RUN_DIR/$name.log" 2>&1 &
  echo $! >"$pid_file"
  echo "started $name (PID $!)"
}

start_service video_stream python3 main.py
echo "logs: $RUN_DIR"
