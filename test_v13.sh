#!/usr/bin/env bash
# v13: gercek mpv (MPRIS) + http artUrl + track gecisi gecikme testi.
set -euo pipefail
cd "$(dirname "$0")"
export DISPLAY="${DISPLAY:-:99}"
export LD_LIBRARY_PATH="$PWD/libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export QT_QPA_PLATFORM=xcb
PORT="${PORT:-8897}"
LOG="$(mktemp)"
pkill -f mpv.AppImage 2>/dev/null || true
pkill -f "http.server $PORT" 2>/dev/null || true
( cd "$HOME/mpv-test" && setsid /usr/bin/python3 -m http.server "$PORT" --bind 127.0.0.1 \
    >/tmp/dock-v13-http.log 2>&1 < /dev/null & )
sleep 0.5
setsid "$HOME/mpv-test/mpv.AppImage" --no-video --ao=null --idle=yes \
  --input-ipc-server=/tmp/mpv.sock --script="$HOME/mpv-test/mpris.so" \
  "$HOME/mpv-test/test.m4a" >/tmp/dock-v13-mpv.log 2>&1 < /dev/null &
sleep 2
DOCK_SAHTE_ARTURL="http://127.0.0.1:$PORT/kapak.png" \
DOCK_SAHTE_ARTURL_2="http://127.0.0.1:$PORT/kapak2.png" \
DOCK_KAPAK_LOG=/tmp/dock-v13-kapak.log \
DOCK_LATENCY_LOG="$LOG" setsid .venv/bin/python main.py >/tmp/dock-v13.log 2>&1 < /dev/null &
sleep 4
xdotool mousemove 1138 834; sleep 0.3; xdotool click 1; sleep 2
: > "$LOG"
printf '%s\n' '{"command":["loadfile","'"$HOME"'/mpv-test/test2.m4a"]}' \
  | socat - UNIX-CONNECT:/tmp/mpv.sock >/dev/null 2>&1 || true
sleep 3
python3 - "$LOG" <<'PY'
import sys
v = sorted(float(x) for x in open(sys.argv[1]))
print(f"kare araligi n={len(v)} max={v[-1]:.1f} ms p95={v[int(len(v)*0.95)]:.1f} ms")
PY
pkill -f mpv.AppImage 2>/dev/null || true
pkill -f "http.server $PORT" 2>/dev/null || true
