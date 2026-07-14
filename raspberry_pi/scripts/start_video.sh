#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RASPBERRY_PI_DIR="$ROOT_DIR/raspberry_pi"
RUN_DIR="$RASPBERRY_PI_DIR/.run"
mkdir -p "$RUN_DIR"
cd "$RASPBERRY_PI_DIR"

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

start_service video_stream python3 -m video.rtp_streamer
echo "logs: $RUN_DIR"
