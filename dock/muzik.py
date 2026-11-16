"""Simdi caliyor: MPRIS (QtDBus) veya demo oynatici."""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtDBus import QDBusConnection, QDBusInterface

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
        self._kapak = ""
        self._sure = _DEMO_SURE
        self._konum = 72_000
        self._caliyor = True
        self._demo = True
        self._iface: QDBusInterface | None = None
        self._deneme = 0
        self._ui_sayac = 0
        self._ui_aktif = False
        self._zaman = QTimer(self)
        self._zaman.setInterval(1000)
        self._zaman.timeout.connect(self._tik)
        self._zaman.start()
        self._mpris_ara()

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
                self._iface = iface
                self._demo = False
                self._mpris_oku()
                return

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
        self._kapak = str(meta.get("mpris:artUrl") or "")
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
            self._mpris_oku()

    @Slot(bool)
    def ui_aktif_ayarla(self, deger: bool) -> None:
        self._ui_aktif = deger
        if deger:
            self.degisti.emit()

    # --- dugmeler ----------------------------------------------------------
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
