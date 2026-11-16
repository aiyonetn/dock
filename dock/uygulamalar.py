"""`.desktop` taramasi, ikon cozumleme ve uygulama baslatma."""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from functools import lru_cache
from dataclasses import asdict, dataclass, field
from pathlib import Path

DESKTOP_DIZINLERI = [
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".local/share/applications",
]

# Dogrudan denenen ikon yollari: agacta dolasmak yok.
HICOLOR_KOKLERI = [
    Path.home() / ".local/share/icons/hicolor",
    Path("/usr/share/icons/hicolor"),
]
TEMA_KOKLERI = [
    Path.home() / ".local/share/icons/Papirus",
    Path("/usr/share/icons/Papirus"),
    Path("/usr/share/icons/ePapirus"),
    Path("/usr/share/icons/elementary-xfce"),
    Path("/usr/share/icons/Adwaita"),
]
PIXMAPS = Path("/usr/share/pixmaps")
# 64 px kaynak: dock ikonu 56 px, buyutmede 106 px'e kadar cikar.
IKON_BOYUTLARI = (64, 128, 48, 256, 32)
IKON_UZANTILARI = ("png", "svg", "svgz")

YER_TUTUCU = Path(__file__).resolve().parent.parent / "assets" / "ikon-yok.svg"

_DOSYA_SINIRI = 40
_ONBELLEK_SURUM = 4

# Varsayilan dock: yalnizca gercek ikonu cozulen uygulamalar girer.
# (kimlik, ikon adi, komut adaylari) — .desktop yoksa komut /usr/bin'den aranir.
ONERILEN = [
    ("google-chrome.desktop", "google-chrome", ("google-chrome", "google-chrome-stable")),
    ("firefox.desktop", "firefox", ("firefox",)),
    ("code.desktop", "code", ("code",)),
    ("org.gnome.Terminal.desktop", "org.gnome.Terminal", ("gnome-terminal",)),
    ("vlc.desktop", "vlc", ("vlc",)),
    ("gimp.desktop", "gimp", ("gimp",)),
    ("libreoffice-writer.desktop", "libreoffice-writer", ("libreoffice", "libreoffice-writer")),
    ("thunderbird.desktop", "thunderbird", ("thunderbird",)),
    ("spotify.desktop", "spotify", ("spotify",)),
    ("discord.desktop", "discord", ("discord",)),
    ("telegram.desktop", "telegram", ("telegram-desktop", "telegram")),
    ("steam.desktop", "steam", ("steam",)),
]
_EN_AZ_IKON = 7

# %f %F %u %U %i %c %k %d %D %n %N %v %m  -> alan kodlari
_ALAN_KODU = re.compile(r"%(?:%|.)")


@dataclass
class Uygulama:
    kimlik: str  # dosya adi, or. "firefox.desktop"
    ad: str
    ikon: str = ""  # mutlak yol; bulunamazsa ""
    komut: list[str] = field(default_factory=list)

    @property
    def baslatilabilir(self) -> bool:
        return bool(self.komut)


def onbellek_yolu() -> Path:
    kok = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(kok) / "dock" / "ikonlar.json"


def _alanlari_oku(yol: Path) -> dict[str, str]:
    alanlar: dict[str, str] = {}
    bolum = ""
    try:
        satirlar = yol.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return alanlar
    for satir in satirlar:
        satir = satir.strip()
        if not satir or satir.startswith("#"):
            continue
        if satir.startswith("["):
            bolum = satir
            if alanlar and bolum != "[Desktop Entry]":
                break
            continue
        if bolum != "[Desktop Entry]" or "=" not in satir:
            continue
        anahtar, deger = satir.split("=", 1)
        alanlar.setdefault(anahtar.strip(), deger.strip())
    return alanlar


def _komut_coz(exec_satiri: str) -> list[str]:
    try:
        parcalar = shlex.split(exec_satiri)
    except ValueError:
        parcalar = exec_satiri.split()
    temiz: list[str] = []
    for parca in parcalar:
        if _ALAN_KODU.fullmatch(parca):
            continue
        parca = parca.replace("%%", "%")
        if parca:
            temiz.append(parca)
    return temiz


@lru_cache(maxsize=256)
def _dizin_esle(dizin: Path) -> dict[str, Path] | None:
    """Dizin icerigini (kucuk harf govde -> yol) olarak onbellege alir."""
    try:
        with os.scandir(dizin) as tarayici:
            return {
                Path(g.name).stem.casefold(): Path(g.path)
                for g in tarayici
                if g.is_file()
            }
    except OSError:
        return None


def _ada_gore(dizin: Path, ad: str) -> Path | None:
    kucuk = ad.casefold()
    for uzanti in IKON_UZANTILARI:
        aday = dizin / f"{ad}.{uzanti}"
        if aday.is_file():
            return aday
    esleme = _dizin_esle(dizin)
    if esleme and kucuk in esleme:
        return esleme[kucuk]
    return None


def ikon_bul(ikon_adi: str) -> str:
    """SVG -> 256/128/64 px PNG sirasi; 48 px alti kullanilmaz."""
    if not ikon_adi:
        return ""
    yol = Path(ikon_adi)
    if yol.is_absolute():
        if yol.is_file():
            return str(yol)
        ad = yol.stem
    else:
        ad = yol.name
        if yol.suffix.lstrip(".") in IKON_UZANTILARI:
            ad = yol.stem
    if not ad:
        return ""

    kokler = (*HICOLOR_KOKLERI, *TEMA_KOKLERI)
    # 1) SVG
    for kok in kokler:
        for boyut in ("scalable", "64x64"):
            aday = _ada_gore(kok / boyut / "apps", ad)
            if aday is not None and aday.suffix.lower() == ".svg":
                return str(aday)
    # 2) 256 / 128 / 64 px PNG
    for boyut in (256, 128, 64):
        for kok in kokler:
            aday = _ada_gore(kok / f"{boyut}x{boyut}" / "apps", ad)
            if aday is not None and aday.suffix.lower() in (".png", ".svg"):
                return str(aday)
    for uzanti in ("png", "svg"):
        aday = PIXMAPS / f"{ad}.{uzanti}"
        if aday.is_file():
            return str(aday)
    return ""


