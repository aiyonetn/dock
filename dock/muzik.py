"""Simdi caliyor: MPRIS (QtDBus) veya demo oynatici."""
from __future__ import annotations

import base64
import hashlib
import re
import subprocess
import json
import threading
from pathlib import Path
import os
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
    kapakHazir = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._baslik = os.environ.get("DOCK_DEMO_TR") and "Şişli'de Öğle Güneşi · Çığlık" or _DEMO_BASLIK
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
        self._kapak_key = None
        self._islem_sayaci = 0
        self._kapak_bekliyor = False
        self.kapakHazir.connect(self._kapak_sonuc)
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
        hedef = self._kapak_dizini() / "demo-kare.png"
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
        resim.save(str(hedef))
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

    def _kapak_isle(self, url: str) -> tuple[str, str] | None:
        """Kapagi indir/coz, 176 px yuvarlak JPEG + renk JSON onbellege yaz."""
        self._islem_sayaci += 1
        gunluk = os.environ.get("DOCK_KAPAK_LOG")
        if gunluk:
            try:
                with open(gunluk, "a", encoding="utf-8") as dosya:
                    dosya.write(f"kapak-islem {self._islem_sayaci} {url}\n")
            except OSError:
                pass
        if not url:
            return None
        ad = hashlib.sha1(("v2:" + url).encode()).hexdigest()
        hedef = self._kapak_dizini() / f"{ad}.jpg"
        renk_yolu = self._kapak_dizini() / f"{ad}.json"
        if hedef.is_file() and renk_yolu.is_file():
            try:
                return str(hedef), json.loads(renk_yolu.read_text())["renk"]
            except (OSError, ValueError, KeyError):
                pass
        resim = QImage()
        if url.startswith("data:"):
            try:
                ham = base64.b64decode(url.split(",", 1)[1])
                resim = QImage.fromData(ham)
            except Exception as hata:
                print("kapak data hatasi:", hata, flush=True)
        elif url.startswith("http://") or url.startswith("https://"):
            try:
                veri = urlopen(url, timeout=5).read()
                resim = QImage.fromData(veri)
            except Exception as hata:
                print("kapak indirilemedi:", hata, flush=True)
        else:
            yol = url[7:] if url.startswith("file://") else url
            resim = QImage(yol)
        if resim.isNull():
            print("kapak cozulemedi:", url[:80], flush=True)
            return None
        taraf = min(resim.width(), resim.height())
        resim = resim.copy(
            (resim.width() - taraf) // 2, (resim.height() - taraf) // 2, taraf, taraf
        ).scaled(176, 176, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        resim.save(str(hedef), "JPEG", 88)
        renk = self._renk_hesapla(str(hedef))
        renk_yolu.write_text(json.dumps({"renk": renk}))
        return str(hedef), renk

    def _kapak_uygula(self, yol: str, renk: str) -> None:
        if yol != self._kapak or renk != self._renk:
            self._kapak = yol
            self._renk = renk
            self.degisti.emit()

    @Slot(str, str, str)
    def _kapak_sonuc(self, anahtar: str, yol: str, renk: str) -> None:
        if anahtar == str(self._kapak_key):
            self._kapak_uygula(yol, renk)

    def _kapak_baslat(self, url: str) -> None:
        if not url:
            self._kapak_uygula(self._demo_kapak(), self._renk_hesapla(self._demo_kapak()))
            return
        ad = hashlib.sha1(("v2:" + url).encode()).hexdigest()
        hedef = self._kapak_dizini() / f"{ad}.jpg"
        if hedef.is_file():
            try:
                renk = json.loads((self._kapak_dizini() / f"{ad}.json").read_text())["renk"]
                self._kapak_uygula(str(hedef), renk)
                return
            except (OSError, ValueError, KeyError):
                pass
        if not (url.startswith("http://") or url.startswith("https://")):
            sonuc = self._kapak_isle(url)
            if sonuc:
                self._kapak_uygula(*sonuc)
            else:
                self._kapak_uygula(self._demo_kapak(), self._renk_hesapla(self._demo_kapak()))
            return
        if self._kapak_bekliyor:
            return
        self._kapak_bekliyor = True
        anahtar = str(self._kapak_key)

        def islet():
            try:
                sonuc = self._kapak_isle(url)
            except Exception as hata:
                print("kapak isleme hatasi:", hata, flush=True)
                sonuc = None
            self._kapak_bekliyor = False
            if sonuc:
                self.kapakHazir.emit(anahtar, sonuc[0], sonuc[1])

        threading.Thread(target=islet, daemon=True).start()

    def _kapak_hesapla_ve_uygula(self, url: str) -> None:
        self._kapak_baslat(url)

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
    islemSayaci = Property(int, lambda s: s._islem_sayaci, notify=degisti)
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
            self._baslik = os.environ.get("DOCK_DEMO_TR") and "Şişli'de Öğle Güneşi · Çığlık" or _DEMO_BASLIK
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

    def _gdbus_meta(self) -> dict:
        """PySide a{sv} cozemediginde gdbus ile Metadata oku (yedek)."""
        try:
            cikti = subprocess.run(
                [
                    "gdbus", "call", "--session", "--dest", self._servis,
                    "--object-path", "/org/mpris/MediaPlayer2",
                    "--method", "org.freedesktop.DBus.Properties.Get",
                    "org.mpris.MediaPlayer2.Player", "Metadata",
                ],
                capture_output=True, text=True, timeout=3,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return {}

        def metin(anahtar: str) -> str:
            eslesme = re.search(r"'" + anahtar + r"': <'([^']*)'>", cikti)
            if eslesme:
                return eslesme.group(1)
            liste = re.search(r"'" + anahtar + r"': <\[([^\]]*)\]>", cikti)
            if liste:
                return ", ".join(re.findall(r"'([^']*)'", liste.group(1)))
            return ""

        sure = re.search(r"'mpris:length': <int64 (\d+)>", cikti)
        iz = re.search(r"'mpris:trackid': <objectpath '([^']+)'>", cikti)
        return {
            "xesam:title": metin("xesam:title"),
            "xesam:artist": metin("xesam:artist"),
            "xesam:album": metin("xesam:album"),
            "mpris:artUrl": metin("mpris:artUrl"),
            "mpris:length": int(sure.group(1)) if sure else 0,
            "mpris:trackid": iz.group(1) if iz else "",
        }

    def _mpris_oku(self) -> None:
        if self._iface is None:
            return
        try:
            ham = self._iface.property("Metadata")
            meta = ham if isinstance(ham, dict) else None
            durum = str(self._iface.property("PlaybackStatus") or "Paused")
            konum = int(self._iface.property("Position") or 0)
        except Exception:
            self._iface = None
            self._demo = True
            return
        if not meta:
            meta = self._gdbus_meta()
        sanatci = meta.get("xesam:artist") or ""
        if isinstance(sanatci, (list, tuple)):
            sanatci = ", ".join(str(s) for s in sanatci)
        self._baslik = str(meta.get("xesam:title") or "")
        self._sanatci = str(sanatci)
        self._album = str(meta.get("xesam:album") or "")
        art = str(meta.get("mpris:artUrl") or "")
        sahte = os.environ.get("DOCK_SAHTE_ARTURL")
        if sahte:
            ikinci = os.environ.get("DOCK_SAHTE_ARTURL_2")
            art = ikinci if (ikinci and "Turuncu" in str(meta.get("xesam:title") or "")) else sahte
        track = str(meta.get("mpris:trackid") or "")
        anahtar = (track, art)
        if anahtar != self._kapak_key:
            self._kapak_key = anahtar
            self._kapak_baslat(art)
        self._track = track
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
