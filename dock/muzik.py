"""Simdi caliyor: MPRIS (QtDBus) veya demo oynatici."""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import urlopen

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot, Qt
from PySide6.QtDBus import QDBusConnection, QDBusInterface
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath

_MPRIS_ON_EK = "org.mpris.MediaPlayer2."
_DEMO_BASLIK = "Midnight Drive"
_DEMO_SANATCI = "Demo Player"
_DEMO_SURE = 228_000


class MuzikModel(QObject):
    degisti = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._baslik = _DEMO_BASLIK
        self._sanatci = _DEMO_SANATCI
        self._album = "Single"
        self._kapak = self._demo_kapak()
        self._renk = self._renk_hesapla(self._kapak)
        self._sure = _DEMO_SURE
        self._konum = 72_000
        self._caliyor = True
        self._demo = True
        self._iface: QDBusInterface | None = None
        self._servis = ""
        self._track = ""
        self._deneme = 0
        self._ui_sayac = 0
        self._ui_aktif = False
        self._zaman = QTimer(self)
        self._zaman.setInterval(1000)
        self._zaman.timeout.connect(self._tik)
        self._zaman.start()
        self._mpris_ara()

    def _kapak_dizini(self) -> Path:
        yol = Path.home() / ".cache" / "dock" / "kapak"
        yol.mkdir(parents=True, exist_ok=True)
        return yol

    @staticmethod
    def _yuvarlat(resim: QImage, yaricap: int) -> QImage:
        resim = resim.convertToFormat(QImage.Format_ARGB32)
        boya = QPainter(resim)
        boya.setRenderHint(QPainter.Antialiasing, True)
        boya.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        yol = QPainterPath()
        yol.addRoundedRect(0, 0, resim.width(), resim.height(), yaricap, yaricap)
        boya.fillPath(yol, Qt.black)
        boya.end()
        return resim

    def _demo_kapak(self) -> str:
        hedef = self._kapak_dizini() / "demo.png"
        if hedef.is_file():
            return str(hedef)
        resim = QImage(176, 176, QImage.Format_ARGB32)
        boya = QPainter(resim)
        boya.setRenderHint(QPainter.Antialiasing, True)
        gradyan = QLinearGradient(0, 0, 176, 176)
        gradyan.setColorAt(0.0, QColor("#7c5cff"))
        gradyan.setColorAt(1.0, QColor("#35b6ff"))
        boya.fillRect(0, 0, 176, 176, gradyan)
        boya.setPen(Qt.NoPen)
        boya.setBrush(QColor("#ffffff"))
        boya.drawEllipse(58, 108, 26, 22)
        boya.drawRect(79, 46, 7, 70)
        boya.setBrush(QColor("#ffffff"))
        yol = QPainterPath()
        yol.moveTo(86, 46)
        yol.quadTo(122, 52, 128, 82)
        yol.lineTo(117, 76)
        yol.quadTo(108, 60, 86, 60)
        boya.drawPath(yol)
        boya.end()
        self._yuvarlat(resim, 24).save(str(hedef))
        return str(hedef)

    def _renk_hesapla(self, yol: str) -> str:
        resim = QImage(yol)
        if resim.isNull():
            return "#0A0A0A"
        r = g = b = n = 0
        for y in range(0, resim.height(), 8):
            for x in range(0, resim.width(), 8):
                renk = resim.pixelColor(x, y)
                r += renk.red(); g += renk.green(); b += renk.blue(); n += 1
        if n == 0:
            return "#0A0A0A"
        return "#%02x%02x%02x" % (
            int(r / n * 0.42), int(g / n * 0.42), int(b / n * 0.42)
        )

    def _kapak_hazirla(self, url: str) -> str:
        if not url:
            return self._demo_kapak()
        if url.startswith("file://"):
            url = url[7:]
        if url.startswith("http://") or url.startswith("https://"):
            ad = hashlib.sha1(url.encode()).hexdigest()[:16]
            hedef = self._kapak_dizini() / f"{ad}.png"
            if hedef.is_file():
                return str(hedef)
            try:
                veri = urlopen(url, timeout=8).read()
                gecici = hedef.with_suffix(".tmp")
                gecici.write_bytes(veri)
                resim = QImage(str(gecici))
                gecici.unlink(missing_ok=True)
            except Exception as hata:
                print("kapak indirilemedi:", hata, flush=True)
                return self._demo_kapak()
        else:
            resim = QImage(url)
            if resim.isNull():
                return self._demo_kapak()
            hedef = self._kapak_dizini() / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".png")
        if resim.isNull():
            return self._demo_kapak()
        taraf = min(resim.width(), resim.height())
        resim = resim.copy(
            (resim.width() - taraf) // 2, (resim.height() - taraf) // 2, taraf, taraf
        ).scaled(176, 176, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self._yuvarlat(resim, 24).save(str(hedef))
        return str(hedef)

    # --- ozellikler --------------------------------------------------------
    def _oku(self, ad: str):
        return getattr(self, "_" + ad)

    def _yaz(self, ad: str, deger) -> None:
        if getattr(self, "_" + ad) != deger:
            setattr(self, "_" + ad, deger)
            self.degisti.emit()

    baslik = Property(str, lambda s: s._baslik, notify=degisti)
    sanatci = Property(str, lambda s: s._sanatci, notify=degisti)
    album = Property(str, lambda s: s._album, notify=degisti)
    kapak = Property(str, lambda s: s._kapak, notify=degisti)
    renk = Property(str, lambda s: s._renk, notify=degisti)
    sureMs = Property(int, lambda s: s._sure, notify=degisti)
    konumMs = Property(int, lambda s: s._konum, notify=degisti)
    caliyor = Property(bool, lambda s: s._caliyor, notify=degisti)
    demo = Property(bool, lambda s: s._demo, notify=degisti)

    # --- MPRIS -------------------------------------------------------------
    def _mpris_ara(self) -> None:
        if self._iface is not None:
            return
        try:
            arayuz = QDBusConnection.sessionBus().interface()
            adlar = arayuz.registeredServiceNames().value()
        except Exception:
            return
        adaylar = []
        for ad in adlar:
            if not ad.startswith(_MPRIS_ON_EK):
                continue
            iface = QDBusInterface(
                ad,
                "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player",
                QDBusConnection.sessionBus(),
            )
            if iface.isValid():
                durum = str(iface.property("PlaybackStatus") or "")
                adaylar.append((iface, ad, durum))
        if not adaylar:
            return
        calan = next((a for a in adaylar if a[2] == "Playing"), adaylar[-1])
        self._iface = calan[0]
        self._servis = calan[1]
        self._demo = False
        self._mpris_oku()

    @Slot(str, str, str)
    def isim_degisti(self, ad: str, eski: str, yeni: str) -> None:
        if ad == self._servis and not yeni:
            self._iface = None
            self._servis = ""
            self._demo = True
            self._baslik = _DEMO_BASLIK
            self._sanatci = _DEMO_SANATCI
            self._album = "Demo"
            self._kapak = self._demo_kapak()
            self._renk = self._renk_hesapla(self._kapak)
            self._sure = _DEMO_SURE
            self._konum = 0
            self._caliyor = True
            self.degisti.emit()
        elif not self._servis:
            self._mpris_ara()

    def _mpris_oku(self) -> None:
        if self._iface is None:
            return
        try:
            meta = self._iface.property("Metadata") or {}
            durum = str(self._iface.property("PlaybackStatus") or "Paused")
            konum = int(self._iface.property("Position") or 0)
        except Exception:
            self._iface = None
            self._demo = True
            return
        sanatci = meta.get("xesam:artist") or ""
        if isinstance(sanatci, (list, tuple)):
            sanatci = ", ".join(str(s) for s in sanatci)
        self._baslik = str(meta.get("xesam:title") or "")
        self._sanatci = str(sanatci)
        self._album = str(meta.get("xesam:album") or "")
        self._kapak = self._kapak_hazirla(str(meta.get("mpris:artUrl") or ""))
        self._renk = self._renk_hesapla(self._kapak)
        self._track = meta.get("mpris:trackid") or ""
        self._sure = int(int(meta.get("mpris:length") or 0) / 1000)
        self._konum = int(konum / 1000)
        self._caliyor = durum == "Playing"
        self.degisti.emit()

    # --- demo / tik --------------------------------------------------------
    def _tik(self) -> None:
        if self._demo:
            self._deneme += 1
            if self._deneme % 10 == 0:
                self._mpris_ara()
                if not self._demo:
                    return
            if self._caliyor and self._konum < self._sure:
                self._konum = min(self._sure, self._konum + 1000)
                self._ui_sayac += 1
                # Ilerleme 1 sn'de bir; UI 2 sn'de bir cizilir (CPU).
                if self._ui_aktif and self._ui_sayac % 2 == 0:
                    self.degisti.emit()
            elif self._konum >= self._sure:
                self._caliyor = False
                self.degisti.emit()
        else:
            try:
                adlar = QDBusConnection.sessionBus().interface().registeredServiceNames().value()
            except Exception:
                adlar = []
            if self._servis not in adlar:
                self.isim_degisti(self._servis, self._servis, "")
            else:
                self._mpris_oku()

    @Slot(bool)
    def ui_aktif_ayarla(self, deger: bool) -> None:
        self._ui_aktif = deger
        if deger:
            self.degisti.emit()

    # --- dugmeler ----------------------------------------------------------
    @Slot(float)
    def ara(self, oran: float) -> None:
        oran = max(0.0, min(1.0, oran))
        if self._demo:
            self._konum = int(self._sure * oran)
            self.degisti.emit()
            return
        if self._iface is not None:
            try:
                self._iface.call("SetPosition", self._track, int(self._sure * oran * 1000))
            except Exception:
                pass
            self._mpris_oku()

    @Slot()
    def oynat_duraklat(self) -> None:
        if self._demo:
            self._caliyor = not self._caliyor
            self.degisti.emit()
            return
        if self._iface is not None:
            try:
                self._iface.call("PlayPause")
            except Exception:
                pass
            self._mpris_oku()

    @Slot()
    def ileri(self) -> None:
        if self._demo:
            self._konum = min(self._sure, self._konum + 15_000)
            self.degisti.emit()
            return
        if self._iface is not None:
            try:
                self._iface.call("Next")
            except Exception:
                pass
            self._mpris_oku()

    @Slot()
    def geri(self) -> None:
        if self._demo:
            self._konum = max(0, self._konum - 15_000)
            self.degisti.emit()
            return
        if self._iface is not None:
            try:
                self._iface.call("Previous")
            except Exception:
                pass
            self._mpris_oku()

    # QML camelCase takma adlar
    @Slot()
    def oynatDuraklat(self) -> None:
        self.oynat_duraklat()
