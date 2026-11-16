"""Ikon kaynaklarini seffaf, kirpilmis 256 px PNG'lere cevirir."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

_BOYUT = 256
_ALFA_ESIGI = 8
_KOSE_FARKI = 12
_RENK_TOLERANS = 20
_HALE_ALFA = 24
_SON = 224  # 56 px kutunun 4x'i
_IC = 160  # 8 px ic bosluk -> 40 px icerik (4x)


def _onbellek_dizini() -> Path:
    kok = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(kok) / "dock" / "islenmis"


def _svg_oku(yol: Path) -> QImage:
    renderer = QSvgRenderer(str(yol))
    resim = QImage(_BOYUT, _BOYUT, QImage.Format_ARGB32)
    resim.fill(Qt.transparent)
    resim.setDevicePixelRatio(1.0)
    boyaci = QPainter(resim)
    boyaci.setRenderHint(QPainter.Antialiasing, True)
    boyaci.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(boyaci)
    boyaci.end()
    return resim


def _png_oku(yol: Path) -> QImage:
    resim = QImage(str(yol))
    if resim.isNull():
        return resim
    if resim.width() < 256 or resim.height() < 256:
        resim = resim.scaled(
            _BOYUT, _BOYUT, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
    return resim.convertToFormat(QImage.Format_ARGB32)


def _kose_rengi(resim: QImage) -> tuple[int, int, int] | None:
    """Dort kose de opak ve ayni renkteyse o rengi dondurur."""
    gen, yuk = resim.width(), resim.height()
    koseler = [
        resim.pixelColor(0, 0),
        resim.pixelColor(gen - 1, 0),
        resim.pixelColor(0, yuk - 1),
        resim.pixelColor(gen - 1, yuk - 1),
    ]
    if any(k.alpha() < 250 for k in koseler):
        return None
    r0, g0, b0 = koseler[0].red(), koseler[0].green(), koseler[0].blue()
    for k in koseler[1:]:
        if max(abs(k.red() - r0), abs(k.green() - g0), abs(k.blue() - b0)) > _KOSE_FARKI:
            return None
    return r0, g0, b0


def _arka_plani_temizle(resim: QImage) -> QImage:
    """Tekduze kose rengini toleransla seffafa cevirir."""
    renk = _kose_rengi(resim)
    if renk is None:
        return resim
    r0, g0, b0 = renk
    gen, yuk = resim.width(), resim.height()
    for y in range(yuk):
        for x in range(gen):
            renk_px = resim.pixelColor(x, y)
            if renk_px.alpha() == 0:
                continue
            if (
                abs(renk_px.red() - r0) <= _RENK_TOLERANS
                and abs(renk_px.green() - g0) <= _RENK_TOLERANS
                and abs(renk_px.blue() - b0) <= _RENK_TOLERANS
            ):
                renk_px.setAlpha(0)
                resim.setPixelColor(x, y, renk_px)
    return resim


def _hale_temizle(resim: QImage) -> QImage:
    """Kenarda kalan cok dusuk alfali pikselleri sifirla."""
    gen, yuk = resim.width(), resim.height()
    for y in range(yuk):
        for x in range(gen):
            renk = resim.pixelColor(x, y)
            if 0 < renk.alpha() <= _HALE_ALFA:
                renk.setAlpha(0)
                resim.setPixelColor(x, y, renk)
    return resim


def _alfa_sinirlari(resim: QImage) -> tuple[int, int, int, int] | None:
    sol, ust, sag, alt = resim.width(), resim.height(), -1, -1
    for y in range(resim.height()):
        for x in range(resim.width()):
            if resim.pixelColor(x, y).alpha() > _ALFA_ESIGI:
                sol = min(sol, x)
                ust = min(ust, y)
                sag = max(sag, x)
                alt = max(alt, y)
    if sag < sol or alt < ust:
        return None
    return sol, ust, sag + 1, alt + 1


def _plaka_var(resim: QImage) -> bool:
    gen, yuk = resim.width(), resim.height()
    return all(
        resim.pixelColor(x, y).alpha() > 200
        for x, y in [(0, 0), (gen - 1, 0), (0, yuk - 1), (gen - 1, yuk - 1)]
    )


def _son_goruntu(kirpik: QImage) -> QImage:
    """Kirpilmis ikonu 56 px kutuya (8 px bosluk) yerlestirir, golge ekler."""
    olcek = min(_IC / max(1, kirpik.width()), _IC / max(1, kirpik.height()))
    yeni = kirpik.scaled(
        max(1, round(kirpik.width() * olcek)),
        max(1, round(kirpik.height() * olcek)),
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    zemin = QImage(_SON, _SON, QImage.Format_ARGB32)
    zemin.fill(Qt.transparent)
    boyaci = QPainter(zemin)
    boyaci.drawImage((_SON - yeni.width()) // 2, (_SON - yeni.height()) // 2, yeni)
    boyaci.end()

    # 1 px asagi, 6 px blur, %35 siyah golge.
    golge = QImage(_SON, _SON, QImage.Format_ARGB32)
    golge.fill(Qt.transparent)
    boyaci = QPainter(golge)
    boyaci.setOpacity(0.35)
    boyaci.drawImage(0, 4, zemin)
    boyaci.end()
    # Rengi siyaha cevir, alfayi koru.
    boyaci = QPainter(golge)
    boyaci.setCompositionMode(QPainter.CompositionMode_SourceIn)
    boyaci.fillRect(golge.rect(), Qt.black)
    boyaci.end()
    golge = golge.scaled(
        _SON // 8, _SON // 8, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
    ).scaled(_SON, _SON, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    sonuc = QImage(_SON, _SON, QImage.Format_ARGB32)
    sonuc.fill(Qt.transparent)
    boyaci = QPainter(sonuc)
    boyaci.drawImage(0, 0, golge)
    boyaci.drawImage(0, 0, zemin)
    boyaci.end()
    return sonuc


def hazirla(kaynak: str) -> str:
    """Ikonu seffaf, cevresi kirpilmis PNG olarak onbellege yazar."""
    if not kaynak:
        return ""
    yol = Path(kaynak)
    try:
        damga = f"{yol.stat().st_mtime_ns}:{yol.stat().st_size}"
    except OSError:
        return ""
    anahtar = hashlib.sha1(f"{yol}:{damga}:5".encode()).hexdigest()[:20]
    hedef = _onbellek_dizini() / f"{anahtar}.png"
    if hedef.is_file():
        return str(hedef)

    uzanti = yol.suffix.lower()
    if uzanti == ".svg":
        resim = _svg_oku(yol)
    else:
        resim = _png_oku(yol)
    if resim.isNull():
        return ""
    if uzanti != ".svg":
        resim = _hale_temizle(_arka_plani_temizle(resim))
    if _plaka_var(resim):
        return ""
    sinirlar = _alfa_sinirlari(resim)
    if sinirlar is None:
        return ""
    kirpik = _son_goruntu(resim.copy(*sinirlar))

    try:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        tampon = QBuffer()
        tampon.open(QIODevice.WriteOnly)
        kirpik.save(tampon, "PNG")
        hedef.write_bytes(bytes(tampon.data()))
    except OSError:
        return ""
    return str(hedef)
