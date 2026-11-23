#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dock/muzik.py — Dock müzik paneli veri katmanı (MPRIS over DBus).

Seçilen DBus yolu (neden bu?)
-----------------------------
Sunucuda `playerctl` YOK; Python `dbus` / `dbus-next` paketlerine bağımlı olmamak
için **CLI yolu** seçildi:

  1. BİRİNCİL: `gdbus`
     - `Properties.GetAll` ile PlaybackStatus + Metadata + Position **tek çağrıda** gelir.
     - Çıktısı tipli GVariant metni (`<'Playing'>`, `<int64 214000000>`), ayrıştırması
       dbus-send'in düz metnine göre daha güvenilir.
  2. YEDEK: `dbus-send`
     - gdbus yoksa/başarısızsa aynı veri `--print-reply` ile okunur.
     - Formatı dağınık (`array [`, `dict entry(`, `variant   string "x"`), kendi
       ayrıştırıcımız (`_gvariant_coz`) bu biçimi de anlar.

Hiçbiri yoksa ya da oturum veriyolu yoksa `kaynak="yok"` döner — istisna fırlatmaz.

Sözleşmeler
-----------
- Import anında hiçbir DBus / ağ / subprocess işi yapılmaz (backend ilk çağrıda seçilir).
- Her DBus çağrısı en fazla 2 sn (subprocess timeout + `gdbus --timeout`), asılma yok.
- Demo mod: `DOCK_MUZIK=demo` ortam değişkeni.

Genel API
---------
    durum() -> dict
        {"caliyor": bool, "baslik": str, "sanatci": str, "album": str,
         "kapak": str|None, "konum_sn": float, "sure_sn": float,
         "kaynak": "mpris"|"demo"|"yok"}
    kontrol("oynat"|"duraklat"|"ileri"|"geri") -> bool
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from urllib.parse import unquote, urlparse

__all__ = ["durum", "kontrol"]

# --- sabitler ---------------------------------------------------------------

ZAMAN_ASIMI = 2.0                              # saniye; her DBus çağrısı için üst sınır
MPRIS_ONEK = "org.mpris.MediaPlayer2."
OYUNCU_ARAYUZ = "org.mpris.MediaPlayer2.Player"
MPRIS_YOL = "/org/mpris/MediaPlayer2"
PROXY_ADLARI = {"org.mpris.MediaPlayer2.playerctld"}   # gerçek oynatıcı değil, proxy

# Eylem -> MPRIS metod adı
EYLEMLER = {
    "oynat": "Play",
    "duraklat": "Pause",
    "ileri": "Next",
    "geri": "Previous",
}

# Demo çalma listesi (ilk parça raporda/testte beklenen parça)
DEMO_PARCALAR = [
    {"baslik": "Golden Hour Drive", "sanatci": "Nova Lane", "album": "Sunset Boulevard", "sure_sn": 214.0},
    {"baslik": "Neon Rain", "sanatci": "Kite Solids", "album": "After Hours", "sure_sn": 187.0},
    {"baslik": "Sabah Kahvesi", "sanatci": "Deniz Yolu", "album": "Yavaş Sabahlar", "sure_sn": 232.0},
]

# --- modül durumu (tembel) --------------------------------------------------

_BACKEND = None      # None = henüz seçilmedi; "" = hiçbiri yok
_DEMO = None         # demo oynatıcı durumu (ilk durum() çağrısında kurulur)
_SON_ZAMAN_ASIMI = False   # son CLI çağrısı zaman aşımına mı düştü


# --- yardımcı: ortam --------------------------------------------------------

def _ortam():
    """subprocess ortamı: oturum veriyolu yoksa /run/user/<uid>/bus'a düş."""
    env = dict(os.environ)
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        aday = "/run/user/%d/bus" % os.getuid()
        if os.path.exists(aday):
            env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + aday
    if not env.get("XDG_RUNTIME_DIR"):
        aday = "/run/user/%d" % os.getuid()
        if os.path.isdir(aday):
            env["XDG_RUNTIME_DIR"] = aday
    return env


