#!/usr/bin/env python3
"""Dock akıcılık ölçümü: uygulamayı başlatır, fare süpürmesi kaydeder, kare metriklerini yazar.

Kullanım: /usr/bin/python3 kaydir.py <proje_dizini> <etiket>
Çıktı: /tmp/olcum/<etiket>.json + stdout'ta tek satır özet
Metrikler: kare sayısı, tekrar (aynı) kare oranı, hareket miktarının standart sapması (düşük = akıcı).
"""
import json, os, subprocess, sys, time, glob

proje = os.path.abspath(sys.argv[1])
etiket = sys.argv[2]
DISPLAY_N = os.environ.get("OLCUM_DISPLAY", ":99")
env = dict(os.environ, DISPLAY=DISPLAY_N, QT_QPA_PLATFORM="xcb")
lib = f"{proje}/libs/usr/lib/x86_64-linux-gnu"
env["LD_LIBRARY_PATH"] = lib + ":" + env.get("LD_LIBRARY_PATH", "")

os.makedirs("/tmp/olcum", exist_ok=True)
video = f"/tmp/olcum/{etiket}.mp4"

# 1) çalışan eski dock'ları kapat (PID ile, pkill yok)
out = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
for line in out.splitlines():
    if "venv/bin/python main.py" in line:
        pid = line.split()[0]
        try:
            os.kill(int(pid), 15)
        except Exception:
            pass
time.sleep(1)

# 2) uygulamayı başlat
log = open(f"/tmp/olcum/{etiket}.log", "w")
app = subprocess.Popen([f"{proje}/.venv/bin/python", "main.py"], cwd=proje, env=env,
                       stdout=log, stderr=log)
time.sleep(5)

# 3) kayıt + fare süpürmesi
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "x11grab", "-video_size", "1440x900",
                       "-framerate", "30", "-i", DISPLAY_N, "-t", "9", "-pix_fmt", "yuv420p",
                       "-vf", "crop=900:170:280:730", video], env=env)
time.sleep(1.2)
x = 400
while x <= 1040:
    subprocess.run(["xdotool", "mousemove", str(x), "843"], env=env)
    time.sleep(0.06)
    x += 32
ff.wait()
app.terminate()
try:
    app.wait(timeout=5)
except Exception:
    app.kill()

# 4) metrikler
import numpy as np
from PIL import Image

frames = []
tmpdir = f"/tmp/olcum/{etiket}-kareler"
os.makedirs(tmpdir, exist_ok=True)
for f in glob.glob(tmpdir + "/*.png"):
    os.remove(f)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", "scale=450:-2",
                f"{tmpdir}/f_%03d.png"], check=False)
files = sorted(glob.glob(tmpdir + "/*.png"))
prev = None
diffs = []
dup = 0
for f in files:
    a = np.asarray(Image.open(f).convert("L"), dtype=np.float32)
    if prev is not None:
        d = float(np.abs(a - prev).mean())
        diffs.append(d)
        if d < 0.05:
            dup += 1
    prev = a

sonuc = {
    "etiket": etiket,
    "proje": proje,
    "kare_sayisi": len(files),
    "beklenen_kare": 270,
    "tekrar_kare_orani": round(dup / max(1, len(diffs)), 3),
    "hareket_ort": round(float(np.mean(diffs)) if diffs else 0, 3),
    "hareket_std": round(float(np.std(diffs)) if diffs else 0, 3),
    "log_son": open(f"/tmp/olcum/{etiket}.log").read()[-300:],
}
json.dump(sonuc, open(f"/tmp/olcum/{etiket}.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: sonuc[k] for k in ("etiket", "kare_sayisi", "tekrar_kare_orani",
                                       "hareket_ort", "hareket_std")}, ensure_ascii=False))
