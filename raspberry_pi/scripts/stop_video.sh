#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RASPBERRY_PI_DIR="$ROOT_DIR/raspberry_pi"
RUN_DIR="$RASPBERRY_PI_DIR/.run"

for name in video_stream; do
  pid_file="$RUN_DIR/$name.pid"
  if [[ ! -f "$pid_file" ]]; then
    echo "$name is not recorded as running"
    continue
  fi
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill -INT "$pid"
    for _ in {1..50}; do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid"
    fi
    echo "stopped $name (PID $pid)"
  fi
  rm -f "$pid_file"
done
