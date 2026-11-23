#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sahte-mpris.py — test için minik MPRIS oynatıcı (dbus-python + GLib).

Gerçek oynatıcı olmayan sunucuda `muzik.py`'nin DBus yolunu uçtan uca denemek için.
Sunucuda `playerctl` yok; bu sahte oynatıcı `org.mpris.MediaPlayer2.docktest` adını
alır ve Player arayüzünün GetAll / Play / Pause / Next / Previous üyelerini sunar.

Kullanım (kendi başına test):
    python3 sahte-mpris.py --dogrula        # kendi dbus-run-session'ını açar, test eder

Sadece sunucu olarak çalıştırmak (başka bir kabukta muzik.py denemek için):
    python3 sahte-mpris.py --sure 60
"""

import os
import subprocess
import sys
import time

AD = "org.mpris.MediaPlayer2.docktest"
YOL = "/org/mpris/MediaPlayer2"

PARCALAR = [
    {"baslik": "Golden Hour Drive", "sanatci": "Nova Lane",
     "album": "Sunset Boulevard", "sure_sn": 214.0, "kapak": "file:///tmp/yok.png"},
    {"baslik": "Neon Rain", "sanatci": "Kite Solids",
     "album": "After Hours", "sure_sn": 187.0, "kapak": "file:///tmp/yok.png"},
]


def sunucu_calistir(sure_sn=60):
    import dbus
    import dbus.mainloop.glib
    import dbus.service
    from gi.repository import GLib

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    ad = dbus.service.BusName(AD, bus)

    class Oynatici(dbus.service.Object):
        def __init__(self):
            super().__init__(bus, YOL)
            self.idx = 0
            self.caliyor = True
            self.konum_us = 5_000_000

        # --- yardımcılar
        def parca(self):
            return PARCALAR[self.idx]

        def metadata(self):
            p = self.parca()
            return dbus.Dictionary({
                "mpris:trackid": dbus.ObjectPath(YOL + "/Track/1"),
                "mpris:length": dbus.Int64(int(p["sure_sn"] * 1_000_000)),
                "mpris:artUrl": dbus.String(p["kapak"]),
                "xesam:title": dbus.String(p["baslik"]),
                "xesam:artist": dbus.Array([p["sanatci"]], signature="s"),
                "xesam:album": dbus.String(p["album"]),
            }, signature="sv")

        def ozellikler(self):
            return dbus.Dictionary({
                "PlaybackStatus": dbus.String("Playing" if self.caliyor else "Paused"),
                "Metadata": dbus.Dictionary(self.metadata(), signature="sv"),
                "Position": dbus.Int64(self.konum_us),
                "CanControl": dbus.Boolean(True),
                "CanGoNext": dbus.Boolean(True),
                "CanGoPrevious": dbus.Boolean(True),
            }, signature="sv")

        # --- Properties
        @dbus.service.method("org.freedesktop.DBus.Properties",
                             in_signature="ss", out_signature="v")
        def Get(self, arayuz, ad_):
            return self.ozellikler().get(str(ad_), dbus.String(""))

        @dbus.service.method("org.freedesktop.DBus.Properties",
                             in_signature="s", out_signature="a{sv}")
        def GetAll(self, arayuz):
            return self.ozellikler()

        # --- Player
        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Play(self):
            self.caliyor = True

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Pause(self):
            self.caliyor = False

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Next(self):
            self.idx = (self.idx + 1) % len(PARCALAR)
            self.konum_us = 0

        @dbus.service.method("org.mpris.MediaPlayer2.Player")
        def Previous(self):
            self.idx = (self.idx - 1) % len(PARCALAR)
            self.konum_us = 0

    Oynatici()
    print("hazir: %s" % AD, flush=True)
    GLib.timeout_add_seconds(int(sure_sn), lambda: (loop.quit(), False)[1])
    loop = GLib.MainLoop()
    loop.run()


# --- uçtan uca doğrulama ----------------------------------------------------

def _dogrula_ic():
    """dbus-run-session içinde: sahte oynatıcıyı başlat, muzik.py'yi onunla dene."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    kok = os.path.dirname(os.path.abspath(__file__))

    sunucu = subprocess.Popen(
        [sys.executable, os.path.join(kok, "sahte-mpris.py"), "--sure", "60"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        # ad bus'ta görünene kadar bekle (en fazla 10 sn)
        son = time.time() + 10
        while time.time() < son:
            p = subprocess.run(["gdbus", "call", "--session", "--dest", "org.freedesktop.DBus",
                                "--object-path", "/org/freedesktop/DBus",
                                "--method", "org.freedesktop.DBus.ListNames"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if AD in (p.stdout or ""):
                break
            time.sleep(0.2)

        import json
        import muzik

        sonuc = []
        d = muzik.durum()
        print("  durum:", json.dumps(d, ensure_ascii=False))
        sonuc.append(("kaynak=mpris", d.get("kaynak") == "mpris"))
        sonuc.append(("baslik dogru", d.get("baslik") == "Golden Hour Drive"))
        sonuc.append(("sanatci listesi -> metin", d.get("sanatci") == "Nova Lane"))
        sonuc.append(("album", d.get("album") == "Sunset Boulevard"))
        sonuc.append(("sure 214 sn", d.get("sure_sn") == 214.0))
        sonuc.append(("konum 5 sn", abs(d.get("konum_sn", 0) - 5.0) < 0.01))
        sonuc.append(("caliyor True", d.get("caliyor") is True))
        sonuc.append(("kapak: olmayan dosya -> None", d.get("kapak") is None))

        sonuc.append(("kontrol(duraklat)", muzik.kontrol("duraklat") is True))
        time.sleep(0.2)
        sonuc.append(("duraklat sonrasi caliyor=False", muzik.durum().get("caliyor") is False))
        sonuc.append(("kontrol(oynat)", muzik.kontrol("oynat") is True))
        time.sleep(0.2)
        sonuc.append(("oynat sonrasi caliyor=True", muzik.durum().get("caliyor") is True))
        sonuc.append(("kontrol(ileri)", muzik.kontrol("ileri") is True))
        time.sleep(0.2)
        sonuc.append(("ileri sonrasi baslik", muzik.durum().get("baslik") == "Neon Rain"))
        sonuc.append(("kontrol(geri)", muzik.kontrol("geri") is True))
        time.sleep(0.2)
        sonuc.append(("geri sonrasi baslik", muzik.durum().get("baslik") == "Golden Hour Drive"))
        sonuc.append(("bilinmeyen eylem False", muzik.kontrol("zart") is False))
    finally:
        sunucu.terminate()
        try:
            sunucu.wait(timeout=3)
        except subprocess.TimeoutExpired:
            sunucu.kill()

    kalan = [ad for ad, gecti in sonuc if not gecti]
    print("  %d gecti, %d kaldi" % (len(sonuc) - len(kalan), len(kalan)))
    if kalan:
        print("  KALAN:", ", ".join(kalan))
    return 0 if not kalan else 1


def dogrula():
    """Kendi dbus-run-session'ını açıp _dogrula_ic()'i orada çalıştırır."""
    if os.environ.get("SAHTE_MPRIS_IC") != "1":
        env = dict(os.environ)
        env["SAHTE_MPRIS_IC"] = "1"
        env.pop("DOCK_MUZIK", None)          # gerçek MPRIS yolunu test et
        p = subprocess.run(["dbus-run-session", "--",
                            sys.executable, os.path.abspath(__file__), "--dogrula"],
                           env=env)
        return p.returncode
    return _dogrula_ic()


if __name__ == "__main__":
    if "--dogrula" in sys.argv:
        sys.exit(dogrula())
    sure = 60
    if "--sure" in sys.argv:
        sure = int(sys.argv[sys.argv.index("--sure") + 1])
    sunucu_calistir(sure)