def _calistir(argv):
    """Komutu en fazla ZAMAN_ASIMI sn çalıştır. Başarısızsa None döner (istisna yok).

    Zaman aşımı ayrı işaretlenir (_SON_ZAMAN_ASIMI): aynı veriyolunda ikinci CLI'yi
    denemek de 2 sn daha harcar, dock saniyede bir yokladığı için bunu istemeyiz.
    """
    global _SON_ZAMAN_ASIMI
    _SON_ZAMAN_ASIMI = False
    try:
        sonuc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=ZAMAN_ASIMI,
            env=_ortam(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        _SON_ZAMAN_ASIMI = True
        return None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if sonuc.returncode != 0:
        return None
    return sonuc.stdout.decode("utf-8", "replace")


def _backend_sec():
    """İlk çağrıda CLI seçimi; import anında çalışmaz."""
    global _BACKEND
    if _BACKEND is None:
        if shutil.which("gdbus"):
            _BACKEND = "gdbus"
        elif shutil.which("dbus-send"):
            _BACKEND = "dbus-send"
        else:
            _BACKEND = ""
    return _BACKEND


# --- GVariant metin ayrıştırıcı --------------------------------------------
# gdbus ve dbus-send çıktılarının ikisini de okur:
#   gdbus    : ({'PlaybackStatus': <'Playing'>, 'Metadata': <{'xesam:artist': <['A']>}>},)
#   dbus-send: array [ dict entry( string "PlaybackStatus" variant string "Playing" ) ]

_ONEK_ADLARI = {
    "variant", "array", "string", "objectpath", "signature", "byte",
    "int16", "uint16", "int32", "uint32", "int64", "uint64",
    "double", "boolean", "int", "uint", "handle",
}
_SABITLER = {"true": True, "false": False, "nothing": None, "null": None}
_KACISLAR = {"n": "\n", "t": "\t", "r": "\r", "'": "'", '"': '"', "\\": "\\"}


def _bos_atla(s, i):
    while i < len(s) and s[i] in " \t\r\n,":
        i += 1
    return i


def _kelime_oku(s, i):
    bas = i
    while i < len(s) and (s[i].isalnum() or s[i] in "_-+."):
        i += 1
    return s[bas:i], i


def _cift_dict(oge):
    if isinstance(oge, (list, tuple)) and len(oge) >= 2 and len(oge) % 2 == 0:
        try:
            return dict(zip(oge[0::2], oge[1::2]))
        except TypeError:
            return list(oge)
    return oge


def _gv_oku(s, i):
    i = _bos_atla(s, i)
    if i >= len(s):
        return None, i
    c = s[i]

    if c in "([{":
        kapanis = {"(": ")", "[": "]", "{": "}"}[c]
        i += 1
        oge = []
        while True:
            i = _bos_atla(s, i)
            if i >= len(s):
                break
            if s[i] == kapanis:
                i += 1
                break
            if s[i] == ":":          # dict ayıracı
                i += 1
                continue
            deger, i = _gv_oku(s, i)
            oge.append(deger)
        if c == "(":
            return tuple(oge), i
        if c == "[":
            return oge, i
        return _cift_dict(oge), i

    if c == "<":
        deger, i = _gv_oku(s, i + 1)
        i = _bos_atla(s, i)
        if i < len(s) and s[i] == ">":
            i += 1
        return deger, i

    if c == "@":                     # @as [] gibi tip ipuçları
        i += 1
        while i < len(s) and s[i] not in " \t\r\n":
            i += 1
        return _gv_oku(s, i)

    if c in "'\"":
        tirnak = c
        i += 1
        buf = []
        while i < len(s):
            ch = s[i]
            if ch == "\\" and i + 1 < len(s):
                buf.append(_KACISLAR.get(s[i + 1], s[i + 1]))
                i += 2
                continue
            if ch == tirnak:
                return "".join(buf), i + 1
            buf.append(ch)
            i += 1
        return "".join(buf), i

    kelime, i = _kelime_oku(s, i)
    if not kelime:
        return None, i + 1

    if kelime in _SABITLER:
        return _SABITLER[kelime], i

    if kelime == "dict":             # dbus-send: "dict entry( k v )"
        j = _bos_atla(s, i)
        k = j
        while k < len(s) and s[k].isalpha():
            k += 1
        if s[j:k] == "entry":
            i = k
        grup, i = _gv_oku(s, i)
        return _cift_dict(grup), i

    if kelime == "object":           # dbus-send: "object path \"/x\""
        j = _bos_atla(s, i)
        k = j
        while k < len(s) and s[k].isalpha():
            k += 1
        if s[j:k] == "path":
            i = k
        return _gv_oku(s, i)

    if kelime in _ONEK_ADLARI:       # tip öneki: değeri ayrıştır, öneki yut
        return _gv_oku(s, i)

    try:
        if kelime.startswith(("0x", "-0x")):
            return int(kelime, 16), i
        return int(kelime), i
    except ValueError:
        pass
    try:
        return float(kelime), i
    except ValueError:
        return kelime, i


def _gvariant_coz(metin):
    """DBus CLI çıktısını Python nesnesine çevir (başlık satırlarını atlar)."""
    if not metin:
        return None
    metin = metin.strip()
    # dbus-send başlığı: "method return time=... sender=..." — ilk satırı at.
    # (gdbus başlık yazmaz, bu dal ona dokunmaz.)
    if metin.startswith("method return"):
        satir_sonu = metin.find("\n")
        metin = metin[satir_sonu + 1:].strip() if satir_sonu != -1 else ""
    deger, _ = _gv_oku(metin, 0)
    return deger


# --- DBus çağrıları ---------------------------------------------------------

def _gdbus(hedef, yontem, *argumanlar):
    argv = [
        "gdbus", "call", "--session", "--timeout", str(int(ZAMAN_ASIMI)),
        "--dest", hedef, "--object-path", MPRIS_YOL, "--method", yontem,
    ]
    argv.extend(argumanlar)
    return _calistir(argv)


def _dbus_send(hedef, yontem, *argumanlar):
    argv = ["dbus-send", "--session", "--print-reply", "--dest=" + hedef, MPRIS_YOL, yontem]
    argv.extend(argumanlar)
    return _calistir(argv)


def _isimler():
    """Oturum veriyolundaki tüm bus adları (boş liste = veriyolu yok)."""
    backend = _backend_sec()
    if not backend:
        return []

    if backend == "gdbus":
        cikti = _calistir([
            "gdbus", "call", "--session", "--timeout", str(int(ZAMAN_ASIMI)),
            "--dest", "org.freedesktop.DBus", "--object-path", "/org/freedesktop/DBus",
            "--method", "org.freedesktop.DBus.ListNames",
        ])
        if cikti:
            try:
                deger = _gvariant_coz(cikti)
                if isinstance(deger, tuple) and deger:
                    deger = deger[0]
                if isinstance(deger, (list, tuple)):
                    return [str(x) for x in deger]
            except Exception:
                pass
        if _SON_ZAMAN_ASIMI:
            # bus asılı: dbus-send de asılır, 2 sn daha harcamayalım
            return []

    cikti = _calistir([
        "dbus-send", "--session", "--print-reply", "--dest=org.freedesktop.DBus",
        "/org/freedesktop/DBus", "org.freedesktop.DBus.ListNames",
    ])
    if cikti:
        return re.findall(r'string\s+"([^"]+)"', cikti)
    return []


def _adaylar():
    """MPRIS oynatıcı adları; proxy (playerctld) sona atılır."""
    adlar = [a for a in _isimler() if a.startswith(MPRIS_ONEK)]
    gercek = [a for a in adlar if a not in PROXY_ADLARI]
    proxy = [a for a in adlar if a in PROXY_ADLARI]
    # en fazla 3 aday denenir: her aday 1 DBus çağrısı (2 sn) demek
    return (gercek + proxy)[:3]


def _dictest(oge):
    """dbus-send'in `array [ dict entry(...) ]` çıktısını tek sözlüğe indirger."""
    if isinstance(oge, dict):
        return oge
    if isinstance(oge, (list, tuple)) and oge and all(isinstance(x, dict) for x in oge):
        birlesik = {}
        for x in oge:
            birlesik.update(x)
        return birlesik
    return None


def _ozellikler(hedef):
    """Player arayüzünün tüm özellikleri (PlaybackStatus, Metadata, Position...)."""
    backend = _backend_sec()
    if backend == "gdbus":
        cikti = _gdbus(hedef, "org.freedesktop.DBus.Properties.GetAll", OYUNCU_ARAYUZ)
        if cikti:
            try:
                deger = _gvariant_coz(cikti)
                if isinstance(deger, tuple) and deger:
                    deger = deger[0]
                sozluk = _dictest(deger)
                if sozluk:
                    return sozluk
            except Exception:
                pass
        return None

    if backend == "dbus-send":
        cikti = _dbus_send(
            hedef, "org.freedesktop.DBus.Properties.GetAll", "string:" + OYUNCU_ARAYUZ
        )
        if cikti:
            try:
                sozluk = _dictest(_gvariant_coz(cikti))
                if sozluk:
                    return sozluk
            except Exception:
                pass
    return None


# --- alan yardımcıları ------------------------------------------------------

def _metin(deger):
    if deger is None:
        return ""
    if isinstance(deger, (list, tuple)):
        return ", ".join(str(x) for x in deger if x)
    if isinstance(deger, bytes):
        return deger.decode("utf-8", "replace")
    return str(deger).strip()


def _saniye(deger, varsayilan=0.0):
    """MPRIS mikrosaniye -> saniye (negatif/anlamsız değerler varsayılana düşer)."""
    try:
        sn = float(deger) / 1_000_000.0
    except (TypeError, ValueError):
        return varsayilan
    if sn != sn or sn < 0 or sn > 24 * 3600:      # NaN / saçma değer
        return varsayilan
    return sn


def _kapak_yolu(url):
    """mpris:artUrl -> yerel dosya yolu; dosya değilse/yoksa None."""
    if not url or not isinstance(url, str):
        return None
    if not url.startswith("file://"):
        return None                                # http(s) indirilmez: UI tarafı işi
    try:
        yol = unquote(urlparse(url).path)
    except ValueError:
        return None
    return yol if os.path.isfile(yol) else None


def _bos_durum(kaynak="yok"):
    return {
        "caliyor": False,
        "baslik": "",
        "sanatci": "",
        "album": "",
        "kapak": None,
        "konum_sn": 0.0,
        "sure_sn": 0.0,
        "kaynak": kaynak,
    }


# --- demo modu --------------------------------------------------------------

def _demo_mu():
    return os.environ.get("DOCK_MUZIK", "").strip().lower() == "demo"


def _demo_durum():
    global _DEMO
    demo = _DEMO
    if demo is None:
        demo = {"idx": 0, "baslangic": time.monotonic(), "birikmis": 0.0, "caliyor": True}
        _DEMO = demo
    parca = DEMO_PARCALAR[demo["idx"]]
    konum = demo["birikmis"]
    if demo["caliyor"]:
        konum += time.monotonic() - demo["baslangic"]
    sure = float(parca["sure_sn"])
    konum = konum % sure if sure > 0 else 0.0
    return {
        "caliyor": bool(demo["caliyor"]),
        "baslik": parca["baslik"],
        "sanatci": parca["sanatci"],
        "album": parca["album"],
        "kapak": None,
        "konum_sn": round(konum, 2),
        "sure_sn": sure,
        "kaynak": "demo",
    }


def _demo_kontrol(eylem):
    _demo_durum()                                  # durumu kur
    demo = _DEMO
    if demo is None:
        return False
    simdi = time.monotonic()
    if eylem == "duraklat":
        if demo["caliyor"]:                        # oynarken konumu dondur
            demo["birikmis"] += simdi - demo["baslangic"]
            demo["caliyor"] = False
        return True                                # zaten duraklıysa da başarılı (idempotent)
    if eylem == "oynat":
        if not demo["caliyor"]:
            demo["baslangic"] = simdi
            demo["caliyor"] = True
        return True
    if eylem in ("ileri", "geri"):
        adim = 1 if eylem == "ileri" else -1
        demo["idx"] = (demo["idx"] + adim) % len(DEMO_PARCALAR)
        demo["birikmis"] = 0.0
        demo["baslangic"] = simdi
        return True
    return False


# --- genel API --------------------------------------------------------------

def durum():
    """Çalan parçanın anlık durumu. Hata durumunda bile sözlük döner."""
    try:
        if _demo_mu():
            return _demo_durum()

        adaylar = _adaylar()
        if not adaylar:
            return _bos_durum("yok")

        secilen = None
        yedek = None                                   # duraklatılmış/stopped ilk aday
        for ad in adaylar:
            ozellik = _ozellikler(ad)
            if _SON_ZAMAN_ASIMI:
                break                                  # oynatıcı asılı: sıradakini deneme
            if not ozellik:
                continue
            if yedek is None:
                yedek = (ad, ozellik)
            if _metin(ozellik.get("PlaybackStatus")) == "Playing":
                secilen = (ad, ozellik)
                break

        ad, ozellik = secilen or yedek or (None, None)
        if ozellik is None:
            return _bos_durum("yok")

        meta = _dictest(ozellik.get("Metadata")) or {}

        sure = _saniye(meta.get("mpris:length"), 0.0)
        konum = _saniye(ozellik.get("Position"), 0.0)
        if sure > 0 and konum > sure:
            konum = 0.0                                # bazı oynatıcılar bayat konum verir

        return {
            "caliyor": _metin(ozellik.get("PlaybackStatus")) == "Playing",
            "baslik": _metin(meta.get("xesam:title")),
            "sanatci": _metin(meta.get("xesam:artist")),
            "album": _metin(meta.get("xesam:album")),
            "kapak": _kapak_yolu(meta.get("mpris:artUrl")),
            "konum_sn": round(konum, 2),
            "sure_sn": round(sure, 2),
            "kaynak": "mpris",
        }
    except Exception:
        # Veri katmanı asla UI'yı düşürmesin.
        return _bos_durum("yok")


def kontrol(eylem):
    """'oynat' | 'duraklat' | 'ileri' | 'geri' -> bool (başarılı mı)."""
    try:
        if not isinstance(eylem, str):
            return False
        eylem = eylem.strip().lower()
        metod = EYLEMLER.get(eylem)
        if not metod:
            return False

        if _demo_mu():
            return _demo_kontrol(eylem)

        adaylar = _adaylar()
        if not adaylar:
            return False

        backend = _backend_sec()
        tam_yontem = OYUNCU_ARAYUZ + "." + metod
        for ad in adaylar:
            if backend == "gdbus":
                cikti = _gdbus(ad, tam_yontem)
            elif backend == "dbus-send":
                cikti = _dbus_send(ad, tam_yontem)
            else:
                return False
            if cikti is not None:
                return True
            if _SON_ZAMAN_ASIMI:
                return False                           # asılı oynatıcı: sıradakini deneme
        return False
    except Exception:
        return False


if __name__ == "__main__":
    import json

    print(json.dumps(durum(), ensure_ascii=False, indent=2))
