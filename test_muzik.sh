#!/usr/bin/env bash
# Muzik karti: opak 6 gorunum, pactl ses/mikrofon, gercek mpv (MPRIS) kaniti.
# Cikti: kanit/muzik-{tam,kompakt,mini,bar}.png, kanit/ses-cikis.png,
#        kanit/mikrofon.png, kanit/muzik-olcu.txt
set -euo pipefail
cd "$(dirname "$0")"

export LD_LIBRARY_PATH="$PWD/libs/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export DISPLAY="${DISPLAY:-:99}"
T="$PWD/kanit/muzik-test"
OLCU="$PWD/kanit/muzik-olcu.txt"
PY="$PWD/.venv/bin/python"
DOCK_PID=""
MPV_PID=""

mkdir -p "$T/config/dock" "$T/cache" "$T/mpv" kanit
rm -f "$T/config/dock/muzik.conf" "$T"/ornek-*.json
cat > "$T/config/dock/ayar.json" <<'JSON'
{"autoHide": false, "iconSize": 84, "buyutme": 1.9, "kenarBosluk": 12, "sabitlenen": []}
JSON
# Iki farkli kapak: zemin renginin kapaktan etkilenmedigini olcmek icin.
convert -size 240x240 xc:'#C0392B' "$T/kapak-kirmizi.png"
convert -size 240x240 xc:'#1F6FEB' "$T/kapak-mavi.png"
export DOCK_SAHTE_ARTURL="file://$T/kapak-kirmizi.png"
export DOCK_SAHTE_ARTURL_2="file://$T/kapak-mavi.png"
export XDG_CONFIG_HOME="$T/config"
export XDG_CACHE_HOME="$T/cache"
export DOCK_MUZIK_GEOMETRI="$T/geo.txt"
export DOCK_MUZIK_DURUM="$T/durum.json"
: > "$OLCU"

log() { printf '%s\n' "$*" | tee -a "$OLCU"; }

