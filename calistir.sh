#!/usr/bin/env bash
# Dock'i baslatir. Bu sunucuda X ekrani :99 uzerinde calisir.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "HATA: .venv yok. Kurulum: /usr/bin/python3 -m venv .venv && .venv/bin/pip install PySide6" >&2
    exit 1
fi

# Qt6 xcb eklentisi libxcb-cursor'a ihtiyac duyar; sistemde olmadigi icin repo icinden verilir.
export LD_LIBRARY_PATH="$PWD/libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export DISPLAY="${DISPLAY:-:99}"

exec .venv/bin/python main.py "$@"
