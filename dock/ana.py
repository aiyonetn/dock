"""Dock penceresi, arka plan yakalama ve otomatik gizlenme."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QTimer,
    QUrl,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPainterPath
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from . import ayarlar, ikon
from .limit_model import LimitModel, LimitYonetici
from .model import IkonModel
from .uygulamalar import (
    Uygulama,
    baslat,
    onerilen_uygulamalar,
    secilenler,
    tara,
    varsayilan_secim,
)

KOK = Path(__file__).resolve().parent.parent

_ALAN_BOSLUK = 12
_YAN_BOSLUK = 16
_PANEL_YUKSEKLIK = 108
_PANEL_DIKEY_BOSLUK = 12
_ALT_PAY = 12
# Pencere opak: buyuyen ikonlar icin panel ustunde pay, golge icin altta 10 px.
# Kalan alan masaustu goruntusuyle doldurulur; saydamlik/compositor gerekmez.
_PENCERE_UST_PAY = 260
# Yatay pay: buyuyen ikonlar komsularini itince panel genisler, kirpilma olmaz.
_PENCERE_YAN_PAY = 80


class ArkaplanSaglayici(QQuickImageProvider):
    """QML'e panel arkasindan alinan ekran goruntusunu verir.

    "tam"   -> pencerenin tamami (masaustu ile dikissiz birlesir)
    "panel" -> panelin arkasindaki kirpilmis bolge (bulaniklastirilir)
    """

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)
        self.goruntuler: dict[str, QImage] = {}

    def requestImage(self, kimlik, boyut, istenen):  # noqa: N802 (Qt API)
        anahtar = kimlik.split("?", 1)[0]
        resim = self.goruntuler.get(anahtar)
        if resim is None or resim.isNull():
            return QImage()
        boyut.setWidth(resim.width())
        boyut.setHeight(resim.height())
        return resim


class Kopru(QObject):
    """QML'den gelen tiklama isteklerini isler."""

    kartIstendi = Signal()
    kartKapat = Signal()

    def __init__(self, model: IkonModel, uygulamalar: list[Uygulama]) -> None:
        super().__init__()
        self.model = model
        self.uygulamalar = uygulamalar
        self.surecler: dict[int, list[subprocess.Popen]] = {}

    @Slot(int)
    def tikla(self, indeks: int) -> None:
        if not 0 <= indeks < len(self.uygulamalar):
            return
        uygulama = self.uygulamalar[indeks]
        if uygulama.kimlik == "ai-limit.desktop":
            self.kartIstendi.emit()
            return
        self.kartKapat.emit()
        surec = baslat(uygulama)
        if surec is None:
            self.model.parlama_tetikle(indeks, "başlatılamadı")
            return
        self.surecler.setdefault(indeks, []).append(surec)
        self.model.calisti_ayarla(indeks, True)

    def durumlari_tazele(self) -> None:
        for indeks, liste in self.surecler.items():
            canli = [s for s in liste if s.poll() is None]
            self.surecler[indeks] = canli
            self.model.calisti_ayarla(indeks, bool(canli))


