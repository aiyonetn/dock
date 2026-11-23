#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muzik.py testi — demo mod + gerçek mod (oynatıcı yok) + GVariant ayrıştırıcı.

Çalıştır:  python3 muzik-test.py
Çıkış kodu 0 = hepsi geçti.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)

import muzik  # noqa: E402

GECEN = 0
KALAN = 0
HATALAR = []


def kontrol(ad, kosul, ek=None):
    global GECEN, KALAN
    if kosul:
        GECEN += 1
        print("  [GECTI] %s" % ad)
    else:
        KALAN += 1
        HATALAR.append(ad)
        print("  [KALDI] %s%s" % (ad, (" -> " + str(ek)) if ek is not None else ""))


def alanlar_tam(d):
    beklenen = {"caliyor", "baslik", "sanatci", "album", "kapak",
                "konum_sn", "sure_sn", "kaynak"}
    return isinstance(d, dict) and beklenen <= set(d)


# --- 1. GVariant ayrıştırıcı (oynatıcı olmadan doğrulama) -------------------
def test_ayristirici():
    print("\n[1] GVariant ayristirici (gdbus bicimi)")
    ornek = (
        "({'CanControl': <true>, 'Metadata': <{'mpris:artUrl': <'file:///tmp/"
        "kapak%20bir.png'>, 'mpris:length': <int64 214000000>, 'mpris:trackid': "
        "<objectpath '/org/mpris/MediaPlayer2/Track/7'>, 'xesam:album': "
        "<'Sunset Boulevard'>, 'xesam:artist': <['Nova Lane']>, 'xesam:title': "
        "<'Golden Hour Drive'>}>, 'PlaybackStatus': <'Playing'>, 'Position': "
        "<int64 12345678>},)"
    )
    kok = muzik._gvariant_coz(ornek)
    if isinstance(kok, tuple) and kok:
        kok = kok[0]
    kontrol("kok sozluk", isinstance(kok, dict), type(kok))
    if not isinstance(kok, dict):
        return
    kontrol("PlaybackStatus", kok.get("PlaybackStatus") == "Playing", kok.get("PlaybackStatus"))
    kontrol("Position int64", kok.get("Position") == 12345678, kok.get("Position"))
    meta = kok.get("Metadata") or {}
    kontrol("Metadata sozluk", isinstance(meta, dict), type(meta))
    kontrol("baslik", meta.get("xesam:title") == "Golden Hour Drive", meta.get("xesam:title"))
    kontrol("sanatci listesi", meta.get("xesam:artist") == ["Nova Lane"], meta.get("xesam:artist"))
    kontrol("sure mikro->sn", muzik._saniye(meta.get("mpris:length")) == 214.0)
    bos = muzik._gvariant_coz("(@as [],)")
    if isinstance(bos, tuple) and bos:
        bos = bos[0]
    kontrol("bos dizi", bos == [], bos)

    # dbus-send bicimi de ayni ayristiricidan gecmeli
    ds = (
        'method return time=1.0 sender=:1.1 -> destination=:1.2 serial=3 reply_serial=2\n'
        "   array [\n"
        "      dict entry(\n"
        '         string "PlaybackStatus"\n'
        '         variant             string "Playing"\n'
        "      )\n"
        "      dict entry(\n"
        '         string "Metadata"\n'
        "         variant             array [\n"
        "            dict entry(\n"
        '               string "xesam:title"\n'
        '               variant             string "Neon Rain"\n'
        "            )\n"
        "         ]\n"
        "      )\n"
        "   ]\n"
    )
    d = muzik._dictest(muzik._gvariant_coz(ds))
    kontrol("dbus-send sozluk", isinstance(d, dict), type(d))
    if isinstance(d, dict):
        kontrol("dbus-send PlaybackStatus", d.get("PlaybackStatus") == "Playing", d.get("PlaybackStatus"))
        md = muzik._dictest(d.get("Metadata")) or {}
        kontrol("dbus-send baslik", isinstance(md, dict) and md.get("xesam:title") == "Neon Rain", md)

    # kapak: dosya varsa yol, yoksa None
    with tempfile.NamedTemporaryFile(suffix=" kapak.png", delete=False) as f:
        yol = f.name
    try:
        import urllib.parse
        url = "file://" + urllib.parse.quote(yol)
        kontrol("kapak dosya yolu", muzik._kapak_yolu(url) == yol, muzik._kapak_yolu(url))
        kontrol("kapak http -> None", muzik._kapak_yolu("https://x/y.png") is None)
        kontrol("kapak olmayan dosya -> None",
                muzik._kapak_yolu("file:///tmp/boyle-bir-dosya-yok-123.png") is None)
    finally:
        os.unlink(yol)