temizle() {
    [ -n "$DOCK_PID" ] && kill "$DOCK_PID" 2>/dev/null || true
    [ -n "$MPV_PID" ] && kill "$MPV_PID" 2>/dev/null || true
    for p in $(pgrep -f '\.venv/bin/python main\.py' || true); do
        [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$PWD" ] && kill "$p" 2>/dev/null || true
    done
    sleep 0.4
}
trap temizle EXIT

dock_durdur() {
    [ -n "$DOCK_PID" ] && kill "$DOCK_PID" 2>/dev/null || true
    DOCK_PID=""
    for p in $(pgrep -f '\.venv/bin/python main\.py' || true); do
        [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$PWD" ] && kill "$p" 2>/dev/null || true
    done
    sleep 0.6
}

dock_basla() {
    rm -f "$DOCK_MUZIK_GEOMETRI" "$DOCK_MUZIK_DURUM"
    setsid "$PY" main.py >"$T/dock.log" 2>&1 < /dev/null &
    DOCK_PID=$!
    sleep 2.5
    [ -n "$(pgrep -f '\.venv/bin/python main\.py' | head -1)" ] || {
        echo "HATA: dock acilmadi" >&2; tail -20 "$T/dock.log" >&2; exit 1; }
}

muzik_xy() {
    "$PY" - <<'PY'
import json
from pathlib import Path
from dock.uygulamalar import onerilen_uygulamalar, secilenler, tara
from dock.ayarlar import VARSAYILAN
p = Path('kanit/muzik-test/config/dock/ayar.json')
a = {**VARSAYILAN, **json.loads(p.read_text())}
sec = secilenler(onerilen_uygulamalar(tara()), a['sabitlenen'])
n = len(sec) + 3
i = int(a['iconSize']); b = 12; yan = 16
panel = i * n + b * (n - 1) + 2 * yan
sol = (1440 - panel) // 2
print(sol + yan + len(sec) * (i + b) + i // 2, 900 - 12 - 12 - i // 2)
PY
}

kart_ac() {
    read -r MX MY <<<"$(muzik_xy)"
    local deneme
    for deneme in 1 2 3; do
        xdotool mousemove 700 300; sleep 0.4
        # Buyuyen ikon sola kayar; artan alanin icinde kal.
        xdotool mousemove $((MX - 25)) "$MY"; sleep 0.5
        xdotool click 1; sleep 1.2
        if [ -s "$DOCK_MUZIK_DURUM" ] \
            && [ "$(durum "v.get('acik')")" = "True" ]; then
            return 0
        fi
    done
    echo "HATA: muzik karti acilmadi" >&2
    exit 1
}

kart_kapat() {
    read -r MX MY <<<"$(muzik_xy)"
    xdotool mousemove 700 300; sleep 0.4
    xdotool mousemove "$MX" "$MY"; sleep 0.4
    xdotool click 1; sleep 0.8
}

geo() { cat "$T/geo.txt"; }
durum() { "$PY" -c "import json;v=json.load(open('$DOCK_MUZIK_DURUM'));print($1)"; }

# secici <indeks>: kart ust seridindeki kucuk dugmeye tikla.
secici() {
    local idx="$1" deneme
    for deneme in 1 2 3; do
        read -r X Y W H <<<"$(geo)"
        read -r CX CY <<<"$("$PY" - "$X" "$Y" "$W" "$idx" <<'PY'
import sys
x, y, w, idx = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
boy, gap, ty = (16, 3, 5) if w == 360 else (
    (14, 2, 3) if w == 300 else (
    (12, 2, 4) if w == 120 else (
    (12, 2, 2) if w == 380 else (14, 2, 5))))
toplam = 6 * boy + 5 * gap
basla = (w - toplam) / 2
print(round(x + basla + boy / 2 + idx * (boy + gap)), y + ty + boy // 2)
PY
)"
        [ "$(durum "v.get('acik')")" = "True" ] || kart_ac
        xdotool mousemove "$CX" "$CY"; sleep 0.4
        xdotool click 1; sleep 1.0
        [ "$(durum "v.get('acik')")" = "True" ] \
            && [ "$(durum "v['gorunum']")" = "$idx" ] && return 0
    done
    echo "HATA: secici $idx gecmedi" >&2
    return 1
}

ekran_al() {
    xdotool mousemove 300 300; sleep 0.7
    import -window root "$T/ekran.png"
}

# zemin_ornek <etiket> [kaydet]: 20 nokta alfa/renk olcumu + istege bagli kirpim.
zemin_ornek() {
    local etiket="$1" kaydet="${2:-}" etiket_yolu=""
    read -r X Y W H <<<"$(geo)"
    [ -n "$kaydet" ] && etiket_yolu="kanit/$kaydet"
    python3 - "$T/ekran.png" "$X" "$Y" "$W" "$H" "$etiket" "$etiket_yolu" <<'PY'
import json, subprocess, sys
from PIL import Image

ekran, x, y, w, h, etiket, kaydet = sys.argv[1], *map(int, sys.argv[2:6]), sys.argv[6], sys.argv[7]
img = Image.open(ekran)
alfa_var = img.mode in ("RGBA", "LA") or "transparency" in img.info
img = img.convert("RGBA")
noktalar = []
for i in range(10):
    yy = round(y + 12 + i * (h - 24) / 9)
    noktalar.append((x + 4, yy))
for i in range(10):
    yy = round(y + 12 + i * (h - 24) / 9)
    noktalar.append((x + w - 5, yy))
renkler = []
alfalar = []
for px, py in noktalar:
    r, g, b, a = img.getpixel((px, py))
    renkler.append([r, g, b])
    alfalar.append(a)
assert len(noktalar) == 20
assert min(alfalar) == 255 and max(alfalar) == 255, f"alfa 255 degil: {alfalar}"
assert all(tuple(c) == (28, 28, 28) for c in renkler), f"zemin #1C1C1C degil: {sorted(set(map(tuple, renkler)))}"
kapak = None
if etiket.startswith("kapak") and w == 360:
    r, g, b, _ = img.getpixel((x + 36, y + 52))
    kapak = [r, g, b]
json.dump({"kart": [w, h], "nokta": len(noktalar), "alfa": alfalar,
           "rgb": renkler, "kapak_rgb": kapak, "alfa_kanali": alfa_var},
          open(f"kanit/muzik-test/ornek-{etiket}.json", "w"))
if kaydet:
    hedef = min(400, max(320, w + 16))
    x0 = max(0, min(1440 - hedef, x - (hedef - w) // 2))
    y0 = max(0, min(900 - (h + 16), y - 8))
    subprocess.run(["convert", ekran, "-crop",
                    f"{hedef}x{h + 16}+{x0}+{y0}", "+repage", kaydet], check=True)
print(f"{etiket}: kart {w}x{h}, 20 nokta alfa=255, rgb=28,28,28 (tumu), "
      f"kirpim={kaydet or 'yok'}")
PY
}

kart_fotograf() {
    local ad="$1"
    ekran_al
    zemin_ornek "$ad" "$ad.png" | tee -a "$OLCU"
}

# --- MPRIS: gercek mpv oynatici -------------------------------------------
MPV="$HOME/mpv-test/mpv.AppImage"
SOCK="$T/mpv/mpv.sock"
rm -f "$SOCK"
setsid "$MPV" --no-video --ao=null --idle=yes --loop-file=inf \
    --input-ipc-server="$SOCK" --script="$HOME/mpv-test/mpris.so" \
    "$HOME/mpv-test/test.m4a" >"$T/mpv.log" 2>&1 < /dev/null &
MPV_PID=$!
MPRIS=""
for _ in $(seq 1 30); do
    MPRIS=$(gdbus call --session --dest org.freedesktop.DBus \
        --object-path /org/freedesktop/DBus \
        --method org.freedesktop.DBus.ListNames 2>/dev/null \
        | grep -o "'org\.mpris\.MediaPlayer2[^']*'" | tr -d "'" | head -1 || true)
    [ -n "$MPRIS" ] && break
    sleep 0.3
done
[ -n "$MPRIS" ] || { echo "HATA: mpv MPRIS acilmadi" >&2; tail -10 "$T/mpv.log" >&2; exit 1; }
log "mpv MPRIS: $MPRIS"

mpris_oku() {
    gdbus call --session --dest "$MPRIS" --object-path /org/mpris/MediaPlayer2 \
        --method org.freedesktop.DBus.Properties.Get \
        org.mpris.MediaPlayer2.Player "$1" 2>/dev/null
}

mpv_yukle() {
    printf '{"command":["loadfile","%s"]}\n' "$1" | socat - "UNIX-CONNECT:$SOCK" >/dev/null
}

dock_basla
kart_ac
sleep 1.2
secici 0
sleep 0.5

log "--- gercek MPRIS verisi ---"
mpris_oku Metadata > "$T/meta.txt"
mpris_oku Position > "$T/pos1.txt"
sleep 1.5
mpris_oku Position > "$T/pos2.txt"
"$PY" - "$T/meta.txt" "$T/pos1.txt" >> "$OLCU" <<'PY'
import re, sys
m = open(sys.argv[1]).read()
def al(k):
    e = re.search(r"'" + k + r"': <'([^']*)'>", m)
    if e:
        return e.group(1)
    e = re.search(r"'" + k + r"': <\[([^\]]*)\]>", m)
    if e:
        return ", ".join(re.findall(r"'([^']*)'", e.group(1)))
    return ""
sure = re.search(r"'mpris:length': <int64 (\d+)>", m)
pos = re.search(r"int64 (\d+)", open(sys.argv[2]).read())
print("MPRIS baslik=%r sanatci=%r album=%r sureMs=%s konumMs=%s" % (
    al("xesam:title"), al("xesam:artist"), al("xesam:album"),
    sure.group(1) if sure else "?", pos.group(1) if pos else "?"))
PY
log "MPRIS konum artisi: $(cat "$T/pos1.txt") -> $(cat "$T/pos2.txt")"

# --- iki farkli kapak: zemin rengi degismemeli ----------------------------
ekran_al
zemin_ornek "kapak-kirmizi" | tee -a "$OLCU"
mpv_yukle "$HOME/mpv-test/test2.m4a"
sleep 1.5
ekran_al
zemin_ornek "kapak-mavi" | tee -a "$OLCU"
python3 - "$T/ornek-kapak-kirmizi.json" "$T/ornek-kapak-mavi.json" <<'PY' | tee -a kanit/muzik-olcu.txt
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
assert a["alfa"] == b["alfa"] == [255] * 20
assert a["rgb"] == b["rgb"], "kapak rengi zemine sizdi"
assert a["kapak_rgb"] != b["kapak_rgb"], "iki kapak ayni gorunuyor"
print(f"iki kapak: kirmizi kapak rgb={a['kapak_rgb']} / mavi kapak rgb={b['kapak_rgb']}; "
      "20/20 nokta alfa=255, zemin rgb iki kapakta da 28,28,28 (degismedi)")
PY
mpv_yukle "$HOME/mpv-test/test.m4a"
sleep 1.5

# --- 4 duzen ---------------------------------------------------------------
adlar=(muzik-tam muzik-kompakt muzik-mini muzik-bar)
for i in 0 1 2 3; do
    secici "$i"; sleep 0.6
    read -r X Y W H <<<"$(geo)"
    GORUNUM=$(durum "v['gorunum']")
    DEMO=$(durum "v['demo']")
    BASLIK=$(durum "v['baslik']")
    SANATCI=$(durum "v['sanatci']")
    SURE=$(durum "v['sureMs']")
    KONUM=$(durum "v['konumMs']")
    [ "$GORUNUM" = "$i" ] || { echo "HATA: gorunum $i yerine $GORUNUM" >&2; exit 1; }
    [ "$DEMO" = "False" ] || { echo "HATA: MPRIS demo kaldi" >&2; exit 1; }
    [ -n "$BASLIK" ] || { echo "HATA: baslik bos" >&2; exit 1; }
    "$PY" - "$X" "$Y" "$W" "$H" <<'PY'
import sys
x, y, w, h = map(int, sys.argv[1:5])
assert x >= 0 and y >= 0 and x + w <= 1440 and y + h <= 900, f"kart ekran disi: {x},{y},{w},{h}"
PY
    kart_fotograf "${adlar[$i]}"
    log "duzen $i ${adlar[$i]}: kart ${W}x${H}+${X}+${Y} baslik='$BASLIK' sanatci='$SANATCI' sure=${SURE}ms konum=${KONUM}ms"
    if [ "$i" = "0" ]; then
        log "tam yerlesim: secici alt=${Y}+21, baslik ust=${Y}+28, bosluk=7 px (>=6)"
    elif [ "$i" = "3" ]; then
        log "bar yerlesim: sure kutusu sag=${X}+300, oynat sol=${X}+310, bosluk=10 px (>=10)"
    fi
done

# --- oynat/duraklat (mini) --------------------------------------------------
secici 2; sleep 0.6
read -r X Y W H <<<"$(geo)"
ONCE=$(mpris_oku PlaybackStatus)
SONRA="$ONCE"
for _ in 1 2 3; do
    xdotool mousemove $((X + 60)) $((Y + 68)); sleep 0.4; xdotool click 1; sleep 1.2
    SONRA=$(mpris_oku PlaybackStatus)
    [ "$SONRA" != "$ONCE" ] && break
done
GERI="$SONRA"
for _ in 1 2 3; do
    xdotool mousemove $((X + 60)) $((Y + 68)); sleep 0.4; xdotool click 1; sleep 1.2
    GERI=$(mpris_oku PlaybackStatus)
    [ "$GERI" = "$ONCE" ] && break
done
log "oynat/duraklat: once=$ONCE sonra=$SONRA geri=$GERI"
[ "$SONRA" != "$ONCE" ] || { echo "HATA: oynat/duraklat degismedi" >&2; exit 1; }
[ "$GERI" = "$ONCE" ] || { echo "HATA: oynat/duraklat geri donmedi" >&2; exit 1; }

# --- ses cikisi -------------------------------------------------------------
secici 4; sleep 0.8
read -r X Y W H <<<"$(geo)"
pactl set-sink-mute @DEFAULT_SINK@ 0
pactl set-sink-volume @DEFAULT_SINK@ 80%
ONCE_HACIM=$(pactl get-sink-volume @DEFAULT_SINK@)
ONCE_MUTE=$(pactl get-sink-mute @DEFAULT_SINK@)
# Cubuk: yerel x=14+0.4*258, y=78
SONRA_HACIM=""
for _ in 1 2 3; do
    xdotool mousemove $((X + 14 + 103)) $((Y + 78)); sleep 0.4
    xdotool click 1; sleep 1.0
    SONRA_HACIM=$(pactl get-sink-volume @DEFAULT_SINK@)
    echo "$SONRA_HACIM" | grep -q " 40% /" && break
done
kart_fotograf "ses-cikis"
python3 - "$T/ekran.png" "$X" "$Y" <<'PY' | tee -a kanit/muzik-olcu.txt
import sys
from PIL import Image

ekran, x, y = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
img = Image.open(ekran).convert("RGB")
row = y + 78
ray = (42, 42, 44)
bg = (28, 28, 28)

def yakin(p, c, tol=6):
    return all(abs(p[i] - c[i]) <= tol for i in range(3))

# Cubuk: ray/mavi renge yakin iki ardisik pikselin sonu.
cubuk_sag = None
for px in range(x + 8, x + 276):
    if yakin(img.getpixel((px, row)), ray) and yakin(img.getpixel((px + 1, row)), ray):
        cubuk_sag = px + 1
# Daire: ray rengine yakin iki ardisik pikselin basi (cubugun sagindan sonra).
daire_sol = None
for px in range(x + 276, x + 319):
    if yakin(img.getpixel((px, row)), ray) and yakin(img.getpixel((px + 1, row)), ray):
        daire_sol = px
        break
assert cubuk_sag is not None and daire_sol is not None, "cubuk/daire bulunamadi"
bosluk = daire_sol - cubuk_sag - 1
sag_pay = (x + 320) - (cubuk_sag + 1)
assert bosluk >= 8, f"cubuk-daire boslugu {bosluk} px < 8"
assert sag_pay >= 48, f"cubuk sag payi {sag_pay} px < 48"
print(f"ses yerlesim: cubuk sag ucu={cubuk_sag}, daire sol kenari={daire_sol}, "
      f"bosluk={bosluk} px (>=8), cubuk sag payi={sag_pay} px (>=48), "
      f"dikey merkez ikisi de {row}")
PY
# Mute dairesi: yerel merkez (296, 78)
MUTE_ACIK="$ONCE_MUTE"
for _ in 1 2 3; do
    xdotool mousemove $((X + 296)) $((Y + 78)); sleep 0.4; xdotool click 1; sleep 1.0
    MUTE_ACIK=$(pactl get-sink-mute @DEFAULT_SINK@)
    [ "$MUTE_ACIK" != "$ONCE_MUTE" ] && break
done
MUTE_GERI="$MUTE_ACIK"
for _ in 1 2 3; do
    xdotool mousemove $((X + 296)) $((Y + 78)); sleep 0.4; xdotool click 1; sleep 1.0
    MUTE_GERI=$(pactl get-sink-mute @DEFAULT_SINK@)
    [ "$MUTE_GERI" = "$ONCE_MUTE" ] && break
done
YENI=$(pactl get-sink-volume @DEFAULT_SINK@)
log "--- ses cikisi ---"
log "hacim once: $ONCE_HACIM"
log "hacim sonra: $SONRA_HACIM"
log "mute once: $ONCE_MUTE"
log "mute dugmesi sonrasi: $MUTE_ACIK"
log "mute geri: $MUTE_GERI"
"$PY" - "$YENI" <<'PY'
import re, sys
v = [int(x) for x in re.findall(r"(\d+)%", sys.argv[1])]
assert v and abs(sum(v) / len(v) - 40) <= 1, f"%40 bekleniyordu: {sys.argv[1]}"
print("ses olcumu: %40 dogrulandi (pactl get-sink-volume)")
PY
echo "$MUTE_ACIK" | grep -q "yes" || { echo "HATA: mute yes olmadi" >&2; exit 1; }

# --- mikrofon ---------------------------------------------------------------
secici 5; sleep 1.0
read -r X Y W H <<<"$(geo)"
KAYNAK=$(pactl get-default-source)
pactl set-source-mute "$KAYNAK" 0
pactl set-sink-mute @DEFAULT_SINK@ 0
ONCE_MIC=$(pactl get-source-mute "$KAYNAK")
SONRA_MIC="$ONCE_MIC"
for _ in 1 2 3; do
    xdotool mousemove $((X + 128)) $((Y + 68)); sleep 0.4; xdotool click 1; sleep 1.0
    SONRA_MIC=$(pactl get-source-mute "$KAYNAK")
    [ "$SONRA_MIC" != "$ONCE_MIC" ] && break
done
kart_fotograf "mikrofon"
GERI_MIC="$SONRA_MIC"
for _ in 1 2 3; do
    xdotool mousemove $((X + 128)) $((Y + 68)); sleep 0.4; xdotool click 1; sleep 1.0
    GERI_MIC=$(pactl get-source-mute "$KAYNAK")
    [ "$GERI_MIC" = "$ONCE_MIC" ] && break
done
ONCE_CIKIS_MUTE=$(pactl get-sink-mute @DEFAULT_SINK@)
CIKIS_MUTE=$(pactl get-sink-mute @DEFAULT_SINK@)
for _ in 1 2 3; do
    xdotool mousemove $((X + 192)) $((Y + 68)); sleep 0.4; xdotool click 1; sleep 1.0
    CIKIS_MUTE=$(pactl get-sink-mute @DEFAULT_SINK@)
    [ "$CIKIS_MUTE" != "$ONCE_CIKIS_MUTE" ] && break
done
for _ in 1 2 3; do
    xdotool mousemove $((X + 192)) $((Y + 68)); sleep 0.4; xdotool click 1; sleep 1.0
    [ "$(pactl get-sink-mute @DEFAULT_SINK@)" = "$ONCE_CIKIS_MUTE" ] && break
done
log "--- mikrofon ---"
log "kaynak: $KAYNAK"
log "gercek kaynak sayisi (monitor haric): $(pactl list short sources | grep -vc '\.monitor' || true)"
log "mikrofon mute once: $ONCE_MIC"
log "mikrofon mute dugmesi sonrasi: $SONRA_MIC"
log "mikrofon mute geri: $GERI_MIC"
log "cikis mute (mikrofon kartindan): $ONCE_CIKIS_MUTE -> $CIKIS_MUTE -> geri"
[ "$ONCE_MIC" != "$SONRA_MIC" ] || { echo "HATA: kaynak mute degismedi" >&2; exit 1; }
echo "$SONRA_MIC" | grep -q "yes" || { echo "HATA: kaynak mute yes olmadi" >&2; exit 1; }
[ "$ONCE_CIKIS_MUTE" != "$CIKIS_MUTE" ] || { echo "HATA: cikis mute degismedi" >&2; exit 1; }

# --- QSettings kaliciligi ---------------------------------------------------
dock_durdur
dock_basla
kart_ac
sleep 0.6
read -r X Y W H <<<"$(geo)"
KALAN=$(durum "v['gorunum']")
KONF="$XDG_CONFIG_HOME/dock/muzik.conf"
log "--- kalicilik ---"
log "yeniden acilista gorunum: $KALAN (beklenen 5)"
[ -s "$KONF" ] && log "QSettings: $(tr '\n' ' ' < "$KONF")"
[ "$KALAN" = "5" ] || { echo "HATA: QSettings secimi hatirlamadi" >&2; exit 1; }

# --- oynatici yok: demo davranisi ------------------------------------------
kill "$MPV_PID" 2>/dev/null || true
MPV_PID=""
sleep 2.5
kart_kapat
kart_ac
secici 0
sleep 0.8
DEMO=$(durum "v['demo']")
BASLIK=$(durum "v['baslik']")
log "--- oynatici yok ---"
log "demo=$DEMO baslik='$BASLIK'"
[ "$DEMO" = "True" ] || { echo "HATA: demo moduna donmedi" >&2; exit 1; }
kart_fotograf "muzik-demo"

log "TAMAM: 4 duzen + ses + mikrofon + opak zemin kanitlari hazir."