class Dock(QWidget):
    def __init__(self, ayar: dict, uygulamalar: list[Uygulama]) -> None:
        bayraklar = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        super().__init__(None, bayraklar)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle("Dock")

        self.ayar = ayar
        self.uygulamalar = uygulamalar
        self.model = IkonModel(uygulamalar, self)
        self.kopru = Kopru(self.model, uygulamalar)
        self.kopru.kartIstendi.connect(self._kart_degistir)
        self.kopru.kartKapat.connect(lambda: self._kart_ayarla(False))
        self.limit_model = LimitModel(self)
        self.limit_yonetici = LimitYonetici(self.limit_model, self)
        self.saglayici = ArkaplanSaglayici()
        self._sayac = 0
        self._gorunur = False
        self._son_icerde = time.monotonic()

        self._olcu_hesapla()
        self._pencereleri_kur()
        self._arayuzu_kur()
        self._zamanlayicilari_kur()
        self._ilk_konum()

    # --- olculer -----------------------------------------------------------
    def _olcu_hesapla(self) -> None:
        ikon = int(self.ayar["iconSize"])
        buyutme = float(self.ayar["buyutme"])
        self._panel_yukseklik = _PANEL_YUKSEKLIK
        self._hucre_yukseklik = int(ikon * buyutme)
        taban = ikon * len(self.uygulamalar) + _ALAN_BOSLUK * max(0, len(self.uygulamalar) - 1)
        self._taban_panel_genislik = taban + 2 * _YAN_BOSLUK
        self._gen = self._taban_panel_genislik + 2 * _PENCERE_YAN_PAY
        self._yuk = self._panel_yukseklik + _ALT_PAY + _PENCERE_UST_PAY
        self._panel_x = _PENCERE_YAN_PAY
        self._panel_y = self._yuk - _ALT_PAY - self._panel_yukseklik

        ekran = QApplication.primaryScreen().geometry()
        self._ekran = ekran
        self._x = ekran.x() + (ekran.width() - self._gen) // 2
        # Pencere tabani ekran tabaninda; panel 10 px yukarida.
        self._y_gorunur = ekran.y() + ekran.height() - self._yuk
        self._y_gizli = ekran.y() + ekran.height()

    # --- pencere -----------------------------------------------------------
    def _pencereleri_kur(self) -> None:
        self.resize(self._gen, self._yuk)
        self.yerlesim = QVBoxLayout(self)
        self.yerlesim.setContentsMargins(0, 0, 0, 0)
        self.yerlesim.setSpacing(0)

        self.gorunum = QQuickWidget()
        self.gorunum.setClearColor(Qt.black)
        self.gorunum.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.yerlesim.addWidget(self.gorunum)

    def _arayuzu_kur(self) -> None:
        motor = self.gorunum.engine()
        motor.addImageProvider("arkaplan", self.saglayici)
        baglam = self.gorunum.rootContext()
        baglam.setContextProperty("kopru", self.kopru)
        baglam.setContextProperty("ayar", self.ayar)
        baglam.setContextProperty("ikonModel", self.model)
        baglam.setContextProperty("limitModel", self.limit_model)
        baglam.setContextProperty("ikonSayisi", len(self.uygulamalar))
        baglam.setContextProperty(
            "yerTutucu", QUrl.fromLocalFile(str(KOK / "assets" / "ikon-yok.svg")).toString()
        )
        # Golge gorseli: her karede blur yerine tek dokulu dikdortgen.
        self.saglayici.goruntuler["golge"] = self._golge_uret(
            self._taban_panel_genislik + 24, self._panel_yukseklik + 24
        )
        baglam.setContextProperty("golgeUrl", "image://arkaplan/golge")
        self.gorunum.setSource(QUrl.fromLocalFile(str(KOK / "qml" / "Dock.qml")))
        if self.gorunum.status() == QQuickWidget.Error:
            hatalar = " | ".join(h.toString() for h in self.gorunum.errors())
            raise RuntimeError(f"QML yuklenemedi: {hatalar}")

    def _zamanlayicilari_kur(self) -> None:
        self._fare_zaman = QTimer(self)
        self._fare_zaman.setInterval(50)
        self._fare_zaman.timeout.connect(self._fare_denetle)
        self._fare_zaman.start()

        self._surec_zaman = QTimer(self)
        self._surec_zaman.setInterval(1500)
        self._surec_zaman.timeout.connect(self._acik_pencereleri_tazele)
        self._surec_zaman.start()
        self._acik_pencereleri_tazele()

        self._animasyon = QPropertyAnimation(self, b"pos", self)
        self._animasyon.setEasingCurve(QEasingCurve.OutCubic)

    def _kart_ayarla(self, acik: bool) -> None:
        kok = self.gorunum.rootObject()
        if kok is not None:
            kok.setProperty("kartAcik", acik)

    def _kart_degistir(self) -> None:
        kok = self.gorunum.rootObject()
        if kok is not None:
            kok.setProperty("kartAcik", not bool(kok.property("kartAcik")))

    # --- konum / gorunurluk ------------------------------------------------
    def _ilk_konum(self) -> None:
        if self.ayar["autoHide"]:
            self.move(self._x, self._y_gizli)
            self.show()
            self._gorunur = False
        else:
            # Yakalama pencere gorunmeden once goster() icinde yapilir.
            self.move(self._x, self._y_gorunur)
            self.goster()
            self.show()

    def _acik_pencereleri_tazele(self) -> None:
        """Acik uygulama gostergesi: simdilik yalniz Chrome (wmctrl)."""
        acik = False
        try:
            cikti = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=1.5
            ).stdout.casefold()
            acik = "chrome" in cikti
        except (OSError, subprocess.SubprocessError):
            pass
        if not acik:
            # Pencere yoneticisi yoksa (Xvfb) surec adindan anla.
            try:
                acik = subprocess.run(
                    ["pgrep", "-f", "google-chrome"],
                    capture_output=True,
                    timeout=1.0,
                ).returncode == 0
            except (OSError, subprocess.SubprocessError):
                return
        for indeks, uygulama in enumerate(self.uygulamalar):
            if uygulama.kimlik.startswith("google-chrome"):
                self.model.calisti_ayarla(indeks, acik)

    def _kaydir(self, y: int, sure: int) -> None:
        self._animasyon.stop()
        self._animasyon.setDuration(sure)
        self._animasyon.setStartValue(self.pos())
        self._animasyon.setEndValue(QPoint(self._x, y))
        self._animasyon.start()

    def goster(self) -> None:
        if self._gorunur:
            return
        # Pencere hala gizliyken yakala: kendi icerigimizi cekmeyiz.
        self._arkaplan_yenile()
        self._gorunur = True
        self._son_icerde = time.monotonic()
        self._kaydir(self._y_gorunur, 200)

    def gizle(self) -> None:
        if not self._gorunur:
            return
        self._gorunur = False
        self._kaydir(self._y_gizli, 220)

    # --- arka plan ---------------------------------------------------------
    @staticmethod
    def _bulanik(resim: QImage, kat: int = 10) -> QImage:
        """Ucuz blur: kucult, sonra yumusak geri buyut."""
        kucuk = resim.scaled(
            max(1, resim.width() // kat),
            max(1, resim.height() // kat),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        bulanik = kucuk.scaled(resim.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return Dock._koseleri_yuvarlat(bulanik, 20)

    @staticmethod
    def _koseleri_yuvarlat(resim: QImage, yaricap: int) -> QImage:
        """Kose yuvarlatmayi goruntuye bir kez uygular.

        QML'de her karede MultiEffect/mask calistirmak yazilim render'da
        kare basina ~3-4 ms CPU yiyor; burada bir kez yapmak bedava.
        """
        resim = resim.convertToFormat(QImage.Format_RGBA8888)
        boya = QPainter(resim)
        boya.setRenderHint(QPainter.Antialiasing, True)
        boya.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        yol = QPainterPath()
        yol.addRoundedRect(0, 0, resim.width(), resim.height(), yaricap, yaricap)
        boya.fillPath(yol, Qt.black)
        boya.end()
        return resim

    @staticmethod
    def _golge_uret(gen: int, yuk: int, kat: int = 6) -> QImage:
        """Panel golgesini bir kez uretir (yuvarlat + ucuz blur).

        Onceden QML'de golge bir layer + MultiEffect idi ve panel genisligi
        her degistiginde yeniden isleniyordu.
        """
        resim = QImage(max(4, gen), max(4, yuk), QImage.Format_RGBA8888)
        resim.fill(Qt.transparent)
        boya = QPainter(resim)
        boya.setRenderHint(QPainter.Antialiasing, True)
        boya.setPen(Qt.NoPen)
        boya.setBrush(QColor(0, 0, 0, 150))
        boya.drawRoundedRect(0, 0, gen, yuk, 20, 20)
        boya.end()
        kucuk = resim.scaled(
            max(2, gen // kat), max(2, yuk // kat), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        return kucuk.scaled(gen, yuk, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    def _arkaplan_yenile(self) -> None:
        """Masaustunu yakalar; yalnizca goster() cagirir (QTimer yok)."""
        if self._gorunur and self.geometry().intersects(
            QRect(self._x, self._y_gorunur, self._gen, self._yuk)
        ):
            return
        kok = self.gorunum.rootObject()
        if kok is None:
            return
        ekran = self.screen()
        if ekran is None:
            return
        resim = ekran.grabWindow(0, self._x, self._y_gorunur, self._gen, self._yuk)
        if resim.isNull():
            return
        tam = resim.toImage().convertToFormat(QImage.Format_RGBA8888)
        panel = tam.copy(
            QRect(
                self._panel_x,
                self._panel_y,
                self._taban_panel_genislik,
                self._panel_yukseklik,
            )
        )
        # "golge" anahtarini koru: sozlugu tumden degistirmek gorseli siler.
        self.saglayici.goruntuler["tam"] = tam
        self.saglayici.goruntuler["panel"] = self._bulanik(panel)
        self._sayac += 1
        kok.setProperty("arkaplanTam", f"image://arkaplan/tam?{self._sayac}")
        kok.setProperty("arkaplanPanel", f"image://arkaplan/panel?{self._sayac}")

    # --- otomatik gizlenme -------------------------------------------------
    def _fare_denetle(self) -> None:
        if not self.ayar["autoHide"]:
            return
        imlec = QCursor.pos()
        alt_sinir = self._ekran.y() + self._ekran.height() - 2
        alt_kenarda = imlec.y() >= alt_sinir
        if not self._gorunur:
            if alt_kenarda:
                self.goster()
            return
        if alt_kenarda or self.geometry().contains(imlec):
            self._son_icerde = time.monotonic()
            return
        if time.monotonic() - self._son_icerde >= 0.8:
            self.gizle()


def calistir() -> int:
    uygulama = QApplication([])
    uygulama.setApplicationName("dock")
    uygulama.setQuitOnLastWindowClosed(True)

    tarama = tara(56)
    hazir: list[Uygulama] = []
    for aday in onerilen_uygulamalar(tarama):
        islenmis = ikon.hazirla(aday.ikon)
        if islenmis:
            aday.ikon = islenmis
            hazir.append(aday)
    onerilen = hazir
    if len(onerilen) < 8:
        print(
            f"HATA: yalnizca {len(onerilen)} seffaf ikon bulundu, en az 8 gerekli",
            flush=True,
        )
        return 1
    havuz = onerilen
    varsayilan = varsayilan_secim(onerilen)
    ayar = ayarlar.yukle(varsayilan)
    gecerli = [k for k in ayar["sabitlenen"] if k in {u.kimlik for u in havuz}]
    if len(gecerli) < 8:
        ayar["sabitlenen"] = list(varsayilan)
        ayarlar.kaydet(ayar)
    secili = secilenler(havuz, ayar["sabitlenen"])
    if not secili:
        print("HATA: sabitlenen uygulamalarin hicbiri bulunamadi", flush=True)
        return 1
    ai_ikon = KOK / "assets" / "ai-limit.svg"
    ai_uygulama = Uygulama(kimlik="ai-limit.desktop", ad="AI Limit", ikon=str(ai_ikon))
    islenmis_ai = ikon.hazirla(str(ai_ikon))
    if islenmis_ai:
        ai_uygulama.ikon = islenmis_ai
        secili.append(ai_uygulama)

    pencere = Dock(ayar, secili)
    pencere.show()
    return uygulama.exec()