# --- 2. demo mod ------------------------------------------------------------
def test_demo():
    print("\n[2] demo mod (DOCK_MUZIK=demo)")
    os.environ["DOCK_MUZIK"] = "demo"
    d = muzik.durum()
    print("  durum:", json.dumps(d, ensure_ascii=False))
    kontrol("sozluk alanlari tam", alanlar_tam(d), d)
    kontrol("kaynak=demo", d.get("kaynak") == "demo", d.get("kaynak"))
    kontrol("baslik", d.get("baslik") == "Golden Hour Drive", d.get("baslik"))
    kontrol("sanatci", d.get("sanatci") == "Nova Lane", d.get("sanatci"))
    kontrol("sure_sn=214", d.get("sure_sn") == 214.0, d.get("sure_sn"))
    kontrol("caliyor", d.get("caliyor") is True)

    k0 = d.get("konum_sn", 0)
    time.sleep(0.8)
    k1 = muzik.durum().get("konum_sn", 0)
    kontrol("konum ilerliyor", k1 > k0, "%s -> %s" % (k0, k1))

    kontrol("duraklat True", muzik.kontrol("duraklat") is True)
    d = muzik.durum()
    kontrol("duraklat sonrasi caliyor=False", d.get("caliyor") is False, d.get("caliyor"))
    k2 = d.get("konum_sn", 0)
    time.sleep(0.4)
    k3 = muzik.durum().get("konum_sn", 0)
    kontrol("duraklatinca konum sabit", abs(k3 - k2) < 0.05, "%s -> %s" % (k2, k3))

    kontrol("oynat True", muzik.kontrol("oynat") is True)
    kontrol("oynat sonrasi caliyor=True", muzik.durum().get("caliyor") is True)

    kontrol("ileri True", muzik.kontrol("ileri") is True)
    d = muzik.durum()
    kontrol("ileri parca degisti", d.get("baslik") == "Neon Rain", d.get("baslik"))
    kontrol("konum sifirlandi", d.get("konum_sn", 99) < 1.0, d.get("konum_sn"))
    kontrol("geri True", muzik.kontrol("geri") is True)
    kontrol("geri ilk parcaya dondu", muzik.durum().get("baslik") == "Golden Hour Drive")

    kontrol("bilinmeyen eylem False", muzik.kontrol("zikzak") is False)
    kontrol("None eylem False", muzik.kontrol(None) is False)


# --- 3. gerçek mod ----------------------------------------------------------
def test_gercek():
    print("\n[3] gercek mod (MPRIS / oynatici yok senaryosu)")
    os.environ.pop("DOCK_MUZIK", None)
    t0 = time.monotonic()
    d = muzik.durum()
    gecen = time.monotonic() - t0
    print("  durum:", json.dumps(d, ensure_ascii=False))
    print("  sure: %.2f sn" % gecen)
    kontrol("sozluk alanlari tam", alanlar_tam(d), d)
    kontrol("kaynak mpris|yok", d.get("kaynak") in ("mpris", "yok"), d.get("kaynak"))
    kontrol("caliyor bool", isinstance(d.get("caliyor"), bool))
    kontrol("konum/sure float", isinstance(d.get("konum_sn"), float) and isinstance(d.get("sure_sn"), float))
    kontrol("2 sn x aday siniri (<=7 sn)", gecen <= 7.0, gecen)

    for eylem in ("oynat", "duraklat", "ileri", "geri", "yok-boyle-bir-sey"):
        sonuc = muzik.kontrol(eylem)
        kontrol("kontrol(%s) bool" % eylem, isinstance(sonuc, bool), sonuc)

    d2 = muzik.durum()
    kontrol("ikinci cagri da sagliyor", alanlar_tam(d2) and d2.get("kaynak") in ("mpris", "yok"))


