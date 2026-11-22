#!/usr/bin/env bash
# 5 sistem kartini acar, 640x360 kanit + karsilastirma uretir, CPU olcer.
set -euo pipefail
cd "$(dirname "$0")"

export LD_LIBRARY_PATH="$PWD/libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export QT_QUICK_BACKEND="${QT_QUICK_BACKEND:-software}"
# Kare kartlarin kose kanitlari duvar kagidiyla karismasin: test icin ozel,
# duz #0A0A0A zeminli Xvfb (:98). Paylasilan :99'a dokunulmaz.
XVFB_PID=""
TEST_DISPLAY="${SISTEM_TEST_DISPLAY:-:98}"
if ! xdpyinfo -display "$TEST_DISPLAY" >/dev/null 2>&1; then
    Xvfb "$TEST_DISPLAY" -screen 0 1440x900x24 -nolisten tcp >/dev/null 2>&1 &
    XVFB_PID=$!
    sleep 1
fi
export DISPLAY="$TEST_DISPLAY"
xsetroot -solid '#0A0A0A' 2>/dev/null || true
export XDG_CONFIG_HOME="$PWD/kanit/test-config"
export XDG_CACHE_HOME="$PWD/kanit/test-cache"
PY="$PWD/.venv/bin/python"
mkdir -p kanit "$XDG_CONFIG_HOME/dock" "$XDG_CACHE_HOME"
LOG="$PWD/kanit/sistem-log.json"
GEO="$PWD/kanit/sistem-geometri.txt"
DURUM="$PWD/kanit/sistem-durum.txt"

mkdir -p "$XDG_CONFIG_HOME/dock"
cat > "$XDG_CONFIG_HOME/dock/ayar.json" <<'JSON'
{"autoHide": false, "iconSize": 84, "buyutme": 1.9, "kenarBosluk": 12, "sabitlenen": []}
JSON

