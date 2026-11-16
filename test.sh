#!/usr/bin/env bash
# Dock'u calistirir, kanit/ altina 6 ekran goruntusu ve olcum yazar.
set -euo pipefail
cd "$(dirname "$0")"

export LD_LIBRARY_PATH="$PWD/libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export DISPLAY="${DISPLAY:-:99}"
PY="$PWD/.venv/bin/python"
mkdir -p kanit

cfg() {  # cfg <anahtar> <json-deger>
    "$PY" - "$1" "$2" <<'PY'
import json, sys
from pathlib import Path
p = Path.home() / ".config" / "dock" / "ayar.json"
p.parent.mkdir(parents=True, exist_ok=True)
veri = json.loads(p.read_text()) if p.is_file() else {
    "autoHide": False, "iconSize": 76, "buyutme": 1.9, "kenarBosluk": 12, "sabitlenen": []}
veri[sys.argv[1]] = json.loads(sys.argv[2])
p.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

durdur() {
    if [ -f /tmp/dock-test.pid ]; then
        kill "$(cat /tmp/dock-test.pid)" 2>/dev/null || true
        sleep 0.4
        rm -f /tmp/dock-test.pid
    fi
    for p in $(pgrep -f '\.venv/bin/python main\.py' || true); do
        [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$PWD" ] && kill "$p" 2>/dev/null || true
    done
}

basla() {
    durdur
    setsid "$PY" main.py >>kanit/oturum.log 2>&1 < /dev/null &
    echo $! > /tmp/dock-test.pid
    sleep 2
}

cfg sabitlenen '[]'
cfg kenarBosluk 12
cfg iconSize 76
cfg autoHide false
# 3. ikonun ekran koordinati (varsayilan ayarlarla hesaplanir).
read -r IX IY < <("$PY" - <<'PY'
import json
from pathlib import Path
from dock.uygulamalar import onerilen_uygulamalar, secilenler, tara
from dock.ayarlar import VARSAYILAN
p = Path.home() / ".config" / "dock" / "ayar.json"
ayar = {**VARSAYILAN, **json.loads(p.read_text())}
u = tara()
h = onerilen_uygulamalar(u)
sec = secilenler(h, ayar["sabitlenen"])
ikon = int(ayar["iconSize"]); bosluk = 10; yan = 16
panel = ikon * len(sec) + bosluk * max(0, len(sec) - 1) + 2 * yan
sol = (1440 - panel) // 2
x = sol + yan + 2 * (ikon + bosluk) + ikon // 2
# panel ekran altindan 10 px yukarida, ikon panel icinde 10 px altta
y = 900 - 12 - 12 - ikon // 2
print(x, y)
PY
)

trap durdur EXIT

# --- 01-03: sabit panel -----------------------------------------------------
basla
DISPLAY="$DISPLAY" xdotool mousemove 720 300
sleep 0.6
DISPLAY="$DISPLAY" import -window root kanit/01-bos.png

DISPLAY="$DISPLAY" xdotool mousemove "$IX" "$IY"
sleep 0.6
DISPLAY="$DISPLAY" import -window root kanit/02-hover.png

DISPLAY="$DISPLAY" xdotool click 1
sleep 1.2
DISPLAY="$DISPLAY" import -window root kanit/03-tiklama.png

# --- 04-05: otomatik gizlenme ----------------------------------------------
durdur
cfg autoHide true
basla
DISPLAY="$DISPLAY" xdotool mousemove 720 300
sleep 1.6
DISPLAY="$DISPLAY" import -window root kanit/04-gizli.png

DISPLAY="$DISPLAY" xdotool mousemove 720 899
sleep 0.6
DISPLAY="$DISPLAY" import -window root kanit/05-acik.png

# --- 06 + olcum: 60 saniye bosta -------------------------------------------
durdur
cfg autoHide false
basla
DISPLAY="$DISPLAY" xdotool mousemove 720 300
PID="$(cat /tmp/dock-test.pid)"
sleep 60
DISPLAY="$DISPLAY" import -window root kanit/06-60s.png
{
    echo "pid=$PID"
    ps -o pid,%cpu,rss,etime,cmd -p "$PID"
} > kanit/olcum.txt

durdur
echo "Kanitlar hazir: $(ls kanit/*.png | tr '\n' ' ')"
cat kanit/olcum.txt