# --- 4. import saflığı ------------------------------------------------------
def test_import_safi():
    print("\n[4] import yan etkisizligi")
    kod = (
        "import sys; sys.path.insert(0, {yol!r}); import muzik;"
        "print('BACKEND=%r' % (muzik._BACKEND,));"
        "print('DEMO=%r' % (muzik._DEMO,))"
    ).format(yol=BURASI)
    p = subprocess.run([sys.executable, "-c", kod], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=20, text=True)
    print("  ", p.stdout.strip().replace("\n", " | "), p.stderr.strip()[:200])
    kontrol("import rc=0", p.returncode == 0, p.stderr[-300:])
    kontrol("import aninda backend secilmedi (None)", "BACKEND=None" in p.stdout, p.stdout)
    kontrol("import aninda demo kurulmadi (None)", "DEMO=None" in p.stdout, p.stdout)


# --- 5. CLI yokmuş gibi davran (graceful) -----------------------------------
def test_cli_yok():
    print("\n[5] CLI yokmus gibi davranma")
    import shutil
    yedek_which = shutil.which
    shutil.which = lambda ad, *a, **k: None
    yedek_backend = muzik._BACKEND
    muzik._BACKEND = None
    try:
        d = muzik.durum()
        kontrol("kaynak=yok", d.get("kaynak") == "yok", d.get("kaynak"))
        kontrol("kontrol False", muzik.kontrol("oynat") is False)
        kontrol("cokme yok", alanlar_tam(d))
    finally:
        shutil.which = yedek_which
        muzik._BACKEND = yedek_backend


# --- 6. asılı CLI -> 2 sn sınırı -------------------------------------------
def test_zaman_asimi():
    print("\n[6] asili DBus CLI -> 2 sn siniri")
    sahte = tempfile.mkdtemp(prefix="sahte-cli-")
    for ad in ("gdbus", "dbus-send"):
        yol = os.path.join(sahte, ad)
        with open(yol, "w") as f:
            f.write("#!/bin/sh\nsleep 30\n")
        os.chmod(yol, 0o755)
    yedek_path = os.environ.get("PATH", "")
    os.environ["PATH"] = sahte + ":" + yedek_path
    os.environ.pop("DOCK_MUZIK", None)
    try:
        t0 = time.monotonic()
        d = muzik.durum()
        g1 = time.monotonic() - t0
        kontrol("durum <= 3 sn (asili CLI)", g1 <= 3.0, "%.2f sn" % g1)
        kontrol("asili CLI -> kaynak=yok", d.get("kaynak") == "yok", d.get("kaynak"))
        t0 = time.monotonic()
        r = muzik.kontrol("oynat")
        g2 = time.monotonic() - t0
        kontrol("kontrol <= 3 sn (asili CLI)", g2 <= 3.0, "%.2f sn" % g2)
        kontrol("asili CLI -> kontrol False", r is False, r)
    finally:
        os.environ["PATH"] = yedek_path
        shutil.rmtree(sahte, ignore_errors=True)


if __name__ == "__main__":
    print("muzik.py testi — python %s" % sys.version.split()[0])
    test_ayristirici()
    test_demo()
    test_gercek()
    test_import_safi()
    test_cli_yok()
    test_zaman_asimi()

    print("\n--- sonuc: %d gecti, %d kaldi ---" % (GECEN, KALAN))
    if KALAN:
        print("hatalar:", ", ".join(HATALAR))
    sys.exit(0 if KALAN == 0 else 1)
