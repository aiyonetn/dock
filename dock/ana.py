"""Dock penceresi, arka plan yakalama ve otomatik gizlenme."""
from __future__ import annotations

import os
import subprocess
import threading
from hashlib import sha1
import time
from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation,
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
from PySide6.QtGui import QColor, QCursor, QFont, QFontDatabase, QImage, QPainter, QPainterPath
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from . import ayarlar, ikon, tema, x11
from .limit_model import LimitModel, LimitYonetici
from .muzik import MuzikModel
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
_PENCERE_UST_PAY = 340
# Yatay pay: buyuyen ikonlar komsularini itince panel genisler, kirpilma olmaz.
_PENCERE_YAN_PAY = 120


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
    kartKonum = Signal(int, int, int, int)
    muzikIstendi = Signal()
    muzikKonum = Signal(int, int, int, int)
    panelGenislik = Signal(int, int)

    def __init__(self, model: IkonModel, uygulamalar: list[Uygulama]) -> None:
        super().__init__()
        self.model = model
        self.uygulamalar = uygulamalar
        self.surecler: dict[int, list[subprocess.Popen]] = {}

    @Slot(int, int, int, int)
    def kart_konumu(self, x: int, y: int, gen: int, yuk: int) -> None:
        self.kartKonum.emit(x, y, gen, yuk)

    @Slot(int, int, int, int)
    def muzik_konumu(self, x: int, y: int, gen: int, yuk: int) -> None:
        self.muzikKonum.emit(x, y, gen, yuk)

    @Slot(int, int)
    def panel_genislik(self, gen: int, x: int) -> None:
        self.panelGenislik.emit(gen, x)

    @Slot(int)
    def tikla(self, indeks: int) -> None:
        if not 0 <= indeks < len(self.uygulamalar):
            return
        uygulama = self.uygulamalar[indeks]
        if uygulama.kimlik == "ai-limit.desktop":
            self.kartIstendi.emit()
            return
        if uygulama.kimlik == "muzik.desktop":
            self.muzikIstendi.emit()
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
    pencereDurum = Signal(bool)

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
        self.kopru.kartKapat.connect(self._kartlari_kapat)
        self.kopru.kartKonum.connect(self._kart_konum_guncelle)
        self.kopru.muzikIstendi.connect(self._muzik_degistir)
        self.kopru.muzikKonum.connect(self._muzik_konum_guncelle)
        self.kopru.panelGenislik.connect(self._panel_genislik_guncelle)
        self.muzik_model = MuzikModel(self)
        self.limit_model = LimitModel(self)
        self.limit_yonetici = LimitYonetici(self.limit_model, self)
        self._kart_bekle = False
        self.limit_yonetici.veriHazir.connect(self._ilk_limit_karti)
        self.saglayici = ArkaplanSaglayici()
        self._sayac = 0
        self._kart_sayac = 0
        self._kart_hash = ""
        self._kart_anahtar = None
        self._muzik_sayac = 0
        self._muzik_hash = ""
        self._muzik_anahtar = None
        self._tam_surum = 0
        self._muzik_rect: tuple[int, int, int, int] | None = None
        self._kart_rect: tuple[int, int, int, int] | None = None
        self._tam: QImage | None = None
        self._gorunur = False
        self._son_icerde = time.monotonic()
        self._grab_sayisi = 0
        self._anim_grab = 0
        self._pencere_mesgul = False
        self.pencereDurum.connect(self._pencere_guncelle)
        self._anim_atlandi = 0
        self._grab_log = None
        if os.environ.get("DOCK_GRAB_LOG"):
            try:
                self._grab_log = open(os.environ["DOCK_GRAB_LOG"], "a", buffering=1)
            except OSError:
                self._grab_log = None

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
        baglam.setContextProperty("muzikModel", self.muzik_model)
        baglam.setContextProperty("ikonSayisi", len(self.uygulamalar))
        baglam.setContextProperty("_pencereSol", self._x)
        baglam.setContextProperty("_ekranGenislik", self._ekran.width())
        baglam.setContextProperty(
            "yaricaplar",
            {
                "panel": tema.PANEL_YARICAP,
                "kart": tema.KART_YARICAP,
                "kartKapak": tema.KART_KAPAK_YARICAP,
                "ikonKapak": round(64 * 0.8 * tema.IKON_KAPAK_ORAN),
            },
        )
        baglam.setContextProperty(
            "yerTutucu", QUrl.fromLocalFile(str(KOK / "assets" / "ikon-yok.svg")).toString()
        )
        # Golge gorseli: her karede blur yerine tek dokulu dikdortgen.
        self.saglayici.goruntuler["golge"] = self._golge_uret(
            self._taban_panel_genislik + 40, self._panel_yukseklik + 40, 6, 20, 20
        )
        baglam.setContextProperty("golgeUrl", "image://arkaplan/golge")
        self.saglayici.goruntuler["kartGolge"] = self._golge_uret(340, 248, 7, 10, 14)
        self.saglayici.goruntuler["muzikGolge"] = self._golge_uret(340, 230, 7, 10, 14)
        self.gorunum.setSource(QUrl.fromLocalFile(str(KOK / "qml" / "Dock.qml")))
        if self.gorunum.status() == QQuickWidget.Error:
            hatalar = " | ".join(h.toString() for h in self.gorunum.errors())
            raise RuntimeError(f"QML yuklenemedi: {hatalar}")

    def _zamanlayicilari_kur(self) -> None:
        self._fare_zaman = QTimer(self)
        self._fare_zaman.setInterval(50)
        self._fare_zaman.timeout.connect(self._fare_denetle)
        self._fare_zaman.start()

        self._arkaplan_zaman = QTimer(self)
        self._arkaplan_zaman.setInterval(1000)
        self._arkaplan_zaman.timeout.connect(self._arkaplan_tazele)
        self._arkaplan_zaman.start()

        self._kart_zaman = QTimer(self)
        self._kart_zaman.setInterval(500)
        self._kart_zaman.timeout.connect(self._kart_arkaplan_yenile)

        self._muzik_zaman = QTimer(self)
        self._muzik_zaman.setInterval(500)
        self._muzik_zaman.timeout.connect(self._muzik_arkaplan_yenile)

        self._surec_zaman = QTimer(self)
        self._surec_zaman.setInterval(1500)
        self._surec_zaman.timeout.connect(self._acik_pencereleri_tazele)
        self._surec_zaman.start()
        self._acik_pencereleri_tazele()

        if os.environ.get("DOCK_LATENCY_LOG"):
            self._lat_son = time.monotonic()
            self._lat_dosya = open(os.environ["DOCK_LATENCY_LOG"], "a", buffering=1)
            self._lat_zaman = QTimer(self)
            self._lat_zaman.setInterval(50)
            def _lat():
                simdi = time.monotonic()
                self._lat_dosya.write(f"{(simdi - self._lat_son) * 1000:.1f}\n")
                self._lat_son = simdi
            self._lat_zaman.timeout.connect(_lat)
            self._lat_zaman.start()

        self._animasyon = QPropertyAnimation(self, b"pos", self)
        self._animasyon.setEasingCurve(QEasingCurve.OutCubic)

    @Slot(object)
    def _ilk_limit_karti(self, veri: dict) -> None:
        # KANIT/otomasyon: DOCK_KART=limit ise ilk veri gelince karti ac.
        if os.environ.get("DOCK_KART") == "limit" and not self._kart_bekle:
            self._kart_bekle = True
            self._kart_ayarla(True)

    def _kartlari_kapat(self) -> None:
        self._kart_ayarla(False)
        self._muzik_ayarla(False)

    def _kart_ayarla(self, acik: bool) -> None:
        if acik:
            self._muzik_ayarla(False)
        kok = self.gorunum.rootObject()
        if kok is not None:
            kok.setProperty("kartAcik", acik)
        zaman = getattr(self, "_kart_zaman", None)
        if acik:
            self._kart_arkaplan_yenile()
            if zaman is not None:
                zaman.start()
        elif zaman is not None:
            zaman.stop()
        self._giris_maskesi_uygula()

    @Slot(int, int, int, int)
    def _kart_konum_guncelle(self, x: int, y: int, gen: int, yuk: int) -> None:
        self._kart_rect = (x, y, gen, yuk)
        self._giris_maskesi_uygula()
        zaman = getattr(self, "_kart_zaman", None)
        if zaman is not None and zaman.isActive():
            self._kart_arkaplan_yenile()

    def _muzik_degistir(self) -> None:
        kok = self.gorunum.rootObject()
        if kok is not None:
            self._muzik_ayarla(not bool(kok.property("muzikAcik")))

    def _muzik_ayarla(self, acik: bool) -> None:
        if acik:
            self._kart_ayarla(False)
        kok = self.gorunum.rootObject()
        if kok is not None:
            kok.setProperty("muzikAcik", acik)
        self.muzik_model.ui_aktif_ayarla(acik)
        zaman = getattr(self, "_muzik_zaman", None)
        if acik:
            self._muzik_arkaplan_yenile()
            if zaman is not None:
                zaman.start()
        elif zaman is not None:
            zaman.stop()
        self._giris_maskesi_uygula()

    @Slot(int, int, int, int)
    def _muzik_konum_guncelle(self, x: int, y: int, gen: int, yuk: int) -> None:
        self._muzik_rect = (x, y, gen, yuk)
        self._giris_maskesi_uygula()
        zaman = getattr(self, "_muzik_zaman", None)
        if zaman is not None and zaman.isActive():
            self._muzik_arkaplan_yenile()

    def _kart_degistir(self) -> None:
        kok = self.gorunum.rootObject()
        if kok is not None:
            self._kart_ayarla(not bool(kok.property("kartAcik")))

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
        self._giris_maskesi_uygula()

    def _acik_pencereleri_tazele(self) -> None:
        """Chrome acik mi? Sorgu ayri thread'de; UI beklemez."""
        if self._pencere_mesgul:
            return
        self._pencere_mesgul = True
        threading.Thread(target=self._pencere_oku, daemon=True).start()

    def _pencere_oku(self) -> None:
        acik = False
        try:
            cikti = subprocess.run(
                ["wmctrl", "-l"], capture_output=True, text=True, timeout=1.5
            ).stdout.casefold()
            acik = "chrome" in cikti
        except (OSError, subprocess.SubprocessError):
            pass
        if not acik:
            try:
                acik = subprocess.run(
                    ["pgrep", "-f", "google-chrome"],
                    capture_output=True,
                    timeout=1.0,
                ).returncode == 0
            except (OSError, subprocess.SubprocessError):
                acik = False
        self._pencere_mesgul = False
        self.pencereDurum.emit(acik)

    @Slot(bool)
    def _pencere_guncelle(self, acik: bool) -> None:
        for indeks, uygulama in enumerate(self.uygulamalar):
            if uygulama.kimlik.startswith("google-chrome"):
                self.model.calisti_ayarla(indeks, acik)

    def _giris_maskesi_uygula(self) -> None:
        bolgeler = [
            (self._panel_x, self._panel_y, self._taban_panel_genislik, self._panel_yukseklik)
        ]
        kok = self.gorunum.rootObject()
        if kok is not None and (
            bool(kok.property("kartAcik")) or bool(kok.property("muzikAcik"))
        ):
            bolgeler.append((0, 0, self._gen, self._panel_y))
        try:
            x11.giris_maskesi(int(self.winId()), bolgeler)
        except Exception:
            pass

    @Slot(int, int)
    def _panel_genislik_guncelle(self, gen: int, x: int) -> None:
        if self._tam is None:
            return
        gen = max(1, min(gen, self._tam.width() - max(0, x)))
        x = max(0, min(x, self._tam.width() - gen))
        parca = self._tam.copy(
            QRect(x, self._panel_y, gen, self._panel_yukseklik)
        )
        self.saglayici.goruntuler["panel"] = self._bulanik(parca)
        self._sayac += 1
        kok = self.gorunum.rootObject()
        if kok is not None:
            kok.setProperty("arkaplanPanel", f"image://arkaplan/panel?{self._sayac}")

    def _kaydir(self, y: int, sure: int) -> None:
        self._animasyon.stop()
        self._animasyon.setDuration(sure)
        self._animasyon.setStartValue(self.pos())
        self._animasyon.setEndValue(QPoint(self._x, y))
        self._animasyon.start()

    def goster(self) -> None:
        if self._gorunur:
            return
        # Gizlenme animasyonu surerken yakalama yok (hayalet olusmasin).
        if self._animasyon.state() != QAbstractAnimation.Running:
            self._arkaplan_yenile()
        elif self._grab_log:
            self._grab_log.write(
                f"{time.monotonic():.3f} goster-anim=1 grab={self._grab_sayisi}\n"
            )
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
    def _cam(resim: QImage, kat: int, alfa: int, yaricap: int, renk=None) -> QImage:
        """Ucuz blur + koyu ton + yuvarlatilmis kose (tek sefer)."""
        kucuk = resim.scaled(
            max(1, resim.width() // kat),
            max(1, resim.height() // kat),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        bulanik = kucuk.scaled(resim.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        boya = QPainter(bulanik)
        ton = QColor(10, 10, 10)
        if renk is not None and renk.isValid():
            ton = QColor(
                int(10 * 0.5 + renk.red() * 0.5),
                int(10 * 0.5 + renk.green() * 0.5),
                int(10 * 0.5 + renk.blue() * 0.5),
            )
        boya.fillRect(bulanik.rect(), QColor(ton.red(), ton.green(), ton.blue(), alfa))
        boya.end()
        return Dock._koseleri_yuvarlat(bulanik, yaricap)

    @staticmethod
    def _bulanik(resim: QImage, kat: int = 10) -> QImage:
        return Dock._cam(resim, kat, 150, 20)

    def _kart_arkaplan_yenile(self) -> None:
        if self._tam is None or self._kart_rect is None:
            return
        anahtar = (self._tam_surum, self._kart_rect)
        if anahtar == self._kart_anahtar:
            return
        self._kart_anahtar = anahtar
        x, y, gen, yuk = self._kart_rect
        x = max(0, min(x, self._tam.width() - gen))
        y = max(0, min(y, self._tam.height() - yuk))
        parca = self._tam.copy(QRect(x, y, gen, yuk))
        goruntu = self._cam(parca, 18, 102, 14, QColor(self.muzik_model.renk))
        ozet = sha1(bytes(goruntu.constBits())).hexdigest()
        if ozet == self._kart_hash:
            return
        self._kart_hash = ozet
        self.saglayici.goruntuler["kart"] = goruntu
        self._kart_sayac += 1
        kok = self.gorunum.rootObject()
        if kok is not None:
            kok.setProperty("kartKaynak", f"image://arkaplan/kart?{self._kart_sayac}")

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
    def _golge_uret(gen: int, yuk: int, kat: int = 6, ic: int = 0, yaricap: int = 20) -> QImage:
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
        boya.drawRoundedRect(ic, ic, gen - 2 * ic, yuk - 2 * ic, yaricap, yaricap)
        boya.end()
        kucuk = resim.scaled(
            max(2, gen // kat), max(2, yuk // kat), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        return kucuk.scaled(gen, yuk, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    def _muzik_arkaplan_yenile(self) -> None:
        if self._tam is None or self._muzik_rect is None:
            return
        anahtar = (self._tam_surum, self._muzik_rect, self.muzik_model.renk)
        if anahtar == self._muzik_anahtar:
            return
        self._muzik_anahtar = anahtar
        x, y, gen, yuk = self._muzik_rect
        x = max(0, min(x, self._tam.width() - gen))
        y = max(0, min(y, self._tam.height() - yuk))
        parca = self._tam.copy(QRect(x, y, gen, yuk))
        goruntu = self._cam(parca, 18, 102, 14, QColor(self.muzik_model.renk))
        ozet = sha1(bytes(goruntu.constBits())).hexdigest()
        if ozet == self._muzik_hash:
            return
        self._muzik_hash = ozet
        self.saglayici.goruntuler["muzikKart"] = goruntu
        self._muzik_sayac += 1
        kok = self.gorunum.rootObject()
        if kok is not None:
            kok.setProperty("muzikKaynak", f"image://arkaplan/muzikKart?{self._muzik_sayac}")

    def _arkaplan_tazele(self) -> None:
        # Gorunurken kendi penceremizi yakalamamak icin yalniz gizliyken
        # tazelenir; animasyon sirasinda hic yakalanmaz.
        if self._animasyon.state() == QAbstractAnimation.Running:
            self._anim_atlandi += 1
            if self._grab_log:
                self._grab_log.write(
                    f"{time.monotonic():.3f} anim=1 grab={self._grab_sayisi} atlandi={self._anim_atlandi}\n"
                )
            return
        if not self._gorunur:
            self._arkaplan_yakala()
            if self._grab_log:
                self._grab_log.write(
                    f"{time.monotonic():.3f} anim=0 grab={self._grab_sayisi}\n"
                )
        elif self._grab_log:
            self._grab_log.write(
                f"{time.monotonic():.3f} anim=0 gorunur=1 grab={self._grab_sayisi}\n"
            )

    def _arkaplan_yenile(self) -> None:
        """Pencere gizliyken yakalar (goster() oncesi)."""
        if self._gorunur:
            return
        self._arkaplan_yakala()

    def _arkaplan_yakala(self) -> None:
        kok = self.gorunum.rootObject()
        if kok is None:
            return
        ekran = self.screen()
        if ekran is None:
            return
        resim = ekran.grabWindow(
            0,
            max(0, self._x),
            self._y_gorunur,
            min(self._gen, self._ekran.width()),
            self._yuk,
        )
        if resim.isNull():
            return
        self._grab_sayisi += 1
        kaynak = resim.toImage().convertToFormat(QImage.Format_RGBA8888)
        if kaynak.width() == self._gen:
            tam = kaynak
        else:
            tam = QImage(self._gen, self._yuk, QImage.Format_RGBA8888)
            tam.fill(QColor(0, 0, 0, 255))
            boya = QPainter(tam)
            boya.drawImage(-self._x + max(0, self._x), 0, kaynak)
            boya.end()
        self._tam = tam
        self._tam_surum += 1
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


def _fontlari_yukle() -> str:
    aileler: dict[str, str] = {}
    for dosya in sorted((KOK / "assets" / "fonts").glob("*.ttf")):
        kimlik = QFontDatabase.addApplicationFont(str(dosya))
        if kimlik < 0:
            print(f"HATA: font yuklenemedi: {dosya.name}", flush=True)
            return ""
        for aile in QFontDatabase.applicationFontFamilies(kimlik):
            aileler[aile] = dosya.name
    if "Geist" not in aileler or "Geist Mono" not in aileler:
        print(f"HATA: Geist aileleri bulunamadi: {aileler}", flush=True)
        return ""
    QApplication.setFont(QFont("Geist", 11))
    return aileler["Geist"]


def calistir() -> int:
    uygulama = QApplication([])
    if not _fontlari_yukle():
        return 1
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
    muzik_ikon = KOK / "assets" / "muzik.svg"
    muzik_uygulama = Uygulama(kimlik="muzik.desktop", ad="Müzik", ikon=str(muzik_ikon))
    islenmis_muzik = ikon.hazirla(str(muzik_ikon))
    if islenmis_muzik:
        muzik_uygulama.ikon = islenmis_muzik
        secili.append(muzik_uygulama)
    ai_ikon = KOK / "assets" / "ai-limit.svg"
    ai_uygulama = Uygulama(kimlik="ai-limit.desktop", ad="AI Limit", ikon=str(ai_ikon))
    islenmis_ai = ikon.hazirla(str(ai_ikon))
    if islenmis_ai:
        ai_uygulama.ikon = islenmis_ai
        secili.append(ai_uygulama)

    pencere = Dock(ayar, secili)
    pencere.show()
    return uygulama.exec()