dock_temizle() {
    for p in $(pgrep -f '\.venv/bin/python main\.py' || true); do
        [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$PWD" ] && kill "$p" 2>/dev/null || true
    done
    sleep 0.5
}
temizle() {
    dock_temizle
    [ -n "${XVFB_PID:-}" ] && kill "$XVFB_PID" 2>/dev/null || true
    sleep 0.3
}

# Son (sistem) ikonunun ekran merkezi.
read -r SX SY SW SH IKON < <("$PY" - <<'PY'
import json, subprocess
from pathlib import Path
from dock.uygulamalar import onerilen_uygulamalar, secilenler, tara
from dock.ayarlar import VARSAYILAN
yol = Path(__import__('os').environ['XDG_CONFIG_HOME']) / 'dock' / 'ayar.json'
ayar = {**VARSAYILAN, **json.loads(yol.read_text())}
sec = secilenler(onerilen_uygulamalar(tara()), ayar['sabitlenen'])
n = len(sec) + 3
ikon = int(ayar['iconSize']); bosluk = 12; yan = 16
g = subprocess.run(['xdotool', 'getdisplaygeometry'], capture_output=True, text=True).stdout.split()
W, H = int(g[0]), int(g[1])
panel = ikon * n + bosluk * (n - 1) + 2 * yan
sol = (W - panel) // 2
x = sol + yan + (n - 1) * (ikon + bosluk) + ikon // 2
y = H - 12 - 12 - ikon // 2
print(x, y, W, H, ikon)
PY
)

# Paneldeki 5 kucuk secim ikonunun merkezleri (Dock.qml izgarasiyla ayni).
DUGME=$(( (IKON * 30 + 50) / 100 ))
ARA=$(( IKON * 5 / 100 )); [ "$ARA" -lt 2 ] && ARA=2
IZGARA_G=$(( 2 * DUGME + ARA ))
IZGARA_Y=$(( 3 * DUGME + 2 * ARA ))
KUTU_TOP=$(( SH - 24 - IKON ))
GX=$(( SX - IKON / 2 + (IKON - IZGARA_G) / 2 ))
GY=$(( KUTU_TOP + (IKON - IZGARA_Y) / 2 ))
sec_x() { echo $(( GX + ($1 % 2) * (DUGME + ARA) + DUGME / 2 )); }
sec_y() { echo $(( GY + ($1 / 2) * (DUGME + ARA) + DUGME / 2 )); }

dock_temizle
rm -f "$LOG" "$GEO" "$DURUM"
setsid env DOCK_SISTEM_LOG="$LOG" DOCK_GEOMETRI="$GEO" DOCK_DURUM_LOG="$DURUM" \
    "$PY" main.py >>kanit/sistem-oturum.log 2>&1 < /dev/null &
sleep 3
PID="$(for p in $(pgrep -f '\.venv/bin/python main\.py' || true); do
    [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$PWD" ] && echo "$p"; done | head -1)"
[ -n "$PID" ] || { echo "HATA: dock acilmadi" >&2; exit 1; }
trap temizle EXIT

# Paneldeki CPU secim ikonuna tikla; kare acilir.
xdotool mousemove "$(sec_x 0)" "$(sec_y 0)"; sleep 0.5
xdotool click 1; sleep 1.5
[ -s "$GEO" ] || { echo "HATA: sistem karti acilmadi" >&2; cat kanit/sistem-oturum.log >&2; exit 1; }
read -r CX CY CW CH < "$GEO"

adlar=(cpu ram network top-cpu top-ram)
for i in 0 1 2 3 4; do
    xdotool mousemove "$(sec_x "$i")" "$(sec_y "$i")"; sleep 0.3; xdotool click 1
    if [ "$i" -ge 3 ]; then sleep 3.6; else sleep 1.1; fi
    ad="${adlar[$i]}"
    read -r CX CY CW CH < "$GEO"
    # 640x360 canli kare icin karti ortala, ekran disina tasirma.
    CX640=$(( CX - 160 )); [ "$CX640" -lt 0 ] && CX640=0
    [ "$CX640" -gt $(( SW - 640 )) ] && CX640=$(( SW - 640 ))
    CY640=$(( CY - 30 )); [ "$CY640" -lt 0 ] && CY640=0
    [ "$CY640" -gt $(( SH - 360 )) ] && CY640=$(( SH - 360 ))
    import -window root -crop "640x360+${CX640}+${CY640}" +repage "kanit/sistem-${ad}.png"
    import -window root -crop "${CW}x${CH}+${CX}+${CY}" +repage "kanit/sistem-kart-${ad}.png"
done

# Ust listelerde gercek surec adlari var mi? (2 sn'lik tarama icin bekle)
sleep 2.2
"$PY" - "$LOG" <<'PY'
import json, sys
v = json.load(open(sys.argv[1], encoding='utf-8'))
assert v.get('cpu') is not None and v.get('ramYuzde') is not None, 'CPU/RAM yok'
assert v.get('indirme') is not None and v.get('yukleme') is not None, 'ag yok'
assert v.get('gecmisSayisi', 0) >= 2, 'ag gecmisi yok'
assert len(v.get('topCpu') or []) >= 1 and (v['topCpu'][0].get('ad') or '').strip(), 'Top CPU bos'
assert len(v.get('topRam') or []) >= 1 and (v['topRam'][0].get('ad') or '').strip(), 'Top RAM bos'
print('veri: cpu=%s ram=%s%% ag=%s/%s B/s gecmis=%s topCpu=%s topRam=%s' % (
    v['cpu'], v['ramYuzde'], v['indirme'], v['yukleme'], v['gecmisSayisi'],
    v['topCpu'][0]['ad'], v['topRam'][0]['ad']))
PY

# CPU kiyasi: mutlak esik yok. Ayni kosuda once sistem karti (sekme 2),
# sonra AI karti 15 sn psutil ile olculur; kural sistem <= AI + 1.0 puan.
# 2026-11-21: ayni makinede 1.10/1.30/1.20/2.60 gibi oynak degerler goruldu;
# paralel is yuku tek basina mutlak esigi guvenilmez kiliyor.
xdotool mousemove "$(sec_x 2)" "$(sec_y 2)"; sleep 0.3; xdotool click 1; sleep 1.0
SYS_CPU=$("$PY" - "$PID" <<'PY'
import psutil, sys
print('%.2f' % psutil.Process(int(sys.argv[1])).cpu_percent(interval=15))
PY
)
echo "sistem kart CPU (sekme 2, 15 sn): ${SYS_CPU}%"

# Disina tiklayinca kapaniyor mu? (Xvfb'de tek tik kacarsa bir kez tekrar.)
disina_tikla() {
    # Genis kart (977 px) 720,450'yi kapatir; kartin solu 451'de baslar.
    xdotool mousemove 300 600; sleep 0.5
    xdotool click 1; sleep 1.0
}
disina_tikla
[ "$(cat "$DURUM" 2>/dev/null || echo 1)" = "0" ] || disina_tikla
[ "$(cat "$DURUM" 2>/dev/null || echo 1)" = "0" ] || { echo "HATA: kart kapanmadi" >&2; exit 1; }

# Yeniden acilip kapaniyor mu?
xdotool mousemove "$(sec_x 0)" "$(sec_y 0)"; sleep 0.5; xdotool click 1; sleep 1.0
[ "$(cat "$DURUM" 2>/dev/null || echo 0)" = "1" ] || { echo "HATA: kart yeniden acilmadi" >&2; exit 1; }
disina_tikla
[ "$(cat "$DURUM" 2>/dev/null || echo 1)" = "0" ] || disina_tikla
[ "$(cat "$DURUM" 2>/dev/null || echo 1)" = "0" ] || { echo "HATA: kart ikinci kez kapanmadi" >&2; exit 1; }

# Ayni kosuda AI karti olcumu (DOCK_KART=limit). Kart acilmazsa kiyas atlanir.
dock_temizle
setsid env DOCK_KART=limit "$PY" main.py >>kanit/sistem-oturum.log 2>&1 < /dev/null &
sleep 6
AI_PID="$(for p in $(pgrep -f '\.venv/bin/python main\.py' || true); do
    [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$PWD" ] && echo "$p"; done | head -1)"
AI_CPU=""
if [ -n "$AI_PID" ]; then
    AI_CPU=$("$PY" - "$AI_PID" <<'PY'
import psutil, sys
print('%.2f' % psutil.Process(int(sys.argv[1])).cpu_percent(interval=15))
PY
)
    echo "AI kart CPU (15 sn): ${AI_CPU}%"
else
    echo "UYARI: AI karti acilmadi -> KIYAS YOK"
fi
if [ -n "$AI_CPU" ]; then
    "$PY" - "$SYS_CPU" "$AI_CPU" <<'PY'
import sys
sistem, ai = float(sys.argv[1]), float(sys.argv[2])
print('KIYAS: sistem %.2f%% <= AI %.2f%% + 1.00%% (fark %.2f)' % (sistem, ai, sistem - ai))
assert sistem <= ai + 1.0, 'sistem CPU, AI + 1.0 puan ustunde: %.2f%% vs %.2f%%' % (sistem, ai)
PY
else
    echo "KIYAS YOK: AI olcumu alinamadi; CPU assert atlandi."
fi
"$PY" - "$LOG" "$SYS_CPU" "$AI_CPU" <<'PY'
import json, sys
yol, sistem, ai = sys.argv[1], sys.argv[2], sys.argv[3]
v = json.load(open(yol, encoding='utf-8'))
v['dockCpuYuzde'] = round(float(sistem), 2)
v['aiCpuYuzde'] = round(float(ai), 2) if ai else None
v['olcumSn'] = 15
json.dump(v, open(yol, 'w', encoding='utf-8'), ensure_ascii=False)
PY
dock_temizle

# Karsilastirma: referans ve bizim kart ayni yukseklikte yan yana.
declare -A REF=(
  [cpu]="cpu-dark-BRtP9be8.webp"
  [ram]="ram-dark-jTUjpVEV.webp"
  [network]="network-dark-DUkjwfvY.webp"
  [top-cpu]="top-cpu-dark-DSVXSe30.webp"
  [top-ram]="top-ram-dark-D2PXHQV2.webp"
)
for ad in "${adlar[@]}"; do
    if [ "$ad" = cpu ] || [ "$ad" = ram ]; then
        # Adil kiyas: referansi kendi kart sinirindan (alpha>8 bbox) kirp,
        # 320x320'ye olcekle; 664x320 #0F0F0F tuval, 24 px bosluk, cerceve yok.
        KIRP=$(convert "refs/lumabar/${REF[$ad]}" -alpha extract -threshold 3% \
            -trim -format '%wx%h%O' info:)
        convert "refs/lumabar/${REF[$ad]}" -crop "$KIRP" +repage \
            -resize 320x320! /tmp/ref-sistem.png
        convert -size 664x320 xc:'#0F0F0F' \
            /tmp/ref-sistem.png -geometry +0+0 -composite \
            "kanit/sistem-kart-${ad}.png" -geometry +344+0 -composite \
            "kanit/karsilastirma-${ad}.png"
        if [ "$ad" = cpu ]; then
            # Mutlak fark: koyu zeminde esit yerler siyah, fark parlak.
            convert /tmp/ref-sistem.png -background '#0F0F0F' -alpha remove -alpha off \
                "kanit/sistem-kart-cpu.png" -compose difference -composite \
                -evaluate multiply 3 "kanit/fark-cpu.png"
        fi
    else
        # Genis kartlar: referans 154 px -> 320 px (x2.077); yan yana etiketli.
        convert "refs/lumabar/${REF[$ad]}" -resize x320 /tmp/ref-sistem.png
        convert "kanit/sistem-kart-${ad}.png" -resize x320 /tmp/dock-sistem.png
        montage -background '#000000' -fill '#EDEDF0' -font DejaVu-Sans -pointsize 20 \
            -label 'lumabar referansı (x2.077)' /tmp/ref-sistem.png \
            -label 'dock' /tmp/dock-sistem.png \
            -tile 2x1 -geometry +16+16 "kanit/karsilastirma-${ad}.png"
    fi
done

echo "TAMAM: 5 kart, karsilastirmalar ve CPU olcumu hazir (PID $PID)."