def _desktop_dosyalari(sinir: int = _DOSYA_SINIRI) -> list[Path]:
    """Tek gecisli scandir; ayni adli dosya bir kez, ada gore sirali."""
    gorulen: set[str] = set()
    dosyalar: list[Path] = []
    for dizin in DESKTOP_DIZINLERI:
        try:
            with os.scandir(dizin) as tarayici:
                for girdi in tarayici:
                    if not girdi.name.endswith(".desktop") or not girdi.is_file():
                        continue
                    if girdi.name in gorulen:
                        continue
                    gorulen.add(girdi.name)
                    dosyalar.append(Path(girdi.path))
        except OSError:
            continue
    dosyalar.sort(key=lambda d: d.name)
    return dosyalar[:sinir]


def _tara_yavas() -> list[Uygulama]:
    uygulamalar: list[Uygulama] = []
    for dosya in _desktop_dosyalari():
        alanlar = _alanlari_oku(dosya)
        if alanlar.get("Type", "Application") != "Application":
            continue
        if alanlar.get("Hidden", "").lower() == "true":
            continue
        if alanlar.get("NoDisplay", "").lower() == "true":
            continue
        if alanlar.get("Terminal", "").lower() == "true":
            continue
        komut = _komut_coz(alanlar.get("Exec", ""))
        if not komut:
            continue
        uygulamalar.append(
            Uygulama(
                kimlik=dosya.name,
                ad=alanlar.get("Name") or dosya.stem,
                ikon=ikon_bul(alanlar.get("Icon", "")),
                komut=komut,
            )
        )
    uygulamalar.sort(key=lambda u: u.ad.casefold())
    return uygulamalar


def _onbellek_oku() -> list[Uygulama] | None:
    try:
        veri = json.loads(onbellek_yolu().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if veri.get("surum") != _ONBELLEK_SURUM:
        return None
    try:
        return [Uygulama(**kayit) for kayit in veri["uygulamalar"]]
    except (KeyError, TypeError, ValueError):
        return None


def _onbellek_yaz(uygulamalar: list[Uygulama]) -> None:
    yol = onbellek_yolu()
    try:
        yol.parent.mkdir(parents=True, exist_ok=True)
        veri = {"surum": _ONBELLEK_SURUM, "uygulamalar": [asdict(u) for u in uygulamalar]}
        yol.write_text(json.dumps(veri, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        pass


def tara(hedef_ikon_boyutu: int = 56) -> list[Uygulama]:
    """Onbellekten okur; yoksa .desktop dosyalarini tarayip onbellege yazar."""
    onbellek = _onbellek_oku()
    if onbellek is not None:
        return onbellek
    uygulamalar = _tara_yavas()
    if uygulamalar:
        _onbellek_yaz(uygulamalar)
    return uygulamalar


def onerilen_uygulamalar(mevcut: list[Uygulama]) -> list[Uygulama]:
    """ONERILEN listesini cozer: ikonu bulunmayan uygulama listeye girmez."""
    indeks = {u.kimlik: u for u in mevcut}
    sonuc: list[Uygulama] = []
    for kimlik, ikon_adi, komutlar in ONERILEN:
        uygulama = indeks.get(kimlik)
        if uygulama is None:
            uygulama = Uygulama(kimlik=kimlik, ad=kimlik.removesuffix(".desktop"))
        if not uygulama.ikon:
            uygulama.ikon = ikon_bul(ikon_adi)
        if not uygulama.komut:
            for ad in komutlar:
                yol = shutil.which(ad)
                if yol:
                    uygulama.komut = [yol]
                    break
        if uygulama.ikon and uygulama.ikon not in {u.ikon for u in sonuc}:
            sonuc.append(uygulama)
    return sonuc


def varsayilan_secim(uygulamalar: list[Uygulama], adet: int = 12) -> list[str]:
    """Oncelikli ve ikonu cozulen uygulamalar; harf kutusu asla secilmez."""
    indeks = {u.kimlik: u for u in uygulamalar}
    secili = [k for k, _, _ in ONERILEN if k in indeks and indeks[k].ikon]
    kalan = [u for u in uygulamalar if u.kimlik not in secili and u.ikon]
    return (secili + [u.kimlik for u in kalan])[:adet]


def secilenler(uygulamalar: list[Uygulama], sabitlenen: list[str], adet: int = 12) -> list[Uygulama]:
    """sabitlenen kimliklerini korur; ikonsuz veya eksikse varsayilana duser."""
    indeks = {u.kimlik: u for u in uygulamalar}
    secili = [indeks[k] for k in sabitlenen if k in indeks and indeks[k].ikon]
    if len(secili) < _EN_AZ_IKON:
        return uygulamalar[:adet]
    return secili[:adet]


def baslat(uygulama: Uygulama) -> subprocess.Popen | None:
    if not uygulama.komut:
        return None
    try:
        return subprocess.Popen(
            uygulama.komut,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":99")},
        )
    except (OSError, ValueError):
        return None
